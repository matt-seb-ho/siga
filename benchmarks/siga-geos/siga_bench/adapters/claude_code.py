"""Claude Code (`claude -p`, the CLI installed in the agent image) via an
Anthropic-compatible gateway (default OpenRouter's https://openrouter.ai/api).

STATUS: EXPERIMENTAL, NOT VALIDATED. This adapter runs the bare Claude Code harness
(no SIGA adapter). In one smoke run (ExampleMandel, a small open model via
OpenRouter) it started and stayed isolated (GitHub, GitLab and PyPI were refused by
the proxy) but timed out without writing a deck. Through OpenRouter's Anthropic
endpoint, assistant events carry no usage, so tokens and $ exist only if Claude Code
exits cleanly (final `result` event), and there is no gate-side $ cap. Use pi or
codex for metered runs. To run Claude Code *with* SIGA, see scripts/siga_cell.py.

Network: like codex, a host CONNECT proxy allowlisting only the gateway host. Unlike pi,
the gateway token is inside the sandbox (Claude Code must hold it); the proxy limits
where it can be used. Token: $OPENROUTER_API_KEY on the host (or the variable named by
$SIGA_CLAUDE_TOKEN_VAR); gateway: --base-url option or $SIGA_ANTHROPIC_BASE_URL.

Tools: the SIGA paper's disallowed list (Skill, AskUserQuestion) plus sub-agent,
scheduling and web tools (Task, Agent, TaskCreate, WebFetch, WebSearch, ...), so the
named model does all the work and cannot reach the web.

Metric mapping (SIGA paper definitions):
  turn = one stream-json `assistant` event; tool call = one `tool_use` block in it.
  tokens from the final `result` event's usage; usd = result.total_cost_usd
  (Claude Code's own estimate; usd_basis "claude-code-estimate").
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

from ..sandbox import SandboxSpec, with_relay
from .base import Adapter, RunContext, api_key, start, wait_socket

PROXY = Path(__file__).resolve().parents[1] / "net" / "connect_proxy.py"
DISALLOWED = ("Skill", "AskUserQuestion", "Task", "Agent", "TaskCreate", "WebFetch", "WebSearch",
              # newer Claude Code builds: sub-agent / scheduling / cross-session tools
              "Workflow", "SendMessage", "CronCreate", "CronDelete", "CronList", "ScheduleWakeup",
              "EnterWorktree", "ExitWorktree", "RemoteTrigger")


class ClaudeCodeAdapter(Adapter):
    name = "claude-code"

    def _base_url(self, ctx):
        return ctx.options.get("base_url") or os.environ.get("SIGA_ANTHROPIC_BASE_URL", "https://openrouter.ai/api")

    def setup(self, ctx: RunContext) -> None:
        (ctx.home / ".claude").mkdir(parents=True, exist_ok=True)

    def services(self, ctx: RunContext):
        sock = ctx.sock_dir / "net.sock"
        host = urlparse(self._base_url(ctx)).hostname
        p = start([sys.executable, str(PROXY), "--socket", str(sock), "--allow", host,
                   "--log", str(ctx.agent_dir / "net.jsonl")], ctx.agent_dir / "proxy.stderr",
                  env={"PATH": "/usr/bin:/bin"})
        wait_socket(sock, [p])
        return [p]

    def sandbox(self, ctx: RunContext, spec: SandboxSpec) -> None:
        key_var = ctx.options.get("key_var") or os.environ.get("SIGA_CLAUDE_TOKEN_VAR", "OPENROUTER_API_KEY")
        key = api_key(key_var)
        if not key:
            raise RuntimeError(f"claude-code: ${key_var} is empty or unset")
        proxy = "http://127.0.0.1:8080"
        spec.env.update({
            "ANTHROPIC_BASE_URL": self._base_url(ctx), "ANTHROPIC_AUTH_TOKEN": key, "ANTHROPIC_API_KEY": "",
            "ANTHROPIC_CUSTOM_MODEL_OPTION": ctx.model, "ANTHROPIC_CUSTOM_MODEL_OPTION_NAME": ctx.model,
            "HTTPS_PROXY": proxy, "https_proxy": proxy, "NO_PROXY": "127.0.0.1,localhost",
            "DISABLE_TELEMETRY": "1", "DISABLE_AUTOUPDATER": "1", "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"})

    def command(self, ctx: RunContext) -> list[str]:
        argv = ["claude", "-p", "--verbose", "--model", ctx.model, "--output-format", "stream-json",
                "--permission-mode", "bypassPermissions", "--max-turns", str(ctx.options.get("max_turns", 100))]
        for t in DISALLOWED:
            argv += ["--disallowedTools", t]
        return with_relay("net.sock", argv + ["--", ctx.prompt])

    def collect(self, ctx: RunContext) -> dict:
        m = {"tokens_in": 0, "tokens_cached_in": 0, "tokens_out": 0, "tokens_reasoning": None,
             "tool_calls": 0, "turns": 0, "usd": None, "usd_basis": "claude-code-estimate", "tools_by_name": {}}
        strings = []
        ev = ctx.agent_dir / "events.jsonl"
        for ln in (ev.read_text(errors="ignore").splitlines() if ev.exists() else []):
            try:
                e = json.loads(ln)
            except json.JSONDecodeError:
                continue
            if e.get("type") == "assistant":
                m["turns"] += 1
                for b in (e.get("message") or {}).get("content") or []:
                    if isinstance(b, dict) and b.get("type") == "tool_use":
                        m["tool_calls"] += 1
                        m["tools_by_name"][b.get("name")] = m["tools_by_name"].get(b.get("name"), 0) + 1
                        strings.append(json.dumps(b.get("input")))
            elif e.get("type") == "result":
                u = e.get("usage") or {}
                m["tokens_cached_in"] = int(u.get("cache_read_input_tokens", 0))
                m["tokens_in"] = int(u.get("input_tokens", 0)) + m["tokens_cached_in"] + int(u.get("cache_creation_input_tokens", 0))
                m["tokens_out"] = int(u.get("output_tokens", 0))
                m["usd"] = e.get("total_cost_usd")
                m["exit_reason"] = e.get("subtype")
        m["commands"] = strings
        return m
