"""Octasic capture file parser.

Reads metadata.json (system-side) + port1_meta.json (driver-side) from a capture
directory and returns a populated CaptureInfo. Per TECH_SPEC §4.

Key rules:
- The POC reads ONLY the fields in TECH_SPEC §4. Other fields are ignored.
- format.type must be "cs16" and format.channels must be 1, else ValueError.
- Missing files raise FileNotFoundError.
- The driver-reported `actual_sample_rate_hz` is the truth — never the configured rate.
"""

from __future__ import annotations

import json
from pathlib import Path

from .schemas import CaptureInfo


def parse_capture_dir(path: Path) -> CaptureInfo:
    """Parse an Octasic capture directory into a CaptureInfo.

    Args:
        path: directory containing metadata.json, port1_meta.json, port1.iq

    Returns:
        CaptureInfo populated from the two metadata files.

    Raises:
        FileNotFoundError: if metadata.json or port1_meta.json is missing.
        ValueError: if format.type != "cs16" or format.channels != 1.
        json.JSONDecodeError: if either metadata file is malformed.
    """
    path = Path(path)
    metadata_path = path / "metadata.json"
    port1_meta_path = path / "port1_meta.json"

    if not metadata_path.exists():
        raise FileNotFoundError(f"metadata.json not found in {path}")
    if not port1_meta_path.exists():
        raise FileNotFoundError(f"port1_meta.json not found in {path}")

    with open(metadata_path) as f:
        metadata = json.load(f)
    with open(port1_meta_path) as f:
        port1_meta = json.load(f)

    fmt = port1_meta.get("format", {})
    if fmt.get("type") != "cs16":
        raise ValueError(
            f"Unsupported IQ format in {path}: type={fmt.get('type')!r} (expected 'cs16')"
        )
    if fmt.get("channels") != 1:
        raise ValueError(
            f"Unsupported channel count in {path}: channels={fmt.get('channels')!r} "
            f"(expected 1 in POC v1)"
        )

    capture = port1_meta.get("capture", {})
    statistics = port1_meta.get("statistics", {})

    return CaptureInfo(
        capture_id=metadata["captureId"],
        board_id=int(metadata.get("boardId", 0)),
        capture_time_iso=metadata["captureTime"],
        capture_start_time_ns=int(capture["capture_start_time_ns"]),
        samples_captured=int(statistics["samples_captured"]),
        actual_sample_rate_hz=float(statistics["actual_sample_rate_hz"]),
        duration_sec=float(capture["duration_sec"]),
        center_freq_hz=int(metadata.get("centerFreqHz", 0)),
        band=int(metadata.get("band", 0)),
        iq_path=path / "port1.iq",
    )
