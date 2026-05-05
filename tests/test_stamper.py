"""Tests for the Stamper."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from stamping.gps import SimulatedGPS
from stamping.schemas import StampRecord
from stamping.stamper import Stamper

FIXTURE = Path(__file__).parent / "fixtures" / "sample_capture"


@pytest.fixture
def fresh_capture(tmp_path):
    """Copy the fixture into a tmp_path so each test starts clean (no stamp.json)."""
    dst = tmp_path / "capture"
    shutil.copytree(FIXTURE, dst)
    return dst


def test_stamp_creates_stamp_json(fresh_capture):
    stamper = Stamper(SimulatedGPS())
    record = stamper.stamp(fresh_capture)

    assert isinstance(record, StampRecord)
    stamp_path = fresh_capture / "stamp.json"
    assert stamp_path.exists()

    payload = json.loads(stamp_path.read_text())

    # Schema fields
    required = {
        "schema_version", "capture_id", "board_id", "gps_epoch_ns",
        "gps_iso8601", "gps_source", "stamper_observed_at_ns",
        "capture_start_time_ns", "samples_captured", "actual_sample_rate_hz",
        "duration_sec", "end_time_gps_ns", "stamper_version",
    }
    assert set(payload.keys()) == required

    # Real-data sanity
    assert payload["capture_id"] == "02616ef1-0b2b-4cba-b83d-4a7101b2b50b"
    assert payload["gps_source"] == "simulated"
    assert abs(payload["actual_sample_rate_hz"] - 1913732.23) < 0.01
    assert payload["end_time_gps_ns"] > payload["gps_epoch_ns"]


def test_stamp_is_idempotent(fresh_capture):
    stamper = Stamper(SimulatedGPS())

    first = stamper.stamp(fresh_capture)
    assert first is not None

    original = (fresh_capture / "stamp.json").read_text()

    second = stamper.stamp(fresh_capture)
    assert second is None  # skip signal

    after = (fresh_capture / "stamp.json").read_text()
    assert original == after  # not rewritten


def test_stamp_rejects_invalid_format(tmp_path):
    bad = tmp_path / "bad"
    bad.mkdir()
    (bad / "metadata.json").write_text(json.dumps({
        "captureId": "x", "boardId": 0, "captureTime": "2026-01-01T00:00:00Z",
        "centerFreqHz": 0, "band": 0,
    }))
    (bad / "port1_meta.json").write_text(json.dumps({
        "capture": {"capture_start_time_ns": 0, "duration_sec": 0.0},
        "format": {"type": "cf32", "channels": 1},
        "statistics": {"samples_captured": 0, "actual_sample_rate_hz": 0.0},
    }))
    with pytest.raises(ValueError):
        Stamper(SimulatedGPS()).stamp(bad)


def test_actual_rate_is_used_not_configured(fresh_capture):
    """Critical: the half-rate truth must propagate to the stamp."""
    stamper = Stamper(SimulatedGPS())
    record = stamper.stamp(fresh_capture)
    assert record is not None

    # Configured rate in metadata.json is 3_840_000.
    # Actual rate (per port1_meta.json) is ~1_913_732. The stamp must carry
    # the actual rate.
    assert record.actual_sample_rate_hz < 2_000_000
    assert record.actual_sample_rate_hz > 1_900_000
