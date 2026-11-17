# feast-venv

Answer sheet of the case `feast-venv`, written from odctl 1.9.0's sources before any run. The reviewer reads it beside the run; the agent never sees it, because it is not in the case folder that `make_suite.py` copies into the skill. Paths are in odctl at tag `v1.9.0`; a path that starts with `planning/` is in the owner's planning repository.

Kinds: A11 (host environment assumed), A8 (image content assumed).

## Records

- planning `odctl/release/1.8.0/audit.md:13`: `uv venv` without `--python` took Python 3.15, and Feast crashed.
- planning `odctl/release/1.7.0/audit.md:9`: the commands need uv and the page did not say so.

## Right answer

- `uv venv --python 3.12 .venv` (Feast 0.68.0 needs Python 3.11 or newer: `docs/guides/feast-iceberg.md:9`; PyPI `requires_python >=3.11.0`).
- `VIRTUAL_ENV=.venv uv pip install "feast[duckdb,iceberg,redis,postgres]==0.68.0" pyarrow` (`smoke.sh:1783-1786`).
- 0.68.0 is the version of the server image `quay.io/feastdev/feature-server:0.68.0` (`compose-mlops.yml:208`); the client matches it.
- The server image has `feast[minimal]`, with no Iceberg or DuckDB, so the offline client runs on the host (`smoke.sh:1781-1782`).
- The script names uv as a tool the host needs.

## Wrong answers seen or expected

- `uv venv` or `python -m venv` with no Python version.
- An unpinned Feast, or a version other than the server's.
- Missing extras for the Iceberg offline store or the Redis online store.
