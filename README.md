# SIGA: Simulator-Interface Grounding Adapters

Code and tasks for **"Simulator-Interface Grounding Adapters for Scientific Simulation Setup: A
Geophysics Case Study"** (NeurIPS 2026).

SIGA is a small adapter around an off-the-shelf coding agent that supplies a scientific
simulator's executable contract, so the agent can write valid input decks without a bespoke
agent loop. It plugs into three harness interfaces and changes nothing else: retrieval and a
validator as tools (**R**, **X**), a validation-gated stop hook (**S**), and a procedural-memory
cheatsheet in the system prompt (**M**). Because the adapter is small and external, it can also
be self-evolved from prior trajectories (**SE**). This repository has the adapter for
[GEOS](https://github.com/GEOS-DEV/GEOS) (built for Claude Code), the 27-task GEOS input-deck
benchmark, and the TreeSim scorer.

> **What you can and cannot rerun yet**
> - **R needs a retrieval database that is not shipped, and its build script is not included
>   yet.** Cells with R (R+M, R+S, R+X, R+S+X+M) cannot be rerun as-is. The expected database
>   schema is under "R: retrieval" below.
> - Every other paper cell (vanilla, S+M, X+M, S+X, S+X+M, SE, SE-prose) runs through the benchmark
>   sandbox: `siga-bench run --agent siga --cell ...`.
> - The Harbor export of the tasks is **untested under Harbor**.

## Repository layout

```
plugin/                     SIGA, the hand-designed adapter (a Claude Code plugin)
  hooks/verify_outputs.py     S: validation Stop hook
  hooks/hooks.json            S: hook registration (used with --plugin-dir)
  scripts/xmllint_mcp.py      X: validator MCP tool (xmllint --schema against the GEOS XSD)
  scripts/geos_rag_mcp.py     R: retrieval MCP server (ChromaDB; three search tools)
  memory_primer_dsv4_m1u.md   M: the procedural-memory cheatsheet
  GEOS_PRIMER_contract.md     the GEOS primer used in every paper cell
  prompts/                    the rest of the paper's system/user prompt text
  .claude-plugin/plugin.json  plugin manifest
plugin_evolving/v3/         SE, the self-evolved adapter (round 3)
src/eval/judge_geos.py      TreeSim, the paper scorer (default)
src/eval/judge_geos_fixed.py  TreeSim with five bug fixes
benchmarks/siga-geos/       the benchmark
  tasks/                      27 Harbor task dirs (+ manifest.json)
  bin/siga-bench, siga_bench/ the runner: sandbox, agents (pi, codex, claude-code, siga), leak probe
  siga_bench/cells.py         how each SIGA cell configures Claude Code
  sandbox/Dockerfile          agent userland for the sandbox
  docs/SCORING.md             the scorers: differences, floors, known weaknesses
  README.md                   benchmark details: isolation, metrics.json, Harbor format
scripts/siga_cell.py        writes a cell's files for running in your own isolated container
tests/                      pytest suite (no GEOS, Docker or network needed)
```

## Install

Requirements: Linux, Python 3.10+, and a GEOS source checkout at the commit the task block
lists were computed against. The runner and the scorers use only the Python standard library.

```bash
git clone https://github.com/matt-seb-ho/siga.git && cd siga
python3 -m venv .venv && . .venv/bin/activate && pip install pytest
pytest                                            # ~15 s, no GEOS needed

git clone https://github.com/GEOS-DEV/GEOS.git /path/to/GEOS
git -C /path/to/GEOS checkout 498d8e33877a1c5539cc3f180c0991dd6189dea1
export SIGA_GEOS_SRC=/path/to/GEOS                # read-only; never modified
```

To run agents you also need [bubblewrap](https://github.com/containers/bubblewrap) (`bwrap`) and
the sandbox userland, which pins Claude Code 2.1.119 (the paper's version), uv, and the MCP
servers' Python dependencies. From the repository root:

```bash
docker build -t siga-agent benchmarks/siga-geos/sandbox
mkdir -p rootfs && docker export "$(docker create siga-agent)" | tar -x -C rootfs
export SIGA_ROOTFS=$PWD/rootfs
```

pi and Codex are bound in from the host (`SIGA_PI_NODE`, `SIGA_PI_PKG`, `SIGA_CODEX_PKG`,
`SIGA_CODEX_AUTH`; see `benchmarks/siga-geos/siga_bench/config.py`).

## Run a task

Every agent runs through `siga-bench`, in a `bwrap` sandbox that sees only:
- the task's filtered GEOS tree at `/geos_lib` (no git history, no reference deck or near-copies);
- an empty `/workspace`;
- the agent's own toolchain and, for SIGA cells, the adapter directory.

The repository, the task directories and their reference decks are never mounted. The only network
exit is a host-side gate or proxy that allows the model API and nothing else. Each run dir gets a
`metrics.json` with the score, tokens, cost, turns, tool calls and any leak-hunting commands.

```bash
cd benchmarks/siga-geos
bin/siga-bench tasks --split val                      # the 17 val tasks (or heldout, all)
```

### Claude Code with SIGA (the paper's cells)

```bash
export ANTHROPIC_AUTH_TOKEN=... SIGA_CLAUDE_TOKEN_VAR=ANTHROPIC_AUTH_TOKEN
bin/siga-bench run --agent siga --cell S+X+M --model deepseek-v4-flash \
    --base-url https://api.deepseek.com/anthropic --task ExampleMandel --seed 1 --timeout 1500 --out runs/sxm-mandel-1
```

- **Cells:** `vanilla`, any subset of `RSXM` (`S+X`, `R+S+X+M`, ...), `SE` and `SE-prose`. The
  paper ran `deepseek-v4-flash` in Claude Code 2.1.119, three runs per cell, with a 1500 s timeout.
- **What the agent sees:** only the adapter directory (`plugin/`, or `plugin_evolving/v3/` for
  SE), read-only at `/plugins/siga`. The cell's Stop-hook settings and MCP config are written into
  the agent's home. The prompts and flags follow the paper's runner (`siga_bench/cells.py`).
- **Network:** the proxy allows only the `--base-url` host.
- **Tools (differs from the paper):** web and sub-agent tools are disallowed by default. The paper
  disallowed only Skill and AskUserQuestion; `--paper-tools` restores that, but model-side web
  search could then reach GitHub, which hosts every reference deck.
- **R cells** also need `--vector-db DIR` (see "R: retrieval"). The database is mounted read-only,
  so, as in the paper, the agent could read it directly. The leak probe warns about this.
- **Check isolation** before a batch: `bin/siga-bench probe --agent siga --cell S+X+M --model m
  --task ExampleMandel --out /tmp/probe` must print `"verdict": "PASS"`.

`scripts/siga_cell.py` writes the same configuration as files, for running Claude Code in a
container you manage. **Its `run.sh` is not sandboxed.** Use it only inside an isolated container
that has a copy of `plugin/` (never the repository) at `/plugins/siga`. `run.sh` refuses to start
if any of the task's reference decks, or any task, reference or solution directory, is visible.

### Bare agents

```bash
export OPENROUTER_API_KEY=...
bin/siga-bench run --agent pi --model <openrouter-model-id> --task ExampleMandel --seed 1 --out runs/pi-1
bin/siga-bench run --agent codex --model <codex-model> --effort max --task ExampleMandel --seed 1 --out runs/codex-1
bin/siga-bench run --agent claude-code --model <model-id> --task ExampleMandel --seed 1 --out runs/cc-1   # experimental
```

These run each harness without any SIGA component, on the same prompt (`instruction.md`). pi and
codex are the tested adapters. The **claude-code adapter is experimental and not validated**: in
its one smoke run it stayed isolated but timed out without writing a deck. Through OpenRouter it
reports no tokens or cost unless Claude Code exits cleanly. The pi gate sends
`HTTP-Referer: https://github.com/matt-seb-ho/siga` and `X-Title: siga-bench` to OpenRouter.

Score any deck: `bin/siga-bench verify --task ExampleMandel --generated DECK_DIR --out OUT_DIR`.
Details: [`benchmarks/siga-geos/README.md`](benchmarks/siga-geos/README.md).

## Scorers

TreeSim (paper appendix "TreeSim") scores the generated deck directory against the reference deck
directory; a missing or unparseable deck scores 0. Two versions ship:

| scorer | file | use |
|---|---|---|
| `paper` (default) | `src/eval/judge_geos.py` | the version behind every number in the paper |
| `fixed` | `src/eval/judge_geos_fixed.py` | fixes include double-counting, order-dependent matching, split-vs-flattened decks, whitespace in GEOS arrays, and `.5` as a number |

Switch with an environment variable or a flag. Both work for `siga-bench run`, `verify`, `oracle`
and `recollect`, and for each task's `tests/score.py` and Harbor `tests/test.sh`:

```bash
export SIGA_SCORER=fixed                                  # or: --scorer fixed
bin/siga-bench oracle --task ExampleMandel --out /tmp/o   # the reference scores 1.0 under both
```

Scores from the two versions are not directly comparable. Read a score against the floors: copying
the closest visible GEOS example scores about 0.60 (val) and 0.49 (held-out) under the paper
scorer, and about 0.65 and 0.54 under the fixed one. An empty deck scores about 0.15–0.18.
[`benchmarks/siga-geos/docs/SCORING.md`](benchmarks/siga-geos/docs/SCORING.md) has the
differences, the per-task floors and the scorer's known weaknesses.

## SIGA components and files

| component | paper | file(s) | how a cell wires it into Claude Code |
|---|---|---|---|
| **R** retrieval | MCP server with three search tools over GEOS docs, XSD entries and example decks | `plugin/scripts/geos_rag_mcp.py` | `--mcp-config` server `geos-rag`; the system prompt gets `plugin/prompts/rag_instructions.txt`. **Needs a database that is not shipped.** |
| **S** validation stop hook | blocks termination until the deck exists, parses, and (with X) validates; returns the errors | `plugin/hooks/verify_outputs.py` | Stop hook in `--settings`; `GEOS_HOOK_XMLLINT=1` adds the schema check when X is on; at most `GEOS_HOOK_MAX_RETRIES` (2) blocks |
| **X** validator tool | the same check, callable while drafting | `plugin/scripts/xmllint_mcp.py` | `--mcp-config` server `xmllint`, tool `validate_geos_xml` |
| **M** procedural memory | LLM-distilled cheatsheet appended to the system prompt | `plugin/memory_primer_dsv4_m1u.md` | `--append-system-prompt` |
| primer | harness contract + GEOS primer, in every cell | `plugin/prompts/agents_contract.md`, `plugin/GEOS_PRIMER_contract.md` | `--append-system-prompt` |
| **SE** self-evolved adapter | agent-rewritten primer, cheatsheet, skills and a sub-agent; S and X unchanged | `plugin_evolving/v3/` | primer `v3/PRIMER.md`, S and X from `v3/`, no R; skills and the sub-agent are not loaded (the paper disabled skill invocation) |
| **SE-prose** | SE's primer and cheatsheet in an S+X cell | `plugin_evolving/v3/PRIMER.md`, `v3/memory/cheatsheet.md` | as S+X, with those two files |

Notes on the shipped files:
- The M cheatsheet (`plugin/memory_primer_dsv4_m1u.md`) is the file every paper M cell loaded.
  An LLM distilled it from training trajectories, and it names some elements that do not exist in
  GEOS (for example `FractureManager`). It is kept verbatim because it is what the experiments used.
- The prompt files are verbatim from the paper's runner. `rag_instructions.txt` names
  `repo3-plugin:geos-rag`; `repo3` was the plugin's internal name.
- The literal `<file>` placeholders in `plugin_evolving/v3/` are verbatim. The self-evolution loop
  replaced XML file names with `<file>` in what the agent wrote, so the evolved adapter could not
  carry task file names.
- `plugin_evolving/v3/.claude-plugin/plugin.json` is a wrapper written for this release.

`plugin/` is also a regular Claude Code plugin: `claude --plugin-dir plugin` loads S (via
`hooks/hooks.json`) and the R and X servers (via `.claude-plugin/plugin.json`) at once. The paper
did not load it that way. It registered each component explicitly, so cells differ only in the
components they enable; `siga_bench/cells.py` does the same.

Environment variables read by the components:

| variable | used by | meaning |
|---|---|---|
| `GEOS_HOOK_XMLLINT` | S | `1`: also run `xmllint --schema` (the paper sets it when S and X are both on) |
| `GEOS_HOOK_SCHEMA_PATH`, `XMLLINT_SCHEMA_PATH` | S, X | GEOS XSD (default `/geos_lib/src/coreComponents/schema/schema.xsd`) |
| `GEOS_HOOK_INPUTS_DIR`, `GEOS_HOOK_MAX_RETRIES`, `GEOS_HOOK_DISABLE` | S | deck dir (default `/workspace/inputs`), block budget, kill switch |
| `GEOS_VECTOR_DB_DIR` | R | ChromaDB directory |
| `OPENROUTER_API_KEY`, `OPENROUTER_API_BASE`, `GEOS_EMBEDDING_MODEL_NAME` | R | query-embedding API (default model `qwen/qwen3-embedding-8b`, the one the paper's collections use) |
| `EXCLUDED_GT_XML_FILENAMES`, `EXCLUDED_RST_PATHS` | R | per-task result filters (the reference deck and source tutorial); cells fill them from the task's block list |

### R: retrieval

**Not reproducible from this release yet:** neither the database nor its build script is
included. R expects a ChromaDB persistent directory with three collections, all embedded with
`qwen/qwen3-embedding-8b` (4096 dimensions) through an OpenAI-compatible embeddings API. The
paper's database held 1,155 documents in total.

| collection | one document per | metadata used by the server |
|---|---|---|
| `geos_navigator` | chunk of GEOS RST documentation | `title`, `breadcrumbs`, `chunk_type`, `source_path` |
| `geos_technical` | short natural-language description ("shadow text") of an example XML snippet | `title`, `xml_reference` (path under `/geos_lib/inputFiles/`), `line_range`, `breadcrumbs`, `source_path` |
| `geos_schema` | element of the GEOS XSD | `element_name`, `title`, `attribute_count` |

`/opt/siga/venv/bin/python plugin/scripts/geos_rag_mcp.py --smoke` (inside the agent image), or
`uv run --script plugin/scripts/geos_rag_mcp.py --smoke`, checks that a database has the three
collections. To keep R from leaking the answer:
- build the collections from the same GEOS commit;
- let the server filter each task's blocked files (the `EXCLUDED_*` variables above);
- keep in mind that an agent with filesystem access to the database can read it directly.

## Add an agent to siga-bench

Write a class in `benchmarks/siga-geos/siga_bench/adapters/` that subclasses `base.Adapter`, and
register it in `adapters/__init__.py`. The contract is in `adapters/base.py`; `pi.py` is a short
example.

| method | job |
|---|---|
| `setup(ctx)` | Write the agent's config into `ctx.home` (the sandbox's `/home/agent`). |
| `services(ctx)` | Start the host side of the network: a gate or proxy on a socket in `ctx.sock_dir`. Return the `Popen`s. |
| `sandbox(ctx, spec)` | Add read-only binds (your binary), `PATH` entries and env vars. Never bind the repository or a task dir. |
| `command(ctx)` | Return the argv to run in the sandbox. The prompt is `ctx.prompt`, identical for every agent. Wrap it with `sandbox.with_relay(sock, argv)` so `127.0.0.1:8080` reaches your service. |
| `collect(ctx)` | Parse `ctx.agent_dir/events.jsonl` (your stdout) and logs into tokens, `usd`, `tool_calls`, `turns`, `exit_reason` and `commands`. |
| `finalize(ctx)` | Optional cleanup, for example credential copy-back. |

The runner owns the rest: the filtered tree, the sandbox, the timeout, verification and
`metrics.json`. Before trusting a new adapter, run `siga-bench probe --agent <yours>` and check
that it prints `"verdict": "PASS"`. `adapters/siga.py` shows how to add an extra read-only
directory.

## Citation

```bibtex
@inproceedings{ho2026siga,
  title={Simulator-Interface Grounding Adapters for Scientific Simulation Setup: A Geophysics Case Study},
  author={Ho, Matthew and Liu, Brian and Chen, Jixuan and Qin, Lianhui},
  booktitle={Advances in Neural Information Processing Systems},
  year={2026}
}
```

## License

MIT ([`LICENSE`](LICENSE)), except the GEOS example decks under
`benchmarks/siga-geos/tasks/*/tests/reference/` and `*/solution/inputs/`, which are unmodified
GEOS files under LGPL-2.1 ([`NOTICE`](NOTICE), [`THIRD_PARTY.md`](THIRD_PARTY.md)).
