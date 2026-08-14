# pytvtools-core — Agents

This is a standalone package. Edit files directly in this repo.

## Synced content — do not hand-edit

The following directories are **synced from the `pytvtools` repo** via
`python scripts/sync_core.py` (run there, targeting this repo's local clone at
`../pytvtools-core-public`):

- `src/pytvtools_core/` — core package source
- `tests/` — test suite
- `notebooks/` — Databricks notebooks (`cache_refresh`, `absorption_ratio`, ...)
- `jobs/` — job templates
- `demos/` — Pages-hosted HTML products and their generators:
  - `demos/absorption_ratio.html` — **generated artifact** from
    `notebooks/absorption_ratio.py` (Databricks `view` mode → UC `chart_output/` volume →
    downloaded → overwritten in the pytvtools `demos/` dir). Never edit it directly here;
    publish new versions from pytvtools and re-sync.
  - `demos/demo_chart.html` + `demos/demo.py` — AAPL demo (regenerable, no UC).

To publish changes: in `pytvtools`, run `sync_core.py` with a commit message, then push
this repo.
