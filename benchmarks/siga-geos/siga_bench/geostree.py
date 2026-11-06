"""Per-task filtered GEOS trees: hardlink copies of the user's GEOS checkout without
the task's blocked files and without any VCS directory. Cached and reused read-only.
The GEOS source itself is never redistributed with this benchmark."""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from . import config

VCS = {".git", ".hg", ".svn"}


def blocked_list(task_dir: Path) -> list[str]:
    f = task_dir / "environment" / "blocked_files.txt"
    return [ln.strip() for ln in f.read_text().splitlines() if ln.strip()]


def build_filtered_tree(src: Path, blocked: list[str], dest: Path) -> None:
    blocked_set = {b.rstrip("/") for b in blocked}

    def ignore(d: str, names: list[str]) -> set[str]:
        rel_d = os.path.relpath(d, src)
        skip = set()
        for n in names:
            rel = n if rel_d == "." else f"{rel_d}/{n}"
            if n in VCS or rel in blocked_set:
                skip.add(n)
        return skip

    def link(s: str, d: str) -> None:
        try:
            os.link(s, d)
        except OSError:
            shutil.copy2(s, d)

    shutil.copytree(src, dest, ignore=ignore, copy_function=link, symlinks=True)
    # Escaping or dangling symlinks would point at host paths: drop them. Links that stay inside
    # the tree are rewritten as relative links, so they survive moving the tree.
    for p in dest.rglob("*"):
        if p.is_symlink():
            tgt = os.path.realpath(p)
            if not tgt.startswith(str(dest) + os.sep) or not os.path.exists(tgt):
                p.unlink()
            elif os.path.isabs(os.readlink(p)):
                rel = os.path.relpath(tgt, p.parent)
                p.unlink()
                p.symlink_to(rel)


def _source_version(src: Path) -> str:
    """The checkout's commit if it is a git repo, else the mtime of inputFiles/: part of the
    cache key, so switching the checkout to another commit never reuses a stale filtered tree."""
    try:
        r = subprocess.run(["git", "-C", str(src), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=30)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    try:
        return str((src / "inputFiles").stat().st_mtime_ns)
    except OSError:
        return "unknown"


def filtered_tree(task_dir: Path, src: Path = None) -> Path:
    """Return the cached filtered tree for this task (built on first use)."""
    src = src or config.require("SIGA_GEOS_SRC", config.GEOS_SRC, "a GEOS source checkout")
    blocked = blocked_list(task_dir)
    key = hashlib.sha256(("\n".join([str(src), _source_version(src)] + blocked)).encode()).hexdigest()[:12]
    root = config.CACHE / "geos_lib" / f"{task_dir.name}-{key}"
    if (root / ".complete").exists():
        return root / "geos"
    root.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(dir=root.parent, prefix=f".{task_dir.name}-"))
    build_filtered_tree(src, blocked, tmp / "geos")
    (tmp / ".complete").write_text("\n".join(blocked) + "\n")
    try:
        tmp.rename(root)
    except OSError:  # another process won the race
        shutil.rmtree(tmp, ignore_errors=True)
    return root / "geos"
