#!/bin/bash
# Harbor verifier: score /workspace/inputs against the reference deck (TreeSim, failures = 0).
# Scorer: SIGA_SCORER=paper (default; the version behind the SIGA paper's numbers) or
# SIGA_SCORER=fixed (five scorer bugs fixed; see benchmarks/siga-geos/docs/SCORING.md).
mkdir -p /logs/verifier
python3 /tests/score.py --scorer "${SIGA_SCORER:-paper}" \
    --reference /tests/reference --generated /workspace/inputs --out /logs/verifier
exit 0
