"""One run: task x agent x model x seed -> run dir with metrics.json.

Run dir layout (--out DIR):
  workspace/inputs/     the agent's deck (sandbox /workspace)
  home/                 the agent's HOME (config, sessions)
  agent/                events.jsonl (agent stdout), stderr.log, gate/proxy logs, rollouts
  verifier/             reward.json, reward.txt, score_details.json
  run.json              full run config (argv, versions, prompt hash, sandbox listing hash)
  metrics.json          the common metrics (see README)
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

from . import config, geostree
from .adapters import ADAPTERS
from .adapters.base import RunContext
from .sandbox import SandboxSpec, bwrap_argv, render

SUSPICIOUS = re.compile(r"\bgit\b|\bcurl\b|\bwget\b|github|raw\.githubusercontent|pip\s+download|"
                        r"find\s+/\s|find\s+/(?:usr|etc|home|opt|proc|data|mnt|srv|run)\b|/(?:data|mnt|srv)/|auth\.json|chatgpt\.com|"
                        r"openrouter|/proc/\d+|/run/net", re.I)


def _sha16(s: str | bytes) -> str:
    return hashlib.sha256(s.encode() if isinstance(s, str) else s).hexdigest()[:16]


def build_prompt(task_dir: Path) -> str:
    """The prompt is the task's instruction.md, identical for every agent."""
    return (task_dir / "instruction.md").read_text()


def verify(task_dir: Path, generated: Path, out: Path, scorer: str | None = None) -> dict:
    """Score `generated` with the task's verifier. `scorer`: "paper" (default) or "fixed";
    None defers to $SIGA_SCORER, then to the paper scorer."""
    out.mkdir(parents=True, exist_ok=True)
    extra = ["--scorer", scorer] if scorer else []
    r = subprocess.run([sys.executable, str(task_dir / "tests" / "score.py"), "--reference",
                        str(task_dir / "tests" / "reference"), "--generated", str(generated), "--out", str(out)] + extra,
                       capture_output=True, text=True, timeout=config.DEFAULT_VERIFIER_TIMEOUT_S)
    if r.returncode != 0:
        (out / "verifier.stderr").write_text(r.stderr)
    try:
        return json.loads((out / "score_details.json").read_text())
    except (OSError, json.JSONDecodeError):
        return {"reward": 0.0, "failure": f"verifier crashed: {r.stderr[-300:]}"}


def _kill(proc: subprocess.Popen) -> None:
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(proc.pid, sig)
        except ProcessLookupError:
            return
        try:
            proc.wait(timeout=20)
            return
        except subprocess.TimeoutExpired:
            continue


def run(agent: str, model: str, task: str, seed: int, out: Path,
        timeout_s: int | None = None, options: dict | None = None, dry_run: bool = False,
        command_override: list[str] | None = None, extra_binds: list[tuple[Path, str]] | None = None,
        scorer: str | None = None) -> dict:
    if agent not in ADAPTERS:
        raise SystemExit(f"unknown agent {agent!r}; have {sorted(ADAPTERS)}")
    task_dir = config.task_dir(task)
    tname = _task_name(task_dir)
    out = out.resolve()
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"run dir {out} exists and is not empty")
    for sub in ("workspace/inputs", "home", "sock", "agent", "verifier"):
        (out / sub).mkdir(parents=True, exist_ok=True)
    options = dict(options or {})
    options.setdefault("run_id", f"siga-{agent}-{task_dir.name}-s{seed}-{int(time.time())}")
    ctx = RunContext(task=tname, task_dir=task_dir, model=model, seed=seed, out=out,
                     prompt=build_prompt(task_dir),
                     timeout_s=int(timeout_s or config.DEFAULT_AGENT_TIMEOUT_S), options=options)
    adapter = ADAPTERS[agent]()
    geos = geostree.filtered_tree(task_dir)
    adapter.setup(ctx)
    spec = SandboxSpec(geos_lib=geos, workspace=ctx.workspace, home=ctx.home, sock_dir=ctx.sock_dir)
    adapter.sandbox(ctx, spec)
    if extra_binds:
        spec.ro_binds += extra_binds
    inner = command_override or adapter.command(ctx)
    argv = bwrap_argv(spec) + inner
    shown = _redact([("<prompt>" if a == ctx.prompt else a) for a in argv])
    home_listing = sorted(str(p.relative_to(ctx.home)) for p in ctx.home.rglob("*"))
    runinfo = {
        "agent": agent, "model": model, "task": tname, "task_id": task_dir.name,
        "seed": seed, "scorer": scorer, "timeout_s": ctx.timeout_s, "options": {k: v for k, v in options.items() if "key" not in k},
        "prompt_sha256": _sha16(ctx.prompt), "instruction_sha256": _sha16((task_dir / "instruction.md").read_text()),
        "geos_lib": str(geos), "argv": render(shown), "home_listing_sha256": _sha16("\n".join(home_listing)),
        "home_listing": home_listing if len(home_listing) < 400 else home_listing[:400],
        "started": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "siga_bench_commit": _git_head(),
    }
    (out / "run.json").write_text(json.dumps(runinfo, indent=1))
    if dry_run:
        return runinfo
    # SIGTERM to the runner must also stop the agent (own process group) and the services.
    def _term(signum, frame):
        raise KeyboardInterrupt(f"signal {signum}")
    old = signal.signal(signal.SIGTERM, _term)
    procs = adapter.services(ctx)
    t0 = time.time()
    timed_out = False
    rc = None
    proc = None
    try:
        with open(ctx.agent_dir / "events.jsonl", "wb") as so, open(ctx.agent_dir / "stderr.log", "wb") as se:
            proc = subprocess.Popen(argv, stdout=so, stderr=se, stdin=subprocess.DEVNULL, start_new_session=True)
            try:
                rc = proc.wait(timeout=ctx.timeout_s)
            except subprocess.TimeoutExpired:
                timed_out = True
                _kill(proc)
                rc = proc.returncode
    except BaseException:
        if proc is not None and proc.poll() is None:
            _kill(proc)
        raise
    finally:
        signal.signal(signal.SIGTERM, old)
        for p in procs:
            try:
                os.killpg(p.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        shutil.rmtree(ctx.sock_dir, ignore_errors=True)   # the per-run /tmp/siga-sock-* dir
    wall = round(time.time() - t0, 1)
    if command_override is not None:          # probe / shell mode: no scoring
        adapter.finalize(ctx)
        return {"exit_code": rc, "timed_out": timed_out, "wall_s": wall}
    m = adapter.collect(ctx)
    adapter.finalize(ctx)
    res = verify(task_dir, ctx.workspace / "inputs", out / "verifier", scorer)
    metrics = assemble(ctx, agent, m, res, rc, timed_out, wall)
    (out / "metrics.json").write_text(json.dumps(metrics, indent=1))
    runinfo.update({"finished": dt.datetime.now().astimezone().isoformat(timespec="seconds"), "exit_code": rc})
    (out / "run.json").write_text(json.dumps(runinfo, indent=1))
    return metrics


def assemble(ctx: RunContext, agent: str, m: dict, res: dict, rc, timed_out: bool, wall: float) -> dict:
    cmds = m.get("commands") or []
    sus = [c[:300] for c in cmds if SUSPICIOUS.search(c)]
    exit_reason = "timeout" if timed_out else (m.get("exit_reason") or f"exit_code {rc}")
    infra = exit_reason == "rate_limited" or (m.get("turns", 0) == 0)
    return {
        "agent": agent, "model": ctx.model, "task": ctx.task, "seed": ctx.seed,
        "score": round(float(res.get("reward") or 0.0), 6), "scorer": res.get("scorer"),
        "score_components": {"treesim_sections": res.get("sections") or {}, "failure": res.get("failure"),
                             "n_generated_xml": res.get("n_generated_xml", 0),
                             "score_primary_no_smoke": res.get("reward_primary")},
        "tokens_in": m.get("tokens_in"), "tokens_cached_in": m.get("tokens_cached_in"),
        "tokens_out": m.get("tokens_out"), "tokens_reasoning": m.get("tokens_reasoning"),
        "usd": m.get("usd"), "usd_basis": m.get("usd_basis"),
        "tool_calls": m.get("tool_calls"), "turns": m.get("turns"), "wall_s": wall,
        "exit_reason": exit_reason, "exit_code": rc, "timed_out": timed_out, "infra_failure": infra,
        "suspicious_commands": sus[:50], "n_suspicious_commands": len(sus),
        "extra": {k: v for k, v in m.items() if k not in {
            "tokens_in", "tokens_cached_in", "tokens_out", "tokens_reasoning", "usd", "usd_basis", "tool_calls",
            "turns", "exit_reason", "commands"}},
    }


_SECRET_ENV = re.compile(r"KEY|TOKEN|SECRET|PASSWORD|AUTH", re.I)


def _redact(argv: list[str]) -> list[str]:
    """Hide the values of secret-looking `--setenv NAME VALUE` pairs before argv is logged."""
    out = list(argv)
    for i in range(len(out) - 2):
        if out[i] == "--setenv" and _SECRET_ENV.search(out[i + 1]) and out[i + 2]:
            out[i + 2] = "<redacted>"
    return out


def _task_name(task_dir: Path) -> str:
    for ln in (task_dir / "task.toml").read_text().splitlines():
        if ln.startswith("siga_task"):
            return ln.split("=", 1)[1].strip().strip('"')
    return task_dir.name


def _git_head() -> str:
    try:
        return subprocess.run(["git", "-C", str(config.BENCH_ROOT), "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        return "?"


def recollect(out: Path, scorer: str | None = None) -> dict:
    """Rebuild metrics.json for a finished run dir from its saved trajectory and deck
    (e.g. after a parser or price fix, or to rescore with the other scorer).
    Agent, task and model come from run.json."""
    out = out.resolve()
    ri = json.loads((out / "run.json").read_text())
    task_dir = config.task_dir(ri["task_id"])
    ctx = RunContext(task=ri["task"], task_dir=task_dir, model=ri["model"],
                     seed=ri["seed"], out=out, prompt="", timeout_s=ri["timeout_s"], options=ri.get("options", {}))
    old = json.loads((out / "metrics.json").read_text())
    m = ADAPTERS[ri["agent"]]().collect(ctx)
    res = verify(task_dir, ctx.workspace / "inputs", out / "verifier", scorer or ri.get("scorer"))
    metrics = assemble(ctx, ri["agent"], m, res, old.get("exit_code"), old.get("timed_out", False), old.get("wall_s"))
    if old.get("timed_out"):
        metrics["exit_reason"] = "timeout"
    metrics["recollected"] = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    (out / "metrics.json").write_text(json.dumps(metrics, indent=1))
    return metrics
