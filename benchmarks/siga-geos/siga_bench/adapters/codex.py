"""OpenAI Codex CLI (`codex exec`), ChatGPT-plan login.

Isolation: Codex's own sandbox lets commands read the whole host filesystem, so it is
switched off (sandbox_mode danger-full-access, approval never) and Codex runs inside
our bwrap sandbox instead, where only task files exist. The sandbox has no network;
HTTPS_PROXY points at the relay, which pipes to a host-side CONNECT proxy
(net/connect_proxy.py) that allows only chatgpt.com and *.openai.com on port 443 and
logs every connection (agent/net.jsonl). GitHub, PyPI etc. are refused.

Per-run CODEX_HOME (/home/agent/.codex) holds a copy of ~/.codex/auth.json and a
config.toml with: web_search disabled; memories, plugins, apps, multi_agent, goals,
browser/computer use, image generation off; history persistence none; bundled
skills off. No AGENTS.md exists anywhere in the sandbox. If Codex refreshed the
token during the run, the new auth.json is copied back to ~/.codex/auth.json (only if that file did not change
meanwhile), so the copies never diverge silently.

Metric mapping (SIGA paper definitions):
  turn       = one model response (one `token_usage_record` in the rollout)
  tool call  = one top-level tool call item the model emitted (function_call /
               custom_tool_call / local_shell_call); shell commands run inside a
               code-mode `exec` call are counted separately as commands_executed
  tokens     = sum over responses of input_tokens (cached included), cached_input_tokens,
               output_tokens (reasoning included), reasoning_output_tokens
  usd        = API-equivalent list-price estimate from SIGA_PRICE_<MODEL> ("in,cached_in,out"
               $/Mtok) or DEFAULT_PRICES; otherwise null (usd_basis "list-price-unknown")
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path

from .. import config
from ..sandbox import SandboxSpec, with_relay
from .base import Adapter, RunContext, start, wait_socket

PROXY = Path(__file__).resolve().parents[1] / "net" / "connect_proxy.py"
ALLOW = ("chatgpt.com", "openai.com")

CONFIG_TOML = """\
model = "{model}"
model_reasoning_effort = "{effort}"
web_search = "disabled"
approval_policy = "never"
sandbox_mode = "danger-full-access"
check_for_update_on_startup = false

[features]
memories = false
plugins = false
apps = false
multi_agent = false
goals = false
browser_use = false
computer_use = false
image_generation = false
in_app_browser = false
remote_plugin = false
tool_suggest = false

[history]
persistence = "none"

# Codex's bundled skills (imagegen, openai-docs, skill-creator, skill-installer) are off, so
# the agent has no skills: every agent gets the same task and the same GEOS tree only.
[skills.bundled]
enabled = false
"""

# $/Mtok (input, cached input, output) from OpenAI's model page,
# https://developers.openai.com/api/docs/models/gpt-6-luna (read 2026-11-03).
# Requests whose prompt exceeds LONG_CTX tokens are billed 2x input and 1.5x output.
DEFAULT_PRICES: dict[str, tuple[float, float, float]] = {"gpt-6-luna": (0.10, 0.01, 0.50)}
LONG_CTX, LONG_IN_X, LONG_OUT_X = 272_000, 2.0, 1.5


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else ""


def price_for(model: str):
    env = os.environ.get("SIGA_PRICE_" + re.sub(r"[^A-Za-z0-9]", "_", model).upper())
    if env:
        a = [float(x) for x in env.split(",")]
        return tuple(a), "env SIGA_PRICE_*"
    if model in DEFAULT_PRICES:
        return DEFAULT_PRICES[model], "DEFAULT_PRICES"
    return None, None


class CodexAdapter(Adapter):
    name = "codex"

    def setup(self, ctx: RunContext) -> None:
        ch = ctx.home / ".codex"
        ch.mkdir(parents=True, exist_ok=True)
        if not config.CODEX_AUTH.exists():
            raise config.ConfigError(f"codex: no auth.json at {config.CODEX_AUTH} (run `codex login` or set SIGA_CODEX_AUTH)")
        shutil.copy2(config.CODEX_AUTH, ch / "auth.json")
        (ch / "auth.json").chmod(0o600)
        (ctx.agent_dir / "auth_snapshot.sha").write_text(_sha(config.CODEX_AUTH))
        (ch / "config.toml").write_text(CONFIG_TOML.format(
            model=ctx.model, effort=ctx.options.get("effort", "max")))

    def services(self, ctx: RunContext):
        sock = ctx.sock_dir / "net.sock"
        cmd = [sys.executable, str(PROXY), "--socket", str(sock), "--log", str(ctx.agent_dir / "net.jsonl")]
        for a in ALLOW:
            cmd += ["--allow", a]
        p = start(cmd, ctx.agent_dir / "proxy.stderr", env={"PATH": "/usr/bin:/bin"})
        wait_socket(sock, [p])
        return [p]

    def sandbox(self, ctx: RunContext, spec: SandboxSpec) -> None:
        spec.ro_binds += [(config.require("SIGA_CODEX_PKG", config.CODEX_PKG, "the Codex CLI npm install"), "/opt/codex")]
        spec.path_prefix += ["/opt/codex/node_modules/.bin"]
        proxy = "http://127.0.0.1:8080"
        spec.env.update({"CODEX_HOME": "/home/agent/.codex", "HTTPS_PROXY": proxy, "https_proxy": proxy,
                         "HTTP_PROXY": proxy, "http_proxy": proxy, "NO_PROXY": "127.0.0.1,localhost"})

    def command(self, ctx: RunContext) -> list[str]:
        return with_relay("net.sock", [
            "codex", "exec", "--skip-git-repo-check", "--json", "-m", ctx.model,
            "-c", f"model_reasoning_effort={ctx.options.get('effort', 'max')}",
            "-C", "/workspace", ctx.prompt])

    def collect(self, ctx: RunContext) -> dict:
        m = {"tokens_in": 0, "tokens_cached_in": 0, "tokens_out": 0, "tokens_reasoning": 0,
             "tool_calls": 0, "turns": 0, "commands_executed": 0, "tools_by_name": {}}
        sess = ctx.home / ".codex" / "sessions"
        rollouts = sorted(sess.rglob("rollout-*.jsonl")) if sess.exists() else []
        dst = ctx.agent_dir / "rollouts"
        dst.mkdir(exist_ok=True)
        strings: list[str] = []
        exit_reason = None
        tools_seen = set()
        per_resp: list[dict] = []
        for r in rollouts:
            shutil.copy2(r, dst / r.name)
            seen_resp = set()
            for ln in r.read_text(errors="ignore").splitlines():
                try:
                    d = json.loads(ln)
                except json.JSONDecodeError:
                    continue
                t, p = d.get("type"), d.get("payload") or {}
                if t == "token_usage_record":
                    rid = p.get("response_id")
                    if rid in seen_resp:
                        continue
                    seen_resp.add(rid)
                    u = p.get("usage") or {}
                    per_resp.append(u)
                    m["turns"] += 1
                    m["tokens_in"] += int(u.get("input_tokens", 0))
                    m["tokens_cached_in"] += int(u.get("cached_input_tokens", 0))
                    m["tokens_out"] += int(u.get("output_tokens", 0))
                    m["tokens_reasoning"] += int(u.get("reasoning_output_tokens", 0))
                elif t == "response_item" and p.get("type") in ("function_call", "custom_tool_call", "local_shell_call"):
                    m["tool_calls"] += 1
                    nm = p.get("name") or p.get("type")
                    m["tools_by_name"][nm] = m["tools_by_name"].get(nm, 0) + 1
                    strings.append(str(p.get("input") or p.get("arguments") or p.get("action") or ""))
                elif t == "response_item" and p.get("type") == "additional_tools":
                    tools_seen.update(re.findall(r'"name": "([^"]+)"', json.dumps(p)))
                elif t == "event_msg" and p.get("type") == "item_completed":
                    it = p.get("item") or {}
                    if it.get("type") == "CommandExecution":
                        m["commands_executed"] += 1
                        strings.append(json.dumps(it.get("command")))
                elif t == "event_msg" and p.get("type") == "task_complete":
                    exit_reason = "completed"
                elif t == "event_msg" and p.get("type") in ("error", "stream_error", "turn_aborted"):
                    exit_reason = f"{p.get('type')}: {str(p.get('message') or p.get('reason') or '')[:200]}"
        err = (ctx.agent_dir / "stderr.log")
        errtxt = err.read_text(errors="ignore")[-20000:] if err.exists() else ""
        evtxt = (ctx.agent_dir / "events.jsonl").read_text(errors="ignore")[-20000:] if (ctx.agent_dir / "events.jsonl").exists() else ""
        if re.search(r"rate.?limit|usage limit|429|Too Many Requests", errtxt + evtxt, re.I) and exit_reason != "completed":
            exit_reason = "rate_limited"
        m["exit_reason"] = exit_reason
        m["model_tools"] = sorted(tools_seen)
        m["commands"] = strings
        price, src = price_for(ctx.model)
        if price:
            pin, pcache, pout = price
            usd = 0.0
            for u in per_resp:
                i, c, o = int(u.get("input_tokens", 0)), int(u.get("cached_input_tokens", 0)), int(u.get("output_tokens", 0))
                xi, xo = (LONG_IN_X, LONG_OUT_X) if i > LONG_CTX else (1.0, 1.0)
                usd += ((i - c) * pin * xi + c * pcache * xi + o * pout * xo) / 1e6
            m["usd"] = round(usd, 6)
            m["usd_basis"] = "list-price-estimate"
            m["usd_price_source"] = src
        else:
            m["usd"] = None
            m["usd_basis"] = "list-price-unknown"
        return m

    def finalize(self, ctx: RunContext) -> None:
        run_auth = ctx.home / ".codex" / "auth.json"
        snap = (ctx.agent_dir / "auth_snapshot.sha").read_text().strip()
        note = {"refreshed": False}
        if run_auth.exists() and _sha(run_auth) != snap:
            note["refreshed"] = True
            lock = config.CODEX_AUTH.parent / "auth.json.siga.lock"
            with open(lock, "w") as fh:
                fcntl.flock(fh, fcntl.LOCK_EX)
                if _sha(config.CODEX_AUTH) == snap:
                    tmp = config.CODEX_AUTH.with_suffix(".json.siga.tmp")
                    shutil.copy2(run_auth, tmp)
                    tmp.chmod(0o600)
                    os.replace(tmp, config.CODEX_AUTH)
                    note["copied_back"] = True
                else:
                    note["copied_back"] = False
                    note["conflict"] = "global auth.json changed during the run; left as is"
        (ctx.agent_dir / "auth_refresh.json").write_text(json.dumps(note))
        # The run's credential copy is not kept in the run dir.
        try:
            run_auth.unlink()
        except OSError:
            pass
