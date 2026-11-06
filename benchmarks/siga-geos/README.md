# siga-geos: the SIGA GEOS input-deck benchmark

An agent gets a natural-language description of a GEOS simulation and the GEOS source tree
(examples, docs, schema). It must write the XML input deck. The deck is scored against the
reference deck with TreeSim, a tree-similarity score in [0, 1]. A missing or unparseable deck
scores 0.

There are 27 tasks: the SIGA paper's 17 validation tasks (`val`) and its 10 held-out tasks
(`heldout`). Each task is a [Harbor](https://github.com/harbor-framework/harbor) task directory
under `tasks/`; `tasks/manifest.json` lists them and their splits.

`siga-bench` runs any supported agent on any task in an isolated sandbox and writes one common
`metrics.json`. `pi`, `codex` and `claude-code` run the bare agent harness. `siga` runs Claude Code
with a SIGA adapter cell (see the top-level README). Commands below run from `benchmarks/siga-geos/`,
except where noted.

> The Harbor export (`tasks/*/task.toml`, `environment/`, `tests/test.sh`) is **untested under
> Harbor**. The local runner (`siga-bench`) is what has been tested.

## Setup

```bash
git clone https://github.com/GEOS-DEV/GEOS.git /path/to/GEOS
git -C /path/to/GEOS checkout 498d8e33877a1c5539cc3f180c0991dd6189dea1   # the commit the block lists use
export SIGA_GEOS_SRC=/path/to/GEOS            # read-only; never modified

docker build -t siga-agent sandbox      # agent userland (Claude Code 2.1.119, uv, MCP deps pinned)
mkdir -p rootfs && docker export "$(docker create siga-agent)" | tar -x -C rootfs
export SIGA_ROOTFS=$PWD/rootfs
```

The runner needs Linux with [bubblewrap](https://github.com/containers/bubblewrap) (`bwrap`) and
Python 3.10+ (standard library only). `SIGA_CACHE` (default `~/.cache/siga-bench`) holds the
filtered GEOS trees; files are hardlinked when it is on the same filesystem as `SIGA_GEOS_SRC`.
Agent toolchains: `SIGA_PI_NODE` + `SIGA_PI_PKG` (pi), `SIGA_CODEX_PKG` + `SIGA_CODEX_AUTH` (Codex).
All variables are documented in `siga_bench/config.py`.

## Run one task

```bash
export OPENROUTER_API_KEY=...      # pi and claude-code
bin/siga-bench run --agent pi    --model <openrouter-model-id> --task ExampleMandel --seed 1 --out runs/pi-mandel-1
bin/siga-bench run --agent codex --model <codex-model> --effort max --task ExampleMandel --seed 1 --out runs/codex-mandel-1
bin/siga-bench run --agent claude-code --model <model-id> --task ExampleMandel --seed 1 --out runs/cc-mandel-1   # experimental
bin/siga-bench run --agent siga --cell S+X+M --model <model-id> --base-url <anthropic-compatible-url> \
    --task ExampleMandel --seed 1 --out runs/sxm-mandel-1                                                  # SIGA cell
```

- `--agent`: `pi`, `codex`, `claude-code` or `siga`.
  - `siga` mounts only the adapter dir (`plugin/` or `plugin_evolving/v3/`) at `/plugins/siga`.
    `--cell` picks the cell, `--vector-db DIR` is needed for R cells, and `--paper-tools` keeps the
    web tools on, as in the paper.
  - **claude-code is experimental and not validated**:
  it runs and is isolated, but via OpenRouter it has no $ cap and no token counts on timeout, and
  its one smoke run timed out without a deck.
- `--timeout`: defaults to 1800 s. The paper used 1500 s.
- `--task` takes a SIGA name (`ExampleMandel`) or a task id (`examplemandel`).
- `--scorer paper|fixed`: which TreeSim version scores the deck (default `$SIGA_SCORER`, else `paper`).
- pi: `--cap-usd` (default 3) is enforced by the host-side gate; `--thinking` sets pi's thinking level.
- The run dir holds `metrics.json`, `run.json`, `workspace/inputs/` (the deck), `agent/`
  (trajectory and logs) and `verifier/`.

Other commands:

| command | what it does |
|---|---|
| `tasks --split val\|heldout\|all` | Lists the tasks. |
| `verify --task T --generated DIR [--out DIR] [--scorer S]` | Scores any deck directory (default `--out`: `DIR/../verifier`). |
| `oracle --task T --out DIR [--scorer S]` | Puts the reference deck through the verifier. It scores 1.0 on all 27 tasks under both scorers. |
| `tree --task T` | Builds the task's filtered GEOS tree (no VCS dirs, no blocked files) and prints its path. |
| `probe --agent A --model M --task T --out DIR` | Runs the leak probe inside the real sandbox for that agent. Must print `"verdict": "PASS"`. |
| `leakscan` | Static scan for near-copies of each reference in the visible GEOS tree. |
| `recollect RUN_DIR... [--scorer S]` | Rebuilds `metrics.json` from a finished run (e.g. to rescore with the other scorer). |

## metrics.json

| field | meaning |
|---|---|
| `score`, `scorer` | TreeSim against the full reference dir, and which scorer computed it. Failures count as 0. |
| `score_components` | Per-section TreeSim, `failure`, and `score_primary_no_smoke` (a diagnostic, described below). |
| `tokens_in` / `tokens_cached_in` | All prompt tokens (cached ones included) / the cached part. |
| `tokens_out` / `tokens_reasoning` | Completion tokens (reasoning included) / the reasoning part. |
| `usd`, `usd_basis` | `billed` for pi (cost reported by OpenRouter, logged by the gate). `list-price-estimate` for Codex. |
| `tool_calls`, `turns` | The paper's definitions. See "Turns and tool calls". |
| `wall_s`, `exit_reason`, `timed_out` | Run duration and how the run ended. |
| `infra_failure` | True on a rate limit or when the model was never reached. Rerun these; they are not agent failures. |
| `suspicious_commands` | Commands that look like leak-hunting (`git`, `curl`, `find /`, `auth.json`, ...). Read these before trusting a high score. |

Codex cost is an API-equivalent estimate from a per-model price table (`adapters/codex.py`,
`DEFAULT_PRICES`); override with `SIGA_PRICE_<MODEL>="in,cached,out"` ($ per million tokens).

### Turns and tool calls

| agent | turn | tool call |
|---|---|---|
| paper (Claude Code) | one stream-json `assistant` event | one `tool_use` block |
| claude-code | the same | the same |
| pi | one assistant `message_end` | one `toolCall` block |
| codex | one model response (`token_usage_record`) | one top-level `function_call`/`custom_tool_call` |

Recent Codex versions run shell commands inside a code-mode `exec` tool, so one tool call can run
several commands. The number of commands is reported separately as `extra.commands_executed`.

## Isolation: what the agent can reach

Each run is a `bwrap` sandbox:
- The userland is the image from `sandbox/Dockerfile` (Ubuntu 24.04 with python3, node 22,
  xmllint, git, curl and ripgrep), read-only.
- `/geos_lib` is the task's filtered GEOS tree, read-only. It has no `.git` and none of the task's
  blocked files (`environment/blocked_files.txt`: the reference deck, its variant siblings, its
  source tutorial, and the near-copies in `docs/extra_blocked.json`).
- `/workspace` is fresh for each run, and `/tmp` is a fresh tmpfs.
- The agent's own toolchain is mounted under `/opt`.
- The sandbox has its own network, pid, ipc and user namespaces and a cleared environment.
  Nothing else from the host is mounted.

The network has a single exit, a UNIX socket to a host-side service:
- **pi** reaches `net/llm_gate.py`. It accepts only `POST chat/completions` for the one model,
  strips web plugins, injects the key on the host (the key never enters the sandbox), and
  enforces the per-run $ cap.
- **codex** reaches `net/connect_proxy.py`, an HTTPS `CONNECT` proxy that allows only
  `chatgpt.com` and `*.openai.com` and logs every connection to `agent/net.jsonl`. Codex's own
  sandbox is off (it would let commands read the whole host filesystem); ours replaces it. Its
  config turns off web search, memories, plugins/apps, multi-agent, history and Codex's bundled
  skills. `CODEX_HOME` is per run, and `auth.json` is copied in, copied back only if Codex
  refreshed it, and deleted from the run dir afterwards.
- **claude-code** reaches the same CONNECT proxy, allowing only the gateway host. Its token is
  inside the sandbox (the probe reports this as a warning).
- **siga** is claude-code with these additions:
  - the adapter dir at `/plugins/siga`;
  - the image's `/opt/siga/venv`, the Python that runs the MCP servers;
  - for R cells, the database at `/opt/siga/vector_db` (all read-only).

  The proxy also allows the embedding API host in R cells. The leak probe scans `/plugins` like
  everything else (reference copies, reference lines, and a `benchmark_files` check for task,
  reference or solution dirs).

Leak checks are in `siga_bench/probe/leak_probe.sh`. The known residual: Codex holds a ChatGPT
token and may reach chatgpt.com, so in principle it could call the backend's own web tools by
hand. Such attempts show up in `suspicious_commands` and `net.jsonl`.

## Add your own agent

Write a class in `siga_bench/adapters/` that subclasses `base.Adapter`, and register it in
`adapters/__init__.py`. The contract is in `adapters/base.py`; `pi.py` is a short example.

| method | job |
|---|---|
| `setup(ctx)` | Write the agent's config into `ctx.home` (the sandbox's `/home/agent`). |
| `services(ctx)` | Start the host side of the network: a gate or proxy on a socket in `ctx.sock_dir`. Return the `Popen`s. |
| `sandbox(ctx, spec)` | Add read-only binds (your binary), `PATH` entries and env vars. |
| `command(ctx)` | Return the argv to run in the sandbox. The prompt is `ctx.prompt`, identical for every agent. Wrap it with `sandbox.with_relay(sock, argv)` so `127.0.0.1:8080` reaches your service. |
| `collect(ctx)` | Parse `ctx.agent_dir/events.jsonl` (your stdout) and logs into tokens, `usd`, `tool_calls`, `turns`, `exit_reason` and `commands`. |
| `finalize(ctx)` | Optional cleanup, for example credential copy-back. |

The runner owns the rest: the filtered tree, the sandbox, the timeout, verification and
`metrics.json`. Before trusting a new adapter, run `siga-bench probe --agent <yours>`.

## Harbor format

Each `tasks/<id>/` follows Harbor task schema 1.4 (harbor 0.25.0, https://www.harborframework.com/docs/tasks):

| file | contents |
|---|---|
| `task.toml` | Metadata, agent timeout 1800 s, verifier timeout 300 s, 4 CPUs and 8 GB. Agent network is `allowlist` (model APIs only). The verifier is `separate` with `no-network`, and the agent's `/workspace/inputs` is passed as an artifact. |
| `instruction.md` | The prompt: the primer sentence, the paths, the spec and a scope note. |
| `environment/Dockerfile` | Fetches GEOS at upstream commit `498d8e33`, then deletes `.git` and the blocked files in the same layer, so blocked files exist in no image layer. |
| `tests/test.sh` | Runs `score.py` with the scorer from `$SIGA_SCORER` (default `paper`) and writes `/logs/verifier/reward.json`. |
| `tests/score.py`, `tests/judge_geos_paper.py`, `tests/judge_geos_fixed.py` | The verifier and the two vendored scorers (stdlib only). |
| `solution/solve.sh` | The oracle: copies the reference deck. |

**Running under Harbor: UNTESTED.** This export has never been run under Harbor. Expect to fix
details such as the `artifacts` key, the verifier image, and how `/tests` is mounted. On a Docker host:

```bash
harbor run -p benchmarks/siga-geos/tasks -a oracle          # expect reward 1.0 everywhere
harbor run -p benchmarks/siga-geos/tasks/examplemandel -a codex -m <model>
```

To use the fixed scorer under Harbor, set `SIGA_SCORER=fixed` in the verifier environment, or
change the default in every `tests/test.sh`:
`sed -i 's/SIGA_SCORER:-paper/SIGA_SCORER:-fixed/' benchmarks/siga-geos/tasks/*/tests/test.sh`.

Before trusting a run, check:
- **`allowed_hosts` is a placeholder** (`set-your-model-api-host.invalid`), so an unedited task
  fails closed. Replace it with your agent's API host(s) and nothing else, for example
  `api.openai.com` (and `chatgpt.com`, `auth.openai.com` for a ChatGPT login) for Codex,
  `openrouter.ai` for pi, or your gateway for Claude Code. For example:
  `sed -i 's/"set-your-model-api-host.invalid"/"openrouter.ai"/' tasks/*/task.toml`.
  Never use `public`: GitHub hosts every reference deck.
- **Disable web search and web tools in the agent itself.** Under Harbor nothing strips
  server-side web search (OpenRouter `plugins` / `web_search_options`, Codex web search, Claude
  Code WebFetch/WebSearch) from the agent's requests, as `net/llm_gate.py` does in siga-bench, and
  the allowed model API host can fetch GitHub on the agent's behalf.
- The paper's local GEOS tree was upstream `498d8e33` plus local changes to file modes and some
  data tables (and to `buckleyLeverett_base.xml`, a reference that is blocked anyway), so a
  Docker tree can differ slightly from the one the paper's agents saw.
- Harbor's built-in agents don't apply the Codex configuration above (web search off and so on).
  Set it through the agent's own options.

## Known issues and design choices

`docs/SCORING.md` covers the scorers in full.

- **Two scorers.** `paper` is the TreeSim version behind every number in the SIGA paper. `fixed`
  corrects five bugs: include double-counting, order-dependent matching, split vs flattened decks,
  whitespace in GEOS arrays, and `.5` not parsed as a number. Numbers from the two are not
  directly comparable.
- **Smoke decks in the reference.** In 10 tasks the reference includes `*_smoke` decks. In 7 of
  them, a correct deck without the smoke deck scores about 0.5 on `score`.
  `score_primary_no_smoke` scores against the reference without its smoke decks.
- **Floors.** Copying the best visible example scores 0.60 (val) and 0.49 (held-out) under the
  paper scorer, and 0.65 and 0.54 under the fixed one. An empty deck scores 0.15–0.18. These were
  computed on the shipped references and block lists; read an agent's score against them.
- **Wrong values are cheap.** Six physics values off by 10× cost about 0.13. Extra decks cost little.
- **Same-case sibling decks stay visible**, as in the paper. An example is
  `PoroElastic_Mandel_benchmark_sequential.xml` for the Mandel task, whose reference is `_benchmark_fim`.
  Only decks that reproduce a reference at TreeSim ≥ 0.9 on their own are blocked
  (`docs/extra_blocked.json`): the `pknViscosityDominated_poroelastic_*` family, and
  `triaxialDriver_ExtendedDruckerPrager_basicExample.xml` for the ExtendedDruckerPrager task.
  These two extra blocks were added after the paper's runs.
- **Reference fix.** TutorialHydraulicFractureWithAdvancedXML's original ground-truth dir held a
  stray `hydraulicFracturing/` subdirectory of 59 unrelated decks. The reference here is the
  top-level files only, a change from the paper.
- **Scope note.** `instruction.md` ends with a short scope note (the deliverable is the deck; it
  is scored on structure). The paper's prompts did not include it. The `siga` agent and
  `scripts/siga_cell.py` use the paper's prompt construction instead (`siga_bench/cells.py`).
- **`task.toml` provenance fields.** `reference_sha256` is the first 16 hex digits of
  sha256 over each reference file's name followed by its bytes, in sorted file-name order.
  `spec_set = "v2"` is the paper's specification set. `exporter_version` is the version of the
  (unreleased) script that generated the task dirs.
