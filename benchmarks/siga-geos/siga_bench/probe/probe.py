"""Run the leak probe inside a task's real sandbox (same adapter setup, binds and network
services as an agent run, with leak_probe.sh in place of the agent). No model is called;
the model name only configures the adapter (and, for pi, the gate's allowed model).

    siga-bench probe --agent codex --model MODEL --task ExampleMandel --out DIR
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from .. import config, geostree, runner
from ..adapters import ADAPTERS
from ..adapters.base import RunContext
from ..sandbox import SandboxSpec

SCRIPT = Path(__file__).with_name("leak_probe.sh")
_WS = re.compile(r"\s+")


def _visible_texts(tree: Path):
    for p in tree.rglob("*"):
        if p.is_file() and not p.is_symlink() and p.stat().st_size < 5_000_000:
            try:
                b = p.read_bytes()
            except OSError:
                continue
            if b"\0" not in b[:4096]:   # grep -I skips binary files too
                yield b.decode("utf-8", errors="ignore")


def probe_inputs(task_dir: Path, dest: Path, agent: str, options: dict | None = None) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    refs = sorted((task_dir / "tests" / "reference").rglob("*.xml"))
    (dest / "ref_sha256.txt").write_text("".join(hashlib.sha256(f.read_bytes()).hexdigest() + "\n" for f in refs))
    tree = geostree.filtered_tree(task_dir)
    # A "reference-only" line must not occur anywhere in the visible tree, not even as a
    # substring of a longer line, because the probe greps with fixed-string substring matching.
    blob = "\n".join(_WS.sub(" ", t) for t in _visible_texts(tree))
    out = set()
    for f in refs:
        for ln in f.read_text(errors="ignore").splitlines():
            s = ln.strip()
            if len(s) >= 30 and "=" in s and s not in out and _WS.sub(" ", s) not in blob:
                out.add(s)
    (dest / "ref_lines.txt").write_text("".join(x + "\n" for x in sorted(out)))
    spec = SandboxSpec(geos_lib=tree, workspace=Path("/x"), home=Path("/x"), sock_dir=Path("/x"))
    ad = ADAPTERS[agent]()
    dummy = RunContext(task="", task_dir=task_dir, model="m", seed=0, out=Path("/x"),
                       prompt="", timeout_s=1, options=dict(options or {}))
    try:
        ad.sandbox(dummy, spec)
    except RuntimeError:
        pass
    mounts = ["/", "/usr", "/etc", "/proc", "/dev", "/dev/pts", "/dev/shm", "/dev/mqueue", "/dev/null",
              "/dev/zero", "/dev/full", "/dev/random", "/dev/urandom", "/dev/tty", "/dev/console",
              "/tmp", "/geos_lib", "/workspace", "/home/agent", "/run/net", "/opt/relay.py", "/probe"]
    mounts += [dst for _, dst in spec.ro_binds]
    (dest / "expect_mounts.txt").write_text("\n".join(mounts) + "\n")
    import shutil
    shutil.copy2(SCRIPT, dest / "leak_probe.sh")


def probe(agent: str, task: str, out: Path, model: str, options: dict = None) -> dict:
    task_dir = config.task_dir(task)
    out = out.resolve()
    pdir = out.parent / (out.name + ".probe_inputs")
    probe_inputs(task_dir, pdir, agent, options)
    opts = dict(options or {})
    if agent == "pi":
        opts.setdefault("cap_usd", 0.05)
    res = runner.run(agent, model, task, 0, out, timeout_s=600, options=opts,
                     command_override=["bash", "-c", "python3 /opt/relay.py 8080 /run/net/$(ls /run/net | head -1) & sleep 1; exec bash /probe/leak_probe.sh"],
                     extra_binds=[(pdir, "/probe")])
    lines = []
    for ln in (out / "agent" / "events.jsonl").read_text().splitlines():
        try:
            lines.append(json.loads(ln))
        except json.JSONDecodeError:
            pass
    verdict = next((x["probe"] for x in lines if "probe" in x), "NO_RESULT")
    summary = {"agent": agent, "task": task, "verdict": verdict,
               "fails": [x for x in lines if x.get("status") == "FAIL"],
               "warns": [x for x in lines if x.get("status") == "WARN"],
               "n_checks": sum(1 for x in lines if "check" in x), "exit_code": res.get("exit_code")}
    (out / "probe_result.json").write_text(json.dumps({"summary": summary, "checks": lines}, indent=1))
    return summary
