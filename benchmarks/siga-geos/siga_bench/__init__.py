"""siga-bench: the SIGA GEOS input-deck task as a standalone benchmark.

Tasks live in Harbor layout under ``benchmarks/siga-geos/tasks/<task-id>/``;
this package runs agents on them in a bwrap sandbox, verifies
the output and writes a common ``metrics.json``. See ../README.md.
"""
__version__ = "0.1.0"
