"""Static near-copy scan: does any file the agent can see reproduce the reference deck?

For each task, the reference deck's distinctive lines (normalized, >= 20 chars, holding
an attribute) are compared with every visible text file in the GEOS tree (the tree with
the task's blocked files, environment/blocked_files.txt, removed). A file "covers" the
reference to the fraction of those lines it contains. Lines that occur in more than
`common_k` visible files are boilerplate and are dropped first, so the score measures
task-specific content. The reference is the task's tests/reference/ dir.

    siga-bench leakscan [--split all] [--json out.json]      (needs SIGA_GEOS_SRC)
"""
from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

from . import config

TEXT_EXT = {".xml", ".rst", ".py", ".txt", ".md", ".json", ".yaml", ".yml", ".cpp", ".hpp",
            ".sh", ".cmake", ".in", ".csv", ".ats", ".inc", ".html", ".tex", ".ipynb"}
_WS = re.compile(r"\s+")


def norm_lines(text: str) -> set[str]:
    out = set()
    for ln in text.splitlines():
        s = _WS.sub(" ", ln.strip())
        if len(s) >= 20 and "=" in s:
            out.add(s.strip("/> "))
    return out


def index_tree(root: Path) -> dict[str, set[str]]:
    idx = {}
    for p in root.rglob("*"):
        rel = p.relative_to(root)
        if rel.parts and rel.parts[0] == ".git":
            continue
        if not p.is_file() or p.is_symlink():
            continue
        if p.suffix.lower() not in TEXT_EXT and p.suffix:
            continue
        try:
            if p.stat().st_size > 5_000_000:
                continue
            idx[str(rel)] = norm_lines(p.read_text(errors="ignore"))
        except OSError:
            continue
    return idx


def blocked_set(name: str) -> set[str]:
    f = config.task_dir(name) / "environment" / "blocked_files.txt"
    return {ln.strip().rstrip("/") for ln in f.read_text().splitlines() if ln.strip()}


def scan_task(name: str, idx: dict[str, set[str]], blocked: set[str] | None = None, common_k: int = 8,
              top: int = 5) -> dict:
    blocked = blocked_set(name) if blocked is None else blocked
    ref = set()
    for f in sorted((config.task_dir(name) / "tests" / "reference").rglob("*.xml")):
        ref |= norm_lines(f.read_text(errors="ignore"))
    visible = {k: v for k, v in idx.items()
               if k not in blocked and not any(k.startswith(b + "/") for b in blocked)}
    freq = defaultdict(int)
    for lines in visible.values():
        for ln in lines & ref:
            freq[ln] += 1
    distinct = {ln for ln in ref if freq[ln] <= common_k}
    hits = []
    if distinct:
        for rel, lines in visible.items():
            n = len(lines & distinct)
            if n:
                hits.append((n / len(distinct), n, rel))
    hits.sort(reverse=True)
    return {"task": name, "ref_lines": len(ref), "distinct_lines": len(distinct),
            "top": [{"path": r, "coverage": round(c, 3), "n": n} for c, n, r in hits[:top]]}
