"""pi coding agent (earendil-works/pi-coding-agent) on OpenRouter.

Network: pi talks plain HTTP to 127.0.0.1:8080 in the sandbox; the relay pipes it to
the host-side model gate (net/llm_gate.py), which accepts only POST chat/completions
for the one allowed model, strips web plugins, injects the OpenRouter key (the key
never enters the sandbox), enforces a per-run $ cap, and logs billed cost per request.

Key: read on the host from $OPENROUTER_API_KEY (or the variable named by
$SIGA_OR_KEY_VAR; also looked up in the dotenv file $SIGA_ENV_FILE if set).

Config: --offline, -na (ignore project-local files), tools read,bash,edit,write,grep,find,ls,
thinking level from --thinking (default medium).

Metric mapping (SIGA paper definitions):
  turn       = one assistant message (pi `message_end` event with role assistant)
  tool call  = one `toolCall` content block in an assistant message
  tokens_in  = usage.input + usage.cacheRead ; tokens_cached_in = usage.cacheRead
  tokens_out = usage.output ; tokens_reasoning = usage.reasoning
  usd        = sum of gate-logged OpenRouter billed cost (usd_basis "billed")
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from .. import config
from ..sandbox import SandboxSpec, with_relay
from .base import Adapter, RunContext, api_key, start, wait_socket

GATE = Path(__file__).resolve().parents[1] / "net" / "llm_gate.py"


class PiAdapter(Adapter):
    name = "pi"

    def setup(self, ctx: RunContext) -> None:
        d = ctx.home / ".pi" / "agent"
        d.mkdir(parents=True, exist_ok=True)
        (d / "models.json").write_text(json.dumps({"providers": {"openrouter": {
            "baseUrl": "http://127.0.0.1:8080/api/v1", "apiKey": "no-key-in-sandbox"}}}))
        (d / "settings.json").write_text(json.dumps({
            "defaultProvider": "openrouter", "defaultModel": ctx.model,
            "defaultThinkingLevel": ctx.options.get("thinking", "medium"),
            "defaultProjectTrust": "never", "enableInstallTelemetry": False, "quietStartup": True,
            "retry": {"enabled": True, "maxRetries": 5}}))

    def services(self, ctx: RunContext):
        key_var = ctx.options.get("key_var") or os.environ.get("SIGA_OR_KEY_VAR", "OPENROUTER_API_KEY")
        key = api_key(key_var)
        if not key:
            raise RuntimeError(f"pi: ${key_var} is empty or unset (fail closed; no fallback key)")
        sock = ctx.sock_dir / "llm.sock"
        env = {"PATH": "/usr/bin:/bin", "HOME": str(Path.home()), "OPENROUTER_API_KEY": key}
        cmd = [sys.executable, str(GATE), "--socket", str(sock), "--model", ctx.model,
               "--cap-usd", str(ctx.options.get("cap_usd", 3.0)), "--log", str(ctx.agent_dir / "gate_usage.jsonl")]
        if ctx.options.get("sampling_seed") is not None:
            cmd += ["--seed", str(ctx.options["sampling_seed"])]
        p = start(cmd, ctx.agent_dir / "gate.stderr", env=env)
        wait_socket(sock, [p])
        return [p]

    def sandbox(self, ctx: RunContext, spec: SandboxSpec) -> None:
        spec.ro_binds += [(config.require("SIGA_PI_NODE", config.PI_NODE, "a Node.js install"), "/opt/node"),
                          (config.require("SIGA_PI_PKG", config.PI_PKG, "the pi package"), "/opt/pi")]
        spec.path_prefix += ["/opt/node/bin", "/opt/pi/bin"]
        spec.env.update({"PI_OFFLINE": "1", "PI_TELEMETRY": "0"})

    def command(self, ctx: RunContext) -> list[str]:
        return with_relay("llm.sock", [
            "pi", "--mode", "json", "--offline", "-na",
            "--model", f"openrouter/{ctx.model}", "--tools", "read,bash,edit,write,grep,find,ls",
            "--session-dir", "/home/agent/sessions", ctx.prompt])

    def collect(self, ctx: RunContext) -> dict:
        m = {"tokens_in": 0, "tokens_cached_in": 0, "tokens_out": 0, "tokens_reasoning": 0,
             "tool_calls": 0, "turns": 0, "usd": 0.0, "usd_basis": "billed", "tools_by_name": {}}
        last_stop = None
        ev = ctx.agent_dir / "events.jsonl"
        strings: list[str] = []
        if ev.exists():
            for ln in ev.read_text(errors="ignore").splitlines():
                try:
                    e = json.loads(ln)
                except json.JSONDecodeError:
                    continue
                if e.get("type") != "message_end":
                    continue
                msg = e.get("message") or {}
                if msg.get("role") != "assistant":
                    continue
                m["turns"] += 1
                u = msg.get("usage") or {}
                m["tokens_in"] += int(u.get("input", 0)) + int(u.get("cacheRead", 0))
                m["tokens_cached_in"] += int(u.get("cacheRead", 0))
                m["tokens_out"] += int(u.get("output", 0))
                m["tokens_reasoning"] += int(u.get("reasoning", 0))
                last_stop = msg.get("stopReason")
                for c in msg.get("content") or []:
                    if isinstance(c, dict) and c.get("type") == "toolCall":
                        m["tool_calls"] += 1
                        nm = c.get("name", "?")
                        m["tools_by_name"][nm] = m["tools_by_name"].get(nm, 0) + 1
                        strings.append(json.dumps(c.get("arguments", {})))
        gate = ctx.agent_dir / "gate_usage.jsonl"
        n_req = 0
        if gate.exists():
            for ln in gate.read_text().splitlines():
                try:
                    r = json.loads(ln)
                except json.JSONDecodeError:
                    continue
                n_req += 1
                m["usd"] += float(r.get("cost") or 0.0)
        m["usd"] = round(m["usd"], 6)
        m["gate_requests"] = n_req
        m["exit_reason"] = last_stop
        m["commands"] = strings
        return m
