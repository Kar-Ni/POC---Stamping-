"""Validate the POC output against TECH_SPEC §10."""

import json
import sys
from pathlib import Path

REQUIRED_FIELDS = {
    "schema_version", "capture_id", "board_id", "gps_epoch_ns",
    "gps_iso8601", "gps_source", "stamper_observed_at_ns",
    "capture_start_time_ns", "samples_captured", "actual_sample_rate_hz",
    "duration_sec", "end_time_gps_ns", "stamper_version",
}

samples_dir = Path("samples")
captures = sorted(samples_dir.glob("board_*_*"))

print(f"Found {len(captures)} capture directories\n")

results = {1: True, 2: True, 3: True, 4: True, 5: True, 6: True}
issues = []

# Criterion 1: Coverage — exactly one stamp.json per capture
for cap in captures:
    stamp = cap / "stamp.json"
    metadata = cap / "metadata.json"
    port1_meta = cap / "port1_meta.json"
    if metadata.exists() and port1_meta.exists():
        if not stamp.exists():
            results[1] = False
            issues.append(f"  C1: {cap.name} has metadata but no stamp.json")

# Criterion 2: Schema — all required fields present
for cap in captures:
    stamp = cap / "stamp.json"
    if stamp.exists():
        try:
            data = json.loads(stamp.read_text())
        except Exception as e:
            results[2] = False
            issues.append(f"  C2: {cap.name} stamp.json invalid JSON: {e}")
            continue
        missing = REQUIRED_FIELDS - set(data.keys())
        extra = set(data.keys()) - REQUIRED_FIELDS
        if missing:
            results[2] = False
            issues.append(f"  C2: {cap.name} missing fields: {missing}")
        if extra:
            results[2] = False
            issues.append(f"  C2: {cap.name} extra fields: {extra}")

# Criterion 3: Idempotency — running again does not modify or duplicate
import subprocess, os
env = os.environ.copy()
env["PYTHONPATH"] = "src"
checksums_before = {cap.name: (cap / "stamp.json").read_text() for cap in captures if (cap / "stamp.json").exists()}

# Test by re-stamping each capture individually — should all skip
re_skipped = 0
re_stamped = 0
re_failed = 0
for cap in captures:
    result = subprocess.run(
        [sys.executable, "-m", "stamping.main", "--single-capture", str(cap)],
        env=env, capture_output=True, text=True, timeout=10
    )
    # CLI summary is printed to stdout. Keep stderr as fallback for robustness.
    combined = f"{result.stdout}\n{result.stderr}"
    if "skipped=1" in combined:
        re_skipped += 1
    elif "stamped=1" in combined:
        re_stamped += 1
    elif "failed=1" in combined:
        re_failed += 1

if re_stamped > 0:
    results[3] = False
    issues.append(f"  C3: re-run produced {re_stamped} new stamps (should be 0)")
if re_skipped != len(captures):
    results[3] = False
    issues.append(f"  C3: expected {len(captures)} skips, got {re_skipped}")

checksums_after = {cap.name: (cap / "stamp.json").read_text() for cap in captures if (cap / "stamp.json").exists()}
for name in checksums_before:
    if checksums_before[name] != checksums_after[name]:
        results[3] = False
        issues.append(f"  C3: {name} stamp.json was modified by re-run")

# Criterion 4: FS-write latency visible — stamper_observed_at_ns is a real number
for cap in captures:
    stamp = cap / "stamp.json"
    if stamp.exists():
        data = json.loads(stamp.read_text())
        if not isinstance(data.get("stamper_observed_at_ns"), int):
            results[4] = False
            issues.append(f"  C4: {cap.name} stamper_observed_at_ns missing or not int")

# Criterion 5: Sample-rate honesty — uses actual not configured
for cap in captures:
    stamp = cap / "stamp.json"
    port1 = cap / "port1_meta.json"
    if stamp.exists() and port1.exists():
        s = json.loads(stamp.read_text())
        p = json.loads(port1.read_text())
        actual_in_port = p["statistics"]["actual_sample_rate_hz"]
        actual_in_stamp = s["actual_sample_rate_hz"]
        if abs(actual_in_port - actual_in_stamp) > 0.01:
            results[5] = False
            issues.append(f"  C5: {cap.name} stamp rate {actual_in_stamp} != port1_meta rate {actual_in_port}")
        # And it must NOT be the configured rate (3,840,000)
        if abs(actual_in_stamp - 3_840_000) < 1000:
            results[5] = False
            issues.append(f"  C5: {cap.name} stamp rate looks like configured 3.84 MHz, not actual half-rate")

# Criterion 6: Sanity — end > start
for cap in captures:
    stamp = cap / "stamp.json"
    if stamp.exists():
        data = json.loads(stamp.read_text())
        if data["end_time_gps_ns"] <= data["gps_epoch_ns"]:
            results[6] = False
            issues.append(f"  C6: {cap.name} end_time_gps_ns <= gps_epoch_ns")

# Print report
labels = {
    1: "Coverage — one stamp.json per capture",
    2: "Schema — all required fields present",
    3: "Idempotency — re-run does not duplicate or rewrite",
    4: "FS-write latency visible — stamper_observed_at_ns logged",
    5: "Sample-rate honesty — uses port1_meta actual rate, not configured",
    6: "Sanity — end_time_gps_ns > gps_epoch_ns",
}

print("=== Validation against TECH_SPEC §10 ===\n")
all_pass = True
for n in [1, 2, 3, 4, 5, 6]:
    status = "PASS" if results[n] else "FAIL"
    if not results[n]:
        all_pass = False
    print(f"  [{status}] C{n}: {labels[n]}")

if issues:
    print("\nIssues:")
    for i in issues:
        print(i)

print()
print("=" * 60)
print("OVERALL:", "PASS" if all_pass else "FAIL")
print("=" * 60)

sys.exit(0 if all_pass else 1)
