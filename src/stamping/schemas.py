"""Data structures for the stamping POC.

Per TECH_SPEC §8. Two read-only dataclasses:

- CaptureInfo: parsed input from Octasic's metadata files
- StampRecord: output written as stamp.json
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass(frozen=True)
class CaptureInfo:
    """Parsed from metadata.json + port1_meta.json. Read-only."""

    capture_id: str                  # UUID — primary key
    board_id: int                    # which Octasic board
    capture_time_iso: str            # NTP wall-clock from metadata.json
    capture_start_time_ns: int       # monotonic ns counter from port1_meta.json
    samples_captured: int            # actual sample count
    actual_sample_rate_hz: float     # the half-rate truth — NOT the configured rate
    duration_sec: float              # actual measured duration
    center_freq_hz: int              # configured RF center freq
    band: int                        # LTE band
    iq_path: Path                    # path to port1.iq


@dataclass(frozen=True)
class StampRecord:
    """Output of the stamper. Serialized to stamp.json per TECH_SPEC §5."""

    schema_version: str
    capture_id: str
    board_id: int
    gps_epoch_ns: int                # ns since GPS epoch when stamper observed
    gps_iso8601: str                 # human-readable form
    gps_source: str                  # "simulated" | "hardware"
    stamper_observed_at_ns: int      # internal: when stamper noticed the file
    capture_start_time_ns: int       # echoed from port1_meta.json
    samples_captured: int            # echoed
    actual_sample_rate_hz: float     # echoed (the half-rate truth)
    duration_sec: float              # echoed
    end_time_gps_ns: int             # computed: gps_epoch_ns + duration_sec * 1e9
    stamper_version: str

    def to_dict(self) -> dict:
        """Serialize for JSON output."""
        return asdict(self)
