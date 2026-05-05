"""Tests for the Octasic file parser."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from stamping.octasic import parse_capture_dir
from stamping.schemas import CaptureInfo

FIXTURE = Path(__file__).parent / "fixtures" / "sample_capture"


def test_parse_real_capture_returns_populated_info():
    info = parse_capture_dir(FIXTURE)
    assert isinstance(info, CaptureInfo)
    assert info.capture_id == "02616ef1-0b2b-4cba-b83d-4a7101b2b50b"
    assert info.board_id == 0
    assert info.samples_captured == 766400
    # Half-rate truth — must be the actual rate, not the configured 3,840,000
    assert abs(info.actual_sample_rate_hz - 1913732.23) < 0.01
    assert abs(info.duration_sec - 0.400474) < 1e-6
    assert info.center_freq_hz == 1871200000
    assert info.band == 2
    assert info.capture_time_iso.startswith("2026-04-02T18:06:32")
    assert info.capture_start_time_ns == 1116077620134


def test_missing_metadata_raises(tmp_path):
    # Empty dir
    with pytest.raises(FileNotFoundError, match="metadata.json"):
        parse_capture_dir(tmp_path)


def test_missing_port1_meta_raises(tmp_path):
    (tmp_path / "metadata.json").write_text("{}")
    with pytest.raises(FileNotFoundError, match="port1_meta.json"):
        parse_capture_dir(tmp_path)


def test_rejects_non_cs16_format(tmp_path):
    (tmp_path / "metadata.json").write_text(json.dumps({
        "captureId": "test", "boardId": 0, "captureTime": "2026-01-01T00:00:00Z",
        "centerFreqHz": 0, "band": 0,
    }))
    (tmp_path / "port1_meta.json").write_text(json.dumps({
        "capture": {"capture_start_time_ns": 0, "duration_sec": 0.0},
        "format": {"type": "cf32", "channels": 1},
        "statistics": {"samples_captured": 0, "actual_sample_rate_hz": 0.0},
    }))
    with pytest.raises(ValueError, match="Unsupported IQ format"):
        parse_capture_dir(tmp_path)


def test_rejects_multi_channel(tmp_path):
    (tmp_path / "metadata.json").write_text(json.dumps({
        "captureId": "test", "boardId": 0, "captureTime": "2026-01-01T00:00:00Z",
        "centerFreqHz": 0, "band": 0,
    }))
    (tmp_path / "port1_meta.json").write_text(json.dumps({
        "capture": {"capture_start_time_ns": 0, "duration_sec": 0.0},
        "format": {"type": "cs16", "channels": 4},
        "statistics": {"samples_captured": 0, "actual_sample_rate_hz": 0.0},
    }))
    with pytest.raises(ValueError, match="Unsupported channel count"):
        parse_capture_dir(tmp_path)
