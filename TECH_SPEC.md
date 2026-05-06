# ID-IQ Stamping POC v1 Technical Specification

## 1. Purpose

The stamping machine POC v1 proves the basic-mode stamping loop for Octasic IQ
captures. It watches or processes capture directories, reads the Octasic sidecar
metadata, observes the current GPS-disciplined clock value, and emits a
`stamp.json` sidecar for each capture.

POC v1 is intentionally narrow. It does not build the full F12 Engine and does
not perform IMSI extraction, localisation, cataloging, real GPS integration,
live Octasic integration, multi-antenna grouping, UE filtering, or later v2/v3
features.

## 2. Runtime Modes

The CLI supports:

- `--single-capture PATH`: process one capture directory and exit.
- `--watch-dir PATH`: watch a directory tree for arriving captures.
- `--process-existing`: with `--watch-dir`, process existing captures before
  watching for new arrivals.
- `--verbose`: enable debug logging.
- `--version`: print the installed stamper version and exit.

Every run prints a summary containing `stamped`, `skipped`, and `failed` counts.

## 3. Capture Directory Contract

A v1 capture directory is complete when it contains:

- `metadata.json`
- `port1_meta.json`
- `port1.iq`

`stamp.json` is produced by the stamper. If `stamp.json` already exists, the
capture is skipped and the existing stamp is not rewritten.

The watcher trigger is `port1_meta.json`. A watcher event for `port1_meta.json`
must stamp the capture once `metadata.json` is also present.

## 4. Input Metadata

The stamper parses both metadata sidecars:

- `metadata.json` supplies capture-level identifiers and configured RF context,
  including `captureId`, `boardId`, `captureTime`, `centerFreqHz`, and `band`.
- `port1_meta.json` supplies driver-side capture truth, including
  `capture.capture_start_time_ns`, `statistics.samples_captured`, and
  `statistics.actual_sample_rate_hz`.

The v1 format validation rules are locked:

- `port1_meta.json format.type` must be `cs16`.
- `port1_meta.json format.channels` must be `1`.
- Any other IQ format or channel count is rejected.

`statistics.actual_sample_rate_hz` from `port1_meta.json` is the sample-rate
truth for stamping math. `metadata.json sampleRateHz` is configuration context
only and must not be used for duration or end-time stamping math.

## 5. Stamp Output

The stamper writes `stamp.json` beside the input sidecars. The v1 schema is:

- `schema_version`
- `capture_id`
- `board_id`
- `gps_epoch_ns`
- `gps_iso8601`
- `gps_source`
- `stamper_observed_at_ns`
- `capture_start_time_ns`
- `samples_captured`
- `actual_sample_rate_hz`
- `duration_sec`
- `end_time_gps_ns`
- `stamper_version`

For POC v1, `gps_source` is `simulated`.

`stamp.json` must be written atomically by writing a temporary file, flushing and
fsyncing it, and then renaming it into place. Existing `stamp.json` files are
never modified by a normal run.

## 6. Stamping Algorithm

For each capture directory:

1. If `stamp.json` already exists, skip.
2. Read the simulated GPS clock.
3. Parse `metadata.json` and `port1_meta.json`.
4. Validate `format.type == "cs16"`.
5. Validate `format.channels == 1`.
6. Build the stamp record from parsed metadata and the observed GPS time.
7. Set `actual_sample_rate_hz` from
   `port1_meta.json statistics.actual_sample_rate_hz`.
8. Compute `duration_sec` as `samples_captured / actual_sample_rate_hz`.
9. Compute `end_time_gps_ns` from the observed GPS time and computed duration.
10. Atomically write `stamp.json`.

The stamper is deliberately dumb in v1: one capture directory in, one
`stamp.json` out.

## 7. GPS Policy

POC v1 uses simulated GPS only. The clock source may use the host clock as a
stand-in for a GPS-disciplined timestamp, but the output must identify this with
`gps_source: "simulated"`.

Real GPS hardware integration is out of scope for v1.

## 8. Internal Data Structures

The implementation may use simple immutable structures to carry parsed capture
metadata and output stamp data. These structures must not introduce v2/v3
concepts such as UE identity, antenna grouping, localisation state, or catalog
records.

## 9. Error Handling

Malformed or incomplete captures fail that capture without stopping unrelated
captures in watcher or process-existing mode. Single-capture mode exits
non-zero if the requested capture fails.

## 10. Validation Criteria

The POC is considered aligned when:

- Coverage: every complete capture under `samples/` has exactly one
  `stamp.json`.
- Schema: every `stamp.json` contains exactly the v1 fields in section 5.
- Idempotency: rerunning the stamper skips existing stamps and does not rewrite
  them.
- FS visibility: `stamper_observed_at_ns` is present and numeric.
- Sample-rate honesty: `actual_sample_rate_hz` matches
  `port1_meta.json statistics.actual_sample_rate_hz`, not configured
  `metadata.json sampleRateHz`.
- Sanity: `end_time_gps_ns` is greater than `gps_epoch_ns`.
