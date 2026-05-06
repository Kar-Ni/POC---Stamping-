# ID-IQ Stamping POC v1

Basic-mode stamping engine for Octasic captures. Reads Octasic-format capture
directories, attaches GPS-disciplined timestamps (simulated for v1), emits
`stamp.json` sidecar files alongside each capture.

See `TECH_SPEC.md` for the locked POC v1 design.

## Install

```bash
pip install -e .
```

(For tests: `pip install -e ".[dev]"`)

## Run

Single capture (test mode):

```bash
python -m stamping.main --single-capture samples/board_0_<UUID>/
```

Watch a directory and stamp arrivals (the real POC):

```bash
python -m stamping.main --watch-dir samples/ --process-existing --verbose
```

`--process-existing` first stamps every capture already on disk, then watches
for new arrivals.

## What gets produced

Each capture directory gains a `stamp.json` next to its existing
`metadata.json`, `port1_meta.json`, `port1.iq`. The stamp contains:

- `capture_id` (UUID from Octasic)
- `gps_epoch_ns` + `gps_iso8601` (the timestamp at which the stamper observed the capture)
- `gps_source` (`simulated` in v1)
- `actual_sample_rate_hz` (the half-rate truth from `port1_meta.json`)
- `end_time_gps_ns` (computed from sample count and actual rate)
- See `src/stamping/schemas.py::StampRecord` for the full schema.

## Tests

```bash
pip install -e ".[dev]"
pytest -v
```

## What this POC does NOT do

- ❌ Talk to a real Octasic — file replay only
- ❌ Read a real GPS — `SimulatedGPS` uses laptop clock
- ❌ Catalog captures by UE (no L1 CSV merge) — that's v2
- ❌ Multi-antenna grouping — single channel only

These are deferred to v2 (cataloger) and v3 (live + multi-antenna + real GPS).
See `TECH_SPEC.md`.
