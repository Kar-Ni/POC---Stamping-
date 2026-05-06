# USER MANUAL — ID-IQ Stamping POC v1

Audience: **non-developer**. If you can open a terminal and copy-paste, you can
run this. No coding required.

This manual was verified end-to-end on 2026-05-06: install OK, validation
6/6 PASS, 13/13 unit tests PASS, single-capture run produced a fresh
`stamp.json`.

---

## 1. What this tool is (one paragraph)

It reads Octasic IQ capture folders and writes a `stamp.json` next to each
one. The stamp records *when* the capture was observed (timestamp), the
*real* sample rate from `port1_meta.json` (not the nominal one), and a
computed end-time. v1 uses the laptop clock as a stand-in for GPS. That's
it — that is the whole job of v1.

---

## 2. What you need (one time)

- A Mac, Linux, or Windows machine.
- **Python 3.11 or newer.** Check by opening a terminal and typing:

  ```
  python3 --version
  ```

  If you see `Python 3.11.x` or higher, you're good. If not, install from
  https://www.python.org/downloads/ (tick "Add Python to PATH" on Windows).

- The project folder (this folder, `POC---Stamping-`).

---

## 3. First-time install (~2 minutes)

Open a terminal and go into the project folder:

```
cd /path/to/POC---Stamping-
```

Install the project (this also pulls one helper library, `watchdog`):

```
python3 -m pip install -e .
```

You should see `Successfully installed poc-stamping-1.0.0 watchdog-...`. You
only do this once per machine.

---

## 4. Daily use — three things you can do

### 4.1 Stamp a single capture folder

Use this when you have one capture you want to stamp by hand.

```
python3 -m stamping.main --single-capture samples/board_0_02616ef1-0b2b-4cba-b83d-4a7101b2b50b
```

Replace the path with whichever capture folder you want. You will see a line
like:

```
15:54:50 INFO stamping.stamper :: stamped 02616ef1-... gps=2026-05-06T15:54:50.922000Z rate=1913732.23 Hz
Summary: stamped=1 skipped=0 failed=0
```

A new file `stamp.json` appears inside that folder. Done.

### 4.2 Stamp every capture in a folder, then watch for new ones

This is the real POC use case: point it at a directory that the Octasic
writes captures into, and it will stamp every existing capture **and** stamp
each new capture as it arrives.

```
python3 -m stamping.main --watch-dir samples/ --process-existing --verbose
```

What happens:

1. It scans `samples/` and stamps every capture folder it finds.
2. It then **keeps running** and waits for new capture folders to appear.
3. Press **Ctrl+C** when you want to stop it.

Replace `samples/` with the real folder Octasic writes into when you go
live.

### 4.3 Verify everything is correct (validation)

Run this after stamping if you want a green-light check that all 6 acceptance
criteria from the tech spec pass:

```
python3 validate.py
```

Expected output:

```
[PASS] C1: Coverage — one stamp.json per capture
[PASS] C2: Schema — all required fields present
[PASS] C3: Idempotency — re-run does not duplicate or rewrite
[PASS] C4: FS-write latency visible — stamper_observed_at_ns logged
[PASS] C5: Sample-rate honesty — uses port1_meta actual rate, not configured
[PASS] C6: Sanity — end_time_gps_ns > gps_epoch_ns

OVERALL: PASS
```

If any line says `[FAIL]`, do not ship — open the project and check that
capture folder.

---

## 5. What a capture folder must contain

Each capture folder (e.g. `board_0_<UUID>/`) must have these three files
**before** you stamp it:

| File              | Source                | Purpose                         |
|-------------------|-----------------------|---------------------------------|
| `metadata.json`   | Octasic               | UUID, board, mission, freq, band |
| `port1_meta.json` | Octasic               | Real sample rate, sample count  |
| `port1.iq`        | Octasic               | Raw IQ bytes (cs16, interleaved) |

After stamping, a fourth file appears:

| File              | Source       | Purpose                         |
|-------------------|--------------|---------------------------------|
| `stamp.json`      | This tool    | The timestamp + derived fields  |

If `metadata.json` or `port1_meta.json` is missing, the tool will log an
error for that folder and move on — it will not crash on the others.

---

## 6. What a stamp looks like (and how to read it)

Open any `samples/board_0_*/stamp.json`. Example:

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

Field by field:

- `capture_id` — the UUID from Octasic. Same value as the folder name.
- `board_id` — which Octasic board produced the capture.
- `gps_epoch_ns` / `gps_iso8601` — timestamp the stamper assigned. In v1 this
  is the laptop clock at the moment of stamping. In v3 this becomes a real
  GPS reading.
- `gps_source` — `"simulated"` for now. Will become `"gps"` in v3.
- `stamper_observed_at_ns` — wall-clock time the stamper saw the file. In v1
  it equals `gps_epoch_ns`; later versions can differ.
- `capture_start_time_ns` — the value Octasic itself wrote in
  `port1_meta.json` (this is a *board-relative* clock, not wall-clock; do not
  confuse with `gps_epoch_ns`).
- `samples_captured` — total IQ sample count in `port1.iq`.
- `actual_sample_rate_hz` — **the real rate** from `port1_meta.json`. Note
  this is roughly **half** of the nominal `sampleRateHz` in `metadata.json`
  (e.g. 1.91 MHz vs. 3.84 MHz). This is expected — Octasic reports a
  half-rate truth in `port1_meta`. The stamper trusts that value.
- `duration_sec` — capture duration as Octasic reported it.
- `end_time_gps_ns` — computed: `gps_epoch_ns + samples_captured /
  actual_sample_rate_hz`. Tells you when the capture finished, in GPS time.
- `stamper_version` — version string for the stamper that wrote this file.

---

## 7. Re-running is safe (idempotency)

If you run the stamper twice on the same folder, the second run **will not
overwrite** an existing `stamp.json`. You'll see `skipped=N` in the summary.

If you actually want to re-stamp (e.g. you fixed something), delete the
`stamp.json` first, then re-run.

---

## 8. Troubleshooting

| Symptom                                       | Cause / Fix                                                                              |
|-----------------------------------------------|------------------------------------------------------------------------------------------|
| `python3: command not found`                  | Python not installed or not on PATH. Install Python 3.11+ and reopen the terminal.       |
| `ModuleNotFoundError: No module named 'stamping'` | You skipped step 3. Run `python3 -m pip install -e .` from the project folder.        |
| `ModuleNotFoundError: No module named 'watchdog'` | Same as above — install didn't run cleanly. Re-run `python3 -m pip install -e .`.    |
| `failed=N` in the summary                     | A capture folder was missing `metadata.json` or `port1_meta.json`, or the IQ format wasn't `cs16`/single-channel. The log line above the summary names the folder. |
| `validate.py` shows `[FAIL]`                  | Open the named criterion in `POC_Stamping_TechSpec.md` §10. Most common cause: a `stamp.json` was hand-edited or a capture folder is incomplete. |
| Watcher never picks up new captures           | Make sure you passed `--watch-dir` to the **parent** folder, not the capture folder itself. New captures must arrive as full subfolders containing all 3 files. |
| You want to start from a clean state          | Delete every `samples/board_0_*/stamp.json` and re-run.                                  |

---

## 9. What this v1 does NOT do (and what's next)

Out of scope for v1, by design:

- ❌ Does not talk to a real Octasic — file replay only.
- ❌ Does not read a real GPS — uses laptop clock as a stand-in.
- ❌ Does not group captures by UE (no L1 CSV merge).
- ❌ Does not handle multi-antenna grouping — single channel only.

Roadmap (per `POC_Stamping_TechSpec.md` §12):

- **v2 — Cataloger.** Joins L1 CSVs to stamps to produce per-UE catalogs.
- **v3 — Live + multi-antenna + real GPS.** Replaces the simulated GPS, runs
  on live Octasic output, groups multi-antenna captures.

Both v2 and v3 build **on top of** v1's `stamp.json`. The format you see
today is the foundation.

---

## 10. Files in this project (quick map)

```
POC---Stamping-/
├── README.md                  (developer-oriented overview)
├── RUN_ME_FIRST.md            (quick install + run cheatsheet)
├── USER_MANUAL.md             (this file)
├── pyproject.toml             (project metadata + dependencies)
├── validate.py                (TECH_SPEC §10 validation script)
├── src/stamping/
│   ├── main.py                (the CLI you run)
│   ├── stamper.py             (the core ~70-line stamper logic)
│   ├── octasic.py             (parses Octasic capture folders)
│   ├── gps.py                 (SimulatedGPS — replace in v3)
│   ├── watcher.py             (filesystem watcher for --watch-dir)
│   └── schemas.py             (data shapes: CaptureInfo, StampRecord)
├── tests/                     (13 unit tests — run with `pytest -v`)
└── samples/                   (5 real Octasic captures from VU-30 mission 9 / run 43)
```

---

## 11. The exact commands you will use tomorrow

Copy-paste these in order:

```
cd /path/to/POC---Stamping-
python3 -m pip install -e .
python3 -m stamping.main --watch-dir /path/to/where/octasic/writes --process-existing --verbose
```

When you're done, press **Ctrl+C**. To verify the result:

```
python3 validate.py
```

That's the entire workflow.
