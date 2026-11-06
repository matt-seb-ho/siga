"""siga-bench CLI.

  siga-bench tasks [--split val|heldout|all]
  siga-bench run --agent {pi,codex,claude-code,siga} --model M --task T --seed S --out DIR
                 [--timeout S] [--effort max] [--thinking medium] [--cap-usd 3]
                 [--base-url URL] [--scorer paper|fixed]
                 [--cell CELL [--vector-db DIR] [--paper-tools]]          (--agent siga: a SIGA cell)
  siga-bench probe --agent A --model M --task T --out DIR [--cell CELL ...]  (leak probe in the real sandbox)
  siga-bench verify --task T --generated DIR [--out DIR] [--scorer paper|fixed]   (score a deck)
  siga-bench oracle --task T --out DIR [--scorer paper|fixed]      (reference through the verifier)
  siga-bench tree --task T                                         (build + print the filtered GEOS tree)
  siga-bench leakscan [--split all] [--json FILE]                  (static near-copy scan)
  siga-bench recollect RUN_DIR... [--scorer paper|fixed]           (rebuild metrics.json)

The scorer defaults to $SIGA_SCORER, else "paper" (the TreeSim version behind the
SIGA paper's numbers); "fixed" is the version with the five fixes in docs/SCORING.md.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from . import config

SCORER_CHOICES = ("paper", "fixed")


def _siga_opts(a) -> dict:
    o = {}
    if a.base_url:
        o["base_url"] = a.base_url
    if a.cell:
        o["cell"] = a.cell
    if a.vector_db:
        o["vector_db"] = a.vector_db
    if a.paper_tools:
        o["paper_tools"] = True
    return o


def main(argv=None) -> int:
    try:
        return _main(argv)
    except config.ConfigError as e:
        print(f"siga-bench: {e}", file=sys.stderr)
        return 2


def _main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="siga-bench", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("tasks"); t.add_argument("--split", default="all", choices=sorted(config.SPLITS))
    r = sub.add_parser("run")
    r.add_argument("--agent", required=True); r.add_argument("--model", required=True)
    r.add_argument("--task", required=True)
    r.add_argument("--seed", type=int, default=1); r.add_argument("--out", required=True, type=Path)
    r.add_argument("--timeout", type=int, default=None)
    r.add_argument("--effort", default="max", help="codex model_reasoning_effort")
    r.add_argument("--thinking", default="medium", help="pi thinking level")
    r.add_argument("--cap-usd", type=float, default=3.0, help="pi: per-run $ cap enforced by the gate")
    r.add_argument("--base-url", default=None, help="claude-code: Anthropic-compatible gateway URL")
    r.add_argument("--scorer", choices=SCORER_CHOICES, default=None)
    r.add_argument("--dry-run", action="store_true")
    p = sub.add_parser("probe")
    p.add_argument("--agent", required=True); p.add_argument("--model", required=True)
    p.add_argument("--task", required=True); p.add_argument("--out", required=True, type=Path)
    p.add_argument("--base-url", default=None)
    for q in (r, p):
        q.add_argument("--cell", default=None, help="siga: vanilla, any of R/S/X/M (e.g. S+X+M), SE, SE-prose")
        q.add_argument("--vector-db", default=None, help="siga, R cells: host ChromaDB dir (mounted read-only)")
        q.add_argument("--paper-tools", action="store_true",
                       help="siga: disallow only Skill and AskUserQuestion, as in the paper (web tools stay on)")
    v = sub.add_parser("verify")
    v.add_argument("--task", required=True); v.add_argument("--generated", required=True, type=Path)
    v.add_argument("--out", type=Path, default=None)
    v.add_argument("--scorer", choices=SCORER_CHOICES, default=None)
    o = sub.add_parser("oracle"); o.add_argument("--task", required=True); o.add_argument("--out", required=True, type=Path)
    o.add_argument("--scorer", choices=SCORER_CHOICES, default=None)
    tr = sub.add_parser("tree", help="build the task's filtered GEOS tree and print its path")
    tr.add_argument("--task", required=True)
    ls = sub.add_parser("leakscan"); ls.add_argument("--split", default="all", choices=sorted(config.SPLITS))
    ls.add_argument("--json", type=Path)
    rc = sub.add_parser("recollect", help="rebuild metrics.json of finished run dirs")
    rc.add_argument("dirs", nargs="+", type=Path)
    rc.add_argument("--scorer", choices=SCORER_CHOICES, default=None)
    a = ap.parse_args(argv)
    if a.cmd == "recollect":
        from .runner import recollect
        for d in a.dirs:
            m = recollect(d, a.scorer)
            print(d, m["score"], m["scorer"], m["usd"], m["turns"], m["tool_calls"], m["exit_reason"])
        return 0

    if a.cmd == "tasks":
        for n in config.SPLITS[a.split]:
            print(f"{config.task_id(n)}\t{n}")
        return 0
    if a.cmd == "run":
        from . import runner
        opts = {"effort": a.effort, "thinking": a.thinking, "cap_usd": a.cap_usd}
        opts.update(_siga_opts(a))
        m = runner.run(a.agent, a.model, a.task, a.seed, a.out, a.timeout, opts, dry_run=a.dry_run,
                       scorer=a.scorer)
        print(json.dumps({k: m.get(k) for k in ("task", "score", "scorer", "exit_reason", "turns", "tool_calls",
                                                "tokens_in", "tokens_out", "usd", "wall_s",
                                                "infra_failure")} if not a.dry_run else m, indent=1))
        return 0
    if a.cmd == "probe":
        from .probe.probe import probe
        s = probe(a.agent, a.task, a.out, a.model, _siga_opts(a))
        print(json.dumps(s, indent=1))
        return 0 if s["verdict"] == "PASS" else 1
    if a.cmd == "verify":
        from .runner import verify
        td = config.task_dir(a.task)
        out = a.out or (a.generated.parent / "verifier")
        print(json.dumps(verify(td, a.generated, out, a.scorer), indent=1))
        return 0
    if a.cmd == "oracle":
        from .runner import verify
        td = config.task_dir(a.task)
        gen = a.out / "workspace" / "inputs"
        shutil.copytree(td / "solution" / "inputs", gen, dirs_exist_ok=True)
        res = verify(td, gen, a.out / "verifier", a.scorer)
        print(json.dumps({"task": a.task, "scorer": res.get("scorer"), "reward": res["reward"],
                          "failure": res["failure"]}))
        return 0 if res["reward"] > 0.99 else 1
    if a.cmd == "tree":
        from . import geostree
        print(geostree.filtered_tree(config.task_dir(a.task)))
        return 0
    if a.cmd == "leakscan":
        from . import leakscan
        idx = leakscan.index_tree(config.require("SIGA_GEOS_SRC", config.GEOS_SRC, "a GEOS source checkout"))
        res = [leakscan.scan_task(n, idx) for n in config.SPLITS[a.split]]
        for r in res:
            print(r["task"], [(h["path"], h["coverage"]) for h in r["top"][:3]])
        if a.json:
            a.json.write_text(json.dumps(res, indent=1))
        return 0
    return 2
