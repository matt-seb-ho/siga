#!/usr/bin/env python3
"""SIGA verifier: score a generated GEOS deck against the reference with TreeSim.

Shipped into every task as tests/score.py next to two vendored copies of the
TreeSim scorer (stdlib only):

  tests/judge_geos_paper.py   the scorer used for every number in the SIGA paper
                              (identical to src/eval/judge_geos.py)
  tests/judge_geos_fixed.py   the same scorer with five bug fixes
                              (identical to src/eval/judge_geos_fixed.py;
                              see benchmarks/siga-geos/docs/SCORING.md)

The paper scorer is the default. Select the fixed one with ``--scorer fixed`` or
the environment variable ``SIGA_SCORER=fixed``. Used by Harbor's tests/test.sh and
by the local runner, so both paths compute the same number.

    python3 score.py --reference /tests/reference --generated /workspace/inputs --out /logs/verifier

Writes <out>/reward.json ({"reward": treesim}), <out>/reward.txt and
<out>/score_details.json. Failures count as 0 (the paper's failures-as-zero rule):
no XML, unparseable XML, or a scorer exception -> reward 0 with "failure" set.
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

SCORERS = {"paper": "judge_geos_paper", "fixed": "judge_geos_fixed"}
DEFAULT_SCORER = "paper"


def load_scorer(name: str | None = None):
    name = (name or os.environ.get("SIGA_SCORER") or DEFAULT_SCORER).strip().lower()
    if name not in SCORERS:
        raise SystemExit(f"unknown scorer {name!r}; choose one of {sorted(SCORERS)}")
    return name, importlib.import_module(SCORERS[name])


def score(reference: Path, generated: Path, scorer: str | None = None) -> dict:
    name, jg = load_scorer(scorer)
    out: dict = {"reward": 0.0, "failure": None, "sections": {}, "scorer": name}
    if not generated.is_dir() or not any(generated.rglob("*.xml")):
        out["failure"] = "no_xml"
        return out
    try:
        res = jg.evaluate_directories(reference, generated)
    except Exception as e:  # parse error etc. -> 0
        out["failure"] = f"{type(e).__name__}: {str(e)[:300]}"
        return out
    out["reward"] = float(res.get("treesim") or 0.0)
    out["sections"] = res.get("treesim_section_scores") or {}
    out["n_generated_xml"] = len(list(generated.rglob("*.xml")))
    prim = primary_score(jg, reference, generated)
    out["reward_primary"] = out["reward"] if prim is None else prim
    return out


def primary_score(jg, reference: Path, generated: Path):
    """Diagnostic, not the reward: TreeSim against the reference without its *smoke* decks.
    In 10 of 27 tasks the reference includes smoke decks, so in 7 of them a correct
    single deck scores ~0.5 on the headline (paper-faithful) metric; see benchmarks/siga-geos/docs/SCORING.md."""
    keep = [f for f in reference.glob("*.xml") if "smoke" not in f.name.lower()]
    if not keep or len(keep) == len(list(reference.glob("*.xml"))):
        return None
    with tempfile.TemporaryDirectory() as td:
        for f in keep:
            shutil.copy2(f, Path(td) / f.name)
        try:
            return float(jg.evaluate_directories(Path(td), generated).get("treesim") or 0.0)
        except Exception:
            return 0.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reference", required=True, type=Path)
    ap.add_argument("--generated", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--scorer", choices=sorted(SCORERS), default=None,
                    help=f"TreeSim version (default: $SIGA_SCORER or {DEFAULT_SCORER!r})")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    r = score(a.reference, a.generated, a.scorer)
    (a.out / "reward.json").write_text(json.dumps({"reward": round(r["reward"], 6)}))
    (a.out / "reward.txt").write_text(f"{r['reward']:.6f}\n")
    (a.out / "score_details.json").write_text(json.dumps(r, indent=1))
    print(json.dumps({"reward": r["reward"], "failure": r["failure"], "scorer": r["scorer"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
