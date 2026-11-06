# Scoring: TreeSim and its two versions

The benchmark's score is **TreeSim**, a tree similarity in [0, 1] between the deck an agent wrote
(every `*.xml` under its `/workspace/inputs/`) and the task's reference deck
(`tasks/<id>/tests/reference/`). The SIGA paper defines it in its appendix "TreeSim". In short:

- Each deck file is parsed and its `<Included>` files are resolved. All files of a deck are merged
  under one `<Problem>` root.
- Elements are matched to reference elements by tag, `name` and attributes, regardless of order.
- A node scores `0.3 × attribute similarity + 0.7 × mean child score`, minus a small penalty for
  extra children. Attribute values match case-insensitively; numbers match within a relative
  tolerance of 1e-6.
- **Failures score 0:** no XML file, or nothing parses. If some files parse and others don't, the
  broken files are skipped.

## Two versions

| `SIGA_SCORER` | file | what it is |
|---|---|---|
| `paper` (default) | `src/eval/judge_geos.py` | The version behind every number in the SIGA paper. |
| `fixed` | `src/eval/judge_geos_fixed.py` | The same scorer with the five fixes below. |

Each task vendors both, as `tests/judge_geos_paper.py` and `tests/judge_geos_fixed.py` (stdlib only).
Choose one with the environment variable or with a flag:

```bash
export SIGA_SCORER=fixed                         # or pass --scorer fixed
bin/siga-bench verify --task ExampleMandel --generated DECK_DIR --out OUT_DIR
python3 tasks/examplemandel/tests/score.py --scorer fixed --reference ... --generated ... --out ...
```

`metrics.json` and `score_details.json` record which scorer produced the score. Numbers from the
two versions are not directly comparable.

### What the fixed version changes

`tests/test_scorer.py` checks each of these on both versions; the paper version's failures are
marked as expected.

1. **Includes counted again.** In a directory with two or more entry decks (for example a
   `*_benchmark.xml` and a `*_smoke.xml` that both include `*_base.xml`, as most references do),
   the paper version also merges every *included* file as a deck of its own, so the base file's
   sections are counted three times. The fixed version merges only entry decks.
2. **Order-dependent matching.** Repeated blocks with nothing to tell them apart (two `<Solvers>`
   from two decks, say) tie on similarity, and the paper version breaks ties by position, so element
   order can change the score. The fixed version breaks ties by subtree score.
3. **Split vs flattened decks.** GEOS appends an included file's sections and merges repeated
   blocks. The fixed version does the same, so a base+benchmark pair and the same deck flattened
   into one file score alike.
4. **Whitespace in GEOS arrays.** The paper version compares arrays of strings and nested arrays as
   strings, so `{ shale }` ≠ `{shale}` and `{ { 0, 1 } }` ≠ `{{0,1}}`. The fixed version compares
   them token by token.
5. **`.5` as a number.** The paper version does not read `.5` (or `-.25`) as a number, so `0.5`
   vs `.5` is a mismatch. GEOS decks use this form.

Both versions score every reference deck 1.0 against itself (`siga-bench oracle`) and are
unaffected by attribute order, comments, indentation, `1e6` vs `1000000` and `1.0` vs `1`.

## Floors: read scores against these

| reference | split | copy-nearest, paper | copy-nearest, fixed | empty deck, paper | empty deck, fixed |
|---|---|---|---|---|---|
| full reference (`score`) | val (17) | 0.60 | 0.65 | 0.17 | 0.18 |
| full reference (`score`) | held-out (10) | 0.49 | 0.54 | 0.15 | 0.17 |
| without `*smoke*` decks (`score_primary_no_smoke`) | val (17) | 0.74 | 0.75 | 0.21 | 0.21 |
| without `*smoke*` decks (`score_primary_no_smoke`) | held-out (10) | 0.63 | 0.64 | 0.19 | 0.20 |

- **Copy-nearest** is the score of the single best GEOS example deck the agent can see (with its
  included files), chosen with knowledge of the reference. It is an upper bound on "copy an example
  without editing it". Visibility follows each task's `environment/blocked_files.txt`, and blocked
  included files are dropped.
- **Empty deck** is a `<Problem>` holding the eleven standard sections, all empty.
- Only the part of a score above the floor reflects work beyond copying the closest example.
- These numbers were computed on the shipped references and block lists, against GEOS
  `498d8e33`, with the authors' audit script (not included).

Per task, full reference:

| split | task | nearest visible example (fixed scorer) | copy-nearest, paper | copy-nearest, fixed | empty, paper | empty, fixed |
|---|---|---|---|---|---|---|
| val | AdvancedExampleCasedContactThermoElasticWellbore | wellbore/CasedElasticWellbore_ImperfectInterfaces_smoke.xml | 0.23 | 0.31 | 0.10 | 0.13 |
| val | AdvancedExampleDeviatedElasticWellbore | wellbore/CasedElasticWellbore_benchmark.xml | 0.28 | 0.38 | 0.06 | 0.09 |
| val | AdvancedExampleDruckerPrager | triaxialDriver/triaxialDriver_ExtendedDruckerPrager_basicExample.xml | 0.83 | 0.83 | 0.20 | 0.20 |
| val | AdvancedExampleExtendedDruckerPrager | src/coreComponents/integrationTests/constitutiveTests/testTriaxial_modifiedCamClay.xml | 0.73 | 0.73 | 0.20 | 0.20 |
| val | AdvancedExampleModifiedCamClay | triaxialDriver/triaxialDriver_ExtendedDruckerPrager_basicExample.xml | 0.78 | 0.78 | 0.20 | 0.20 |
| val | AdvancedExampleViscoDruckerPrager | triaxialDriver/triaxialDriver_ExtendedDruckerPrager_basicExample.xml | 0.83 | 0.83 | 0.20 | 0.20 |
| val | buckleyLeverettProblem | compositionalMultiphaseFlow/dbc/buckleyLeverett_1d/buckleyLeverett_1d.xml | 0.70 | 0.70 | 0.25 | 0.25 |
| val | ExampleDPWellbore | solidMechanics/ExtendedDruckerPragerWellbore_smoke.xml | 0.33 | 0.46 | 0.08 | 0.11 |
| val | ExampleEDPWellbore | solidMechanics/DruckerPragerWellbore_benchmark.xml | 0.81 | 0.81 | 0.22 | 0.22 |
| val | ExampleIsothermalLeakyWell | compositionalMultiphaseFlow/benchmarks/thermalLeakyWell/thermalLeakyWell_benchmark.xml | 0.66 | 0.68 | 0.26 | 0.26 |
| val | ExampleMandel | poromechanics/PoroElastic_Mandel_prism6_smoke.xml | 0.33 | 0.41 | 0.08 | 0.11 |
| val | ExampleThermalLeakyWell | compositionalMultiphaseFlow/benchmarks/isothermalLeakyWell/isothermalLeakyWell_benchmark.xml | 0.65 | 0.67 | 0.26 | 0.26 |
| val | ExampleThermoporoelasticConsolidation | thermoPoromechanics/ThermoPoroDruckerPrager_consolidation_smoke.xml | 0.82 | 0.82 | 0.20 | 0.20 |
| val | kgdExperimentValidation | hydraulicFracturing/kgdToughnessDominated_benchmark.xml | 0.82 | 0.82 | 0.23 | 0.23 |
| val | pknViscosityDominated | hydraulicFracturing/pennyShapedViscosityDominated_benchmark.xml | 0.84 | 0.84 | 0.23 | 0.23 |
| val | TutorialPoroelasticity | poromechanics/PoroElastic_CarmanKozenyPermeability_fim_smoke.xml | 0.41 | 0.61 | 0.11 | 0.17 |
| val | TutorialSneddon | efemFractureMechanics/Sneddon_embeddedFracShapes_smoke.xml | 0.13 | 0.30 | 0.04 | 0.08 |
| held-out | AdvancedExampleCasedThermoElasticWellbore | wellbore/CasedThermoElasticWellbore_ImperfectInterfaces_smoke.xml | 0.29 | 0.40 | 0.09 | 0.12 |
| held-out | AdvancedExamplePureThermalDiffusionWellbore | wellbore/CasedThermoElasticWellbore_smoke.xml | 0.25 | 0.34 | 0.08 | 0.11 |
| held-out | AdvancedExampleThermoPoroElasticWellbore | wellbore/CasedThermoElasticWellbore_smoke.xml | 0.25 | 0.35 | 0.09 | 0.12 |
| held-out | AdvancedExampleViscoExtendedDruckerPrager | triaxialDriver/triaxialDriver_ExtendedDruckerPrager_basicExample.xml | 0.83 | 0.83 | 0.20 | 0.20 |
| held-out | ExampleIsothermalHystInjection | compositionalMultiphaseWell/simpleCo2InjTutorial_smoke.xml | 0.36 | 0.35 | 0.16 | 0.16 |
| held-out | ExampleMCCWellbore | solidMechanics/ExtendedDruckerPragerWellbore_smoke.xml | 0.74 | 0.74 | 0.20 | 0.20 |
| held-out | ExampleProppantTest | proppant/ProppantGelTransport_smoke.xml | 0.77 | 0.77 | 0.24 | 0.24 |
| held-out | ExamplesingleFracCompression | lagrangianContactMechanics/ContactMechanics_Sneddon_smoke.xml | 0.80 | 0.76 | 0.18 | 0.22 |
| held-out | ExampleVerticalPoroElastoPlasticWellbore | poromechanics/PoroDelftEggWellbore_smoke.xml | 0.23 | 0.41 | 0.05 | 0.10 |
| held-out | TutorialHydraulicFractureWithAdvancedXML | hydraulicFracturing/hydrofractureSinglePhase2d.xml | 0.43 | 0.46 | 0.18 | 0.20 |

## Reference decks: things to know

- **Smoke decks are part of the reference.** In 10 tasks the reference includes `*_smoke` decks
  next to the benchmark deck, and the score is against their union. In 7 of them, a correct deck
  without the smoke deck scores about 0.5. Several prompts list the smoke file among the files to
  create, but not all do. `metrics.json` also reports `score_primary_no_smoke`, the score against
  the reference without its smoke decks. It is a diagnostic; `score` keeps the paper's metric.
- **TutorialHydraulicFractureWithAdvancedXML** uses the top-level files of the source example only.
  The paper's reference for this task also held a stray subdirectory of 59 unrelated decks, so this
  task's scores are not comparable with the paper's.
- **ExampleIsothermalHystInjection.** The smoke deck includes a `*_direct_base.xml` that is not part
  of the reference, so the reference is two unconnected base files plus a smoke deck.
- **Close examples stay visible.** Blocking hides each reference deck, its variant siblings and its
  source tutorial. Other decks of the same case stay visible, as in the paper; adapting them is the
  task. Two visible decks reproduced a reference at TreeSim ≥ 0.9 on their own and are blocked as
  well (`extra_blocked.json`); these two blocks did not exist in the paper's runs.
  `PoroElastic_Mandel_prism6_*` (about 0.8 against the Mandel reference) stays visible.

## Known weaknesses (both versions)

- **Wrong values cost little.** One wrong number costs only its share of one element's attributes.
  Six physics values off by 10× cost about 0.13, and a wrong solver type about 0.04. There is no
  partial credit for close values (relative tolerance 1e-6) and no extra weight on physics.
- **Empty sections earn credit.** A matched element with no attributes gets the full 0.3 attribute
  term, which is why an empty deck scores about 0.2.
- **Extra content is cheap.** Adding three unrelated example decks next to a correct deck costs about
  0.05, and duplicating every element about 0.06.
- **Leniency.**
  - String comparison ignores case, although GEOS names are case-sensitive.
  - The root tag is not checked, so a deck under `<Simulation>` with the right content scores 1.0.
  - A default `xmlns="…"` on `<Problem>` scores 0, although GEOS ignores it.
  - Extra attributes that restate GEOS defaults count as mismatches.
  - GEOS `$parameter$` and `` `expr` `` syntax is compared literally.
- A reference leaf matched to a generated element that has children ignores those children.
- `evaluate_geos` has an optional LLM-judge path (`enable_llm_judge=True`). It is off, imports a
  module that is not included, and no score uses it.

## Calling the scorer from Python

```python
import sys; sys.path.insert(0, "src/eval")
from judge_geos import evaluate_directories          # or: from judge_geos_fixed import evaluate_directories
try:
    reward = float(evaluate_directories(ref_dir, gen_dir)["treesim"])   # in [0, 1]
except Exception:   # FileNotFoundError (no *.xml), ValueError / ParseError (nothing parses)
    reward = 0.0
```

`evaluate_directories` reads both directories recursively (`rglob("*.xml")`), so every XML file
under the agent's output dir counts as part of the submission.
