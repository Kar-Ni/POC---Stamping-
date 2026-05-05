# RUN ME FIRST — ID-IQ Stamping POC v1

**This is a complete, working Python project.** No Cursor, no AI development needed.
You unzip it, install one dependency, and run it. The code is already written
and validated against real Octasic mission data.

## What you have

- ✅ Working Python code (`src/stamping/`)
- ✅ 5 real Octasic captures from VU-30 mission 9 / run 43 (`samples/`)
- ✅ Tests (`tests/`) using one of the captures as a fixture
- ✅ Validation script (`validate.py`) checking all 6 TECH_SPEC §10 criteria
- ✅ Already proven: all 6 criteria PASS on this dataset

## Setup (one time, ~2 minutes)

You need Python 3.11+. Verify:

```
python3 --version
```

If not installed: get it from https://www.python.org/downloads/

Open Terminal (Mac) or Command Prompt / PowerShell (Windows). Navigate into
this folder:

```
cd /path/to/poc_stamping
```

Install the project (pulls one dependency: `watchdog`):

```
python3 -m pip install -e .
```

That's it. The project is now installed.

## Run it

### Option A — Stamp one capture

```
python3 -m stamping.main --single-capture samples/board_0_02616ef1-0b2b-4cba-b83d-4a7101b2b50b
```

You should see output like:

```
2026-05-05 19:48:09 INFO stamping.stamper :: stamped 02616ef1-... gps=2026-05-05T19:48:09.295000Z rate=1913732.23 Hz
Summary: stamped=1 skipped=0 failed=0
```

A new file `stamp.json` appears in that directory.

### Option B — Stamp all 5 captures at once

```
python3 -m stamping.main --watch-dir samples/ --process-existing --verbose
```

(Press `Ctrl+C` after a couple of seconds — it stamps all existing captures
and then waits for new ones.)

You should see 5 lines like `INFO ... stamped ...`, then:

```
Summary: stamped=5 skipped=0 failed=0
```

Now every capture directory has a `stamp.json`.

### Option C — Run the validation

```
python3 validate.py
```

Checks all 6 TECH_SPEC §10 criteria. Should print:

```
=== Validation against TECH_SPEC §10 ===

  [PASS] C1: Coverage — one stamp.json per capture
  [PASS] C2: Schema — all required fields present
  [PASS] C3: Idempotency — re-run does not duplicate or rewrite
  [PASS] C4: FS-write latency visible — stamper_observed_at_ns logged
  [PASS] C5: Sample-rate honesty — uses port1_meta actual rate, not configured
  [PASS] C6: Sanity — end_time_gps_ns > gps_epoch_ns

============================================================
OVERALL: PASS
============================================================
```

### Option D — Run unit tests (optional)

```
python3 -m pip install pytest
python3 -m pytest -v
```

12 tests should pass.

## What the output looks like

After running, look at any `samples/board_0_*/stamp.json`. Example:

```json
{
  "schema_version": "1.0",
  "capture_id": "02616ef1-0b2b-4cba-b83d-4a7101b2b50b",
  "board_id": 0,
  "gps_epoch_ns": 1778010489295641360,
  "gps_iso8601": "2026-05-05T19:48:09.295000Z",
  "gps_source": "simulated",
  "stamper_observed_at_ns": 1778010489295641360,
  "capture_start_time_ns": 1116077620134,
  "samples_captured": 766400,
  "actual_sample_rate_hz": 1913732.23,
  "duration_sec": 0.400474,
  "end_time_gps_ns": 1778010489696115360,
  "stamper_version": "poc-v1.0.0"
}
```

This is the stamping engine's output — the foundation that v2 (cataloger) and
v3 (multi-antenna + live + real GPS) build on.

## What this code does NOT do

- ❌ Talk to a real Octasic — file replay only
- ❌ Read a real GPS — `SimulatedGPS` uses laptop clock as a stand-in
- ❌ Catalog captures by UE (no L1 CSV merge) — that's v2
- ❌ Multi-antenna grouping — single channel only

These are deferred to v2/v3 per `POC_Stamping_TechSpec.md` §12.

## Files in this project

- `src/stamping/main.py` — CLI entrypoint
- `src/stamping/stamper.py` — the dumb stamper (the heart of the POC)
- `src/stamping/octasic.py` — Octasic file parser
- `src/stamping/gps.py` — `SimulatedGPS` (replaceable in v3 by real hardware)
- `src/stamping/watcher.py` — file system watcher
- `src/stamping/schemas.py` — `CaptureInfo` + `StampRecord` dataclasses
- `tests/` — unit tests covering parser, GPS, stamper, idempotency, half-rate
- `samples/` — 5 real Octasic captures for testing
- `validate.py` — full TECH_SPEC §10 validation
- `pyproject.toml` — project metadata + dependencies
- `README.md` — short reference

## What to show Guillaume / Christian

1. **`samples/board_0_*/stamp.json`** — the actual output of the stamper running on real data
2. **`src/stamping/stamper.py`** — the stamper logic, ~70 lines including comments
3. **`POC_Stamping_TechSpec.md`** — the design that produced this code
4. **`validate.py` output** — 6/6 PASS

The conversation becomes: *"We have a working Tier 1 stamper. v2 adds the
cataloger (L1 CSV merge → per-UE grouping). v3 adds multi-antenna and real
GPS. Should we go to v2 next, or refine v1 first based on what we learn?"*

---

*If anything is broken, check `python3 --version` (must be 3.11+) and
that `python3 -m pip install -e .` ran without errors. If you see "Module not found",
you skipped that step.*
