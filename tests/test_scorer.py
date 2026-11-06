"""TreeSim scorer battery, run against both shipped scorers.

  src/eval/judge_geos.py        the paper scorer (every number in the SIGA paper)
  src/eval/judge_geos_fixed.py  the fixed scorer (benchmarks/siga-geos/docs/SCORING.md, "What the fixed version changes")

Every check must pass for the fixed scorer. For the paper scorer, the checks that
exercise the five fixed bugs are expected failures (strict xfail), which documents
exactly where the two versions differ. All synthetic; no data needed.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "eval"))
import judge_geos as paper  # noqa: E402
import judge_geos_fixed as fixed  # noqa: E402

SCORERS = {"paper": paper, "fixed": fixed}
#: Battery checks the paper scorer fails (pytest node names), with the SCORING.md
#: bug each one exercises. These are strict xfails: if one starts passing, the list is stale.
B4 = "bug 4: GEOS arrays compared as whitespace-sensitive strings"
B5 = "bug 5: '.5' not recognised as a number"
PAPER_KNOWN_DIFFERENCES = {
    "test_equivalent_formats[paper-.5-0.5]": B5,
    "test_equivalent_formats[paper--.25--0.25]": B5,
    "test_equivalent_formats[paper-{ shale }-{shale}]": B4,
    "test_equivalent_formats[paper-{ oil, water }-{oil,water}]": B4,
    "test_equivalent_formats[paper-{ { 0, 1 } }-{{0,1}}]": B4,
    "test_equivalent_formats[paper-{ {1, 2}, {3, 4} }-{ { 1.0, 2.0 }, { 3, 4 } }]": B4,
    "test_equivalent_formats[paper-{}-{ }]": B4,
    "test_repeated_sections_merge_like_geos[paper]": "bug 3: repeated top-level sections not merged as GEOS does",
    "test_two_entry_decks_do_not_double_count_includes[paper]": "bug 1: included files counted again as decks",
    "test_sibling_order_with_unnamed_repeated_blocks[paper]": "bug 2: matching depends on element order",
}


@pytest.fixture(params=sorted(SCORERS))
def jg(request):
    why = PAPER_KNOWN_DIFFERENCES.get(request.node.name)
    if why:
        request.applymarker(pytest.mark.xfail(strict=True, reason=f"paper scorer, {why}"))
    return SCORERS[request.param]


def write(d: Path, files: dict[str, str]) -> Path:
    d.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        (d / name).write_text(text)
    return d


def ts(jg, tmp_path: Path, gt: dict[str, str], gen: dict[str, str]) -> float:
    return jg.evaluate_directories(write(tmp_path / "gt", gt), write(tmp_path / "gen", gen))["treesim"]


BASE = """<Problem>
  <Solvers><SinglePhaseFVM name="flow" discretization="tpfa" targetRegions="{ Domain }"/></Solvers>
  <Constitutive>
    <CompressibleSinglePhaseFluid name="water" defaultDensity="1000" defaultViscosity="0.001"
        compressibility="4.4e-10" referencePressure="0.0"/>
    <ConstantPermeability name="rockPerm" permeabilityComponents="{ 1.0e-12, 1.0e-12, 1.0e-12 }"/>
  </Constitutive>
  <FieldSpecifications>
    <FieldSpecification name="initialPressure" fieldName="pressure" scale="1e6" setNames="{ all }"/>
  </FieldSpecifications>
</Problem>"""
BENCH = """<Problem>
  <Included><File name="./base.xml"/></Included>
  <Mesh><InternalMesh name="mesh" xCoords="{ 0, 1 }" nx="{ 10 }" cellBlockNames="{ cb1 }"/></Mesh>
  <Events maxTime="100"><PeriodicEvent name="solverApplications" forceDt="1" target="/Solvers/flow"/></Events>
</Problem>"""
DECK = {"base.xml": BASE, "bench.xml": BENCH}


# ---------------------------------------------------------------- value formats

@pytest.mark.parametrize("a,b", [
    ("1e6", "1000000"), ("1.0e+06", "1000000"), ("1E6", "1e6"), ("1.0", "1"), ("5.", "5"),
    (".5", "0.5"), ("-.25", "-0.25"),
    ("{ 1, 2 }", "{1,2}"), ("{ 1.0e-12, 1e-12 }", "{1e-12,1.0e-12}"),
    ("{ shale }", "{shale}"), ("{ oil, water }", "{oil,water}"),
    ("{ { 0, 1 } }", "{{0,1}}"), ("{ {1, 2}, {3, 4} }", "{ { 1.0, 2.0 }, { 3, 4 } }"),
    ("{}", "{ }"), ("x ", "x"), ("  1e6 ", "1000000"),
])
def test_equivalent_formats(jg, a, b):
    assert jg.values_equivalent(a, b)
    assert jg.values_equivalent(b, a)


@pytest.mark.parametrize("a,b", [
    ("1e6", "1e7"), ("{ 1, 2 }", "{ 1, 2, 3 }"), ("{ oil, water }", "{ water, oil }"),
    ("{ {1, 2}, {3, 4} }", "{ {1, 2, 3, 4} }"), ("{ shale }", "{ sand }"), (".5", "5"),
])
def test_different_values(jg, a, b):
    assert not jg.values_equivalent(a, b)


# ---------------------------------------------------------------- degenerate submissions

def test_failures_map_to_zero(jg, tmp_path):
    gt = write(tmp_path / "gt", DECK)
    cases = {
        "empty_dir": {},
        "empty_file": {"a.xml": ""},
        "invalid": {"a.xml": "<Problem><Solvers></Problem>"},
        "wrong_root_empty": {"a.xml": "<Foo/>"},
    }
    for name, files in cases.items():
        gen = write(tmp_path / name, files)
        out = jg.evaluate_geos({"generated_dir": str(gen)}, {"ground_truth_dir": str(gt)})
        assert out["score"] == 0.0, name
    with pytest.raises(FileNotFoundError):
        jg.evaluate_directories(gt, tmp_path / "empty_dir")
    with pytest.raises(ValueError):
        jg.evaluate_directories(gt, tmp_path / "invalid")


def test_evaluate_geos_reward_is_treesim(jg, tmp_path):
    gt = write(tmp_path / "gt", DECK)
    out = jg.evaluate_geos({"generated_dir": str(gt)}, {"ground_truth_dir": str(gt)})
    assert out["score"] == 1.0 and out["metrics"]["treesim"] == 1.0


# ---------------------------------------------------------------- invariances

def test_oracle_is_one(jg, tmp_path):
    assert ts(jg, tmp_path, DECK, DECK) == 1.0


def test_attribute_order_comments_whitespace(jg, tmp_path):
    gen = {
        "base.xml": BASE.replace('name="water" defaultDensity="1000"', 'defaultDensity="1000" name="water"')
                        .replace("<Solvers>", "<Solvers>\n\n   <!-- a comment -->\n"),
        "bench.xml": '<?xml version="1.0" encoding="UTF-8"?>\n' + BENCH.replace("  ", "\t"),
    }
    assert ts(jg, tmp_path, DECK, gen) == 1.0


def test_split_vs_flattened(jg, tmp_path):
    flat = BENCH.replace('<Included><File name="./base.xml"/></Included>',
                         BASE.replace("<Problem>", "").replace("</Problem>", ""))
    assert ts(jg, tmp_path / "a", DECK, {"deck.xml": flat}) == 1.0
    assert ts(jg, tmp_path / "b", {"deck.xml": flat}, DECK) == 1.0


def test_repeated_sections_merge_like_geos(jg, tmp_path):
    # Same content, FieldSpecifications split over two files vs one block.
    extra = '<FieldSpecification name="bc" fieldName="pressure" scale="2e6" setNames="{ xneg }"/>'
    one = {"base.xml": BASE.replace("</FieldSpecifications>", extra + "</FieldSpecifications>"),
           "bench.xml": BENCH}
    two = {"base.xml": BASE,
           "bench.xml": BENCH.replace("</Mesh>", "</Mesh><FieldSpecifications>" + extra
                                      + "</FieldSpecifications>")}
    assert ts(jg, tmp_path / "a", one, two) == 1.0
    assert ts(jg, tmp_path / "b", two, one) == 1.0


def test_two_entry_decks_do_not_double_count_includes(jg, tmp_path):
    smoke = BENCH.replace('maxTime="100"', 'maxTime="1"')
    d = write(tmp_path / "d", {**DECK, "smoke.xml": smoke})
    root = jg.load_and_resolve_dir(d)
    # base sections once per entry deck (2), not 3 (it used to be re-added as its own deck)
    assert [c.tag for c in root].count("Solvers") == 2


def test_sibling_order_with_unnamed_repeated_blocks(jg, tmp_path):
    smoke = BENCH.replace('maxTime="100"', 'maxTime="1"').replace('nx="{ 10 }"', 'nx="{ 2 }"')
    gt = {**DECK, "smoke.xml": smoke}
    # same decks, entry order swapped by file name
    gen = {"base.xml": BASE, "a_smoke.xml": smoke, "b_bench.xml": BENCH}
    assert ts(jg, tmp_path, gt, gen) == 1.0


def test_include_cycle_and_missing_include(jg, tmp_path):
    cyc = {"a.xml": '<Problem><Included><File name="b.xml"/></Included><Mesh/></Problem>',
           "b.xml": '<Problem><Included><File name="a.xml"/></Included><Events/></Problem>'}
    assert 0.0 < ts(jg, tmp_path / "c", cyc, cyc) <= 1.0
    missing = ts(jg, tmp_path / "m", DECK, {"bench.xml": BENCH})
    assert 0.0 < missing < 0.6


# ---------------------------------------------------------------- sensitivity

def test_wrong_physics_lowers_score(jg, tmp_path):
    wrong = {"base.xml": BASE.replace('defaultViscosity="0.001"', 'defaultViscosity="0.01"')
                             .replace("{ 1.0e-12, 1.0e-12, 1.0e-12 }", "{ 1.0e-11, 1.0e-11, 1.0e-11 }"),
             "bench.xml": BENCH.replace('forceDt="1"', 'forceDt="10"')}
    s = ts(jg, tmp_path / "w", DECK, wrong)
    assert 0.5 < s < 1.0
    swapped = {"base.xml": BASE.replace("SinglePhaseFVM", "SinglePhaseHybridFVM"), "bench.xml": BENCH}
    assert ts(jg, tmp_path / "s", DECK, swapped) < 1.0


def test_extra_elements_penalized_mildly(jg, tmp_path):
    extra = {"base.xml": BASE.replace("</Constitutive>",
                                      '<NullModel name="extra"/></Constitutive>'), "bench.xml": BENCH}
    s = ts(jg, tmp_path, DECK, extra)
    assert 0.9 < s < 1.0
