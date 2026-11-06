"""Paths, task sets and defaults. Host-specific paths come from environment variables.

Required for `run`, `probe` and `leakscan` (not for `tasks`, `verify`, `oracle`):

  SIGA_GEOS_SRC    a GEOS source checkout at GEOS_UPSTREAM_COMMIT (no build needed).
                   The runner never modifies it; it builds a filtered copy per task.
  SIGA_ROOTFS      an unpacked root filesystem of the agent image
                   (benchmarks/siga-geos/sandbox/Dockerfile); must contain usr/ and etc/.

Optional:

  SIGA_CACHE       where filtered GEOS trees are cached (default ~/.cache/siga-bench).
                   Files are hardlinked when SIGA_CACHE is on the same filesystem as
                   SIGA_GEOS_SRC and copied otherwise.
  SIGA_PI_NODE     a Node.js install (dir with bin/node) for the pi agent
  SIGA_PI_PKG      the pi coding agent package (dir with bin/pi)
  SIGA_CODEX_PKG   the Codex CLI npm install (dir with node_modules/.bin/codex)
  SIGA_CODEX_AUTH  Codex auth.json (default ~/.codex/auth.json)
"""
from __future__ import annotations

import os
from pathlib import Path

BENCH_ROOT = Path(__file__).resolve().parents[1]          # benchmarks/siga-geos
REPO_ROOT = BENCH_ROOT.parents[1]                          # the repository root
TASKS_DIR = BENCH_ROOT / "tasks"

# Upstream GEOS commit the task block lists were computed against; the Harbor
# Dockerfiles clone this commit. Use the same commit for SIGA_GEOS_SRC.
GEOS_UPSTREAM_COMMIT = "498d8e33877a1c5539cc3f180c0991dd6189dea1"
GEOS_UPSTREAM_URL = "https://github.com/GEOS-DEV/GEOS.git"


def _env_path(name: str, default: Path | None = None) -> Path | None:
    v = os.environ.get(name)
    return Path(v).expanduser() if v else default


class ConfigError(RuntimeError):
    """A required host path is not configured."""


def require(name: str, value: Path | None, what: str) -> Path:
    if value is None:
        raise ConfigError(f"{name} is not set: point it at {what} (see siga_bench/config.py)")
    return value


# GEOS source tree the sandbox exposes (filtered per task) at /geos_lib.
GEOS_SRC = _env_path("SIGA_GEOS_SRC")
# Agent userland: an unpacked rootfs of sandbox/Dockerfile (Ubuntu 24.04; python3, node 22,
# xmllint, git, curl, ripgrep, Claude Code).
ROOTFS = _env_path("SIGA_ROOTFS")
# Read-only toolchains bound into the sandbox.
PI_NODE = _env_path("SIGA_PI_NODE")
PI_PKG = _env_path("SIGA_PI_PKG")
CODEX_PKG = _env_path("SIGA_CODEX_PKG")
CODEX_AUTH = _env_path("SIGA_CODEX_AUTH", Path.home() / ".codex" / "auth.json")
# Writable scratch: cached filtered GEOS trees.
CACHE = _env_path("SIGA_CACHE", Path.home() / ".cache" / "siga-bench")

# Task sets used in the SIGA paper (App. "Task pool, splits, and hygiene").
VAL17 = [
    "AdvancedExampleCasedContactThermoElasticWellbore",
    "AdvancedExampleDeviatedElasticWellbore",
    "AdvancedExampleDruckerPrager",
    "AdvancedExampleExtendedDruckerPrager",
    "AdvancedExampleModifiedCamClay",
    "AdvancedExampleViscoDruckerPrager",
    "buckleyLeverettProblem",
    "ExampleDPWellbore",
    "ExampleEDPWellbore",
    "ExampleIsothermalLeakyWell",
    "ExampleMandel",
    "ExampleThermalLeakyWell",
    "ExampleThermoporoelasticConsolidation",
    "kgdExperimentValidation",
    "pknViscosityDominated",
    "TutorialPoroelasticity",
    "TutorialSneddon",
]
HELDOUT10 = [
    "AdvancedExampleCasedThermoElasticWellbore",
    "AdvancedExamplePureThermalDiffusionWellbore",
    "AdvancedExampleThermoPoroElasticWellbore",
    "AdvancedExampleViscoExtendedDruckerPrager",
    "ExampleIsothermalHystInjection",
    "ExampleMCCWellbore",
    "ExampleProppantTest",
    "ExamplesingleFracCompression",
    "ExampleVerticalPoroElastoPlasticWellbore",
    "TutorialHydraulicFractureWithAdvancedXML",
]
SPLITS = {"val": VAL17, "heldout": HELDOUT10, "all": VAL17 + HELDOUT10}

DEFAULT_AGENT_TIMEOUT_S = 1800   # the SIGA paper used 1500 s; +300 s for high-effort reasoning models
DEFAULT_VERIFIER_TIMEOUT_S = 300


def task_id(name: str) -> str:
    """Harbor-friendly id: lowercase, '-'-safe. Kept 1:1 with the SIGA task name."""
    return name.lower()


def task_dir(name_or_id: str) -> Path:
    tid = name_or_id.lower()
    d = TASKS_DIR / tid
    if not d.is_dir():
        raise FileNotFoundError(f"no task dir {d}; see `siga-bench tasks`")
    return d
