# Third-party material

## GEOS example input decks (LGPL-2.1-only)

| what | where | source | license |
|---|---|---|---|
| 72 GEOS example XML input files, as the reference deck of each task | `benchmarks/siga-geos/tasks/*/tests/reference/*.xml` | [GEOS](https://github.com/GEOS-DEV/GEOS) `inputFiles/`, commit `498d8e33877a1c5539cc3f180c0991dd6189dea1` | LGPL-2.1-only |
| The same 72 files, as the oracle solution | `benchmarks/siga-geos/tasks/*/solution/inputs/*.xml` | same | LGPL-2.1-only |

Every one of these files is byte-identical to a file in GEOS at that commit (checked with git
blob hashes). They are redistributed unmodified under the GNU Lesser General Public License,
version 2.1; the license text is in [`LICENSES/GEOS-LGPL-2.1.txt`](LICENSES/GEOS-LGPL-2.1.txt).
GEOS copyright: Lawrence Livermore National Security LLC (2016-2024), TotalEnergies
(2018-2024), The Board of Trustees of the Leland Stanford Junior University (2018-2024),
Chevron (2023-2024), and the GEOS/GEOSX Contributors (2019-). GEOS's `NOTICE` and `COPYRIGHT` files at
that commit are reproduced verbatim in [`LICENSES/GEOS-NOTICE.txt`](LICENSES/GEOS-NOTICE.txt) and
[`LICENSES/GEOS-COPYRIGHT.txt`](LICENSES/GEOS-COPYRIGHT.txt). See also [`NOTICE`](NOTICE).

## What is not redistributed

- **The GEOS source tree.** `siga-bench` reads a GEOS checkout that you supply
  (`SIGA_GEOS_SRC`) and builds a per-task filtered copy (hardlinks or copies) in your cache
  directory. The Harbor task images clone GEOS from GitHub at build time.
- **The GEOS XML schema.** The S and X validators read `schema.xsd` from your GEOS checkout
  (`/geos_lib/src/coreComponents/schema/schema.xsd` inside the agent environment).
- **The R retrieval database.** The ChromaDB collections are built from GEOS documentation and
  are not shipped.

## Our own files that describe GEOS

The task specifications (`instruction.md`), the primers, the cheatsheets
(`plugin/memory_primer_dsv4_m1u.md`, `plugin_evolving/v3/`) and the prompts were written by the SIGA
authors (in part with language models) to describe GEOS examples and conventions. They name GEOS
elements and file paths and restate parameter values from the GEOS examples (for instance the
loading tables in some task specifications), but do not copy GEOS files, and are licensed under MIT with the
rest of this repository.
