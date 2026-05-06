"""The dumb stamper.

Per TECH_SPEC §5 (output) + §6 (algorithm) + Framework §14 (basic-mode workflow):

- Receives a capture directory.
- Reads the GPS clock NOW.
- Composes a StampRecord.
- Writes stamp.json atomically alongside the existing metadata.
- Idempotent: skips if stamp.json already exists.
- Knows nothing about UEs, antennas, or selection rules.

The stamper is the trade-secret heart of Layer B / Cycle Processor (L2). The
mechanism is what counts; everything else is wiring.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict
from pathlib import Path

from .gps import SimulatedGPS
from .octasic import parse_capture_dir
from .schemas import StampRecord

logger = logging.getLogger(__name__)

SCHEMA_VERSION = "1.0"


class Stamper:
    """Dumb per-capture stamper.

    Args:
        gps: a clock source exposing now() -> (epoch_ns, iso8601) and source_name.
        stamper_version: version string written into each stamp.
    """

    def __init__(
        self,
        gps: SimulatedGPS,
        stamper_version: str = "poc-v1.0.0",
    ) -> None:
        self._gps = gps
        self._stamper_version = stamper_version

    def stamp(self, capture_dir: Path) -> StampRecord | None:
        """Stamp a single capture directory.

        Returns:
            The StampRecord on success, or None if stamp.json already existed
            (idempotent skip).

        Raises:
            FileNotFoundError, ValueError, json.JSONDecodeError as appropriate
            when input is malformed.
        """
        capture_dir = Path(capture_dir)
        stamp_path = capture_dir / "stamp.json"

        if stamp_path.exists():
            logger.info("skip %s: stamp.json already exists", capture_dir.name)
            return None

        # Read GPS NOW — this is the moment we're bonding to the capture.
        gps_epoch_ns, gps_iso = self._gps.now()

        info = parse_capture_dir(capture_dir)
        if info.actual_sample_rate_hz <= 0:
            raise ValueError(
                f"Invalid actual_sample_rate_hz in {capture_dir}: "
                f"{info.actual_sample_rate_hz!r}"
            )
        duration_sec = info.samples_captured / info.actual_sample_rate_hz

        record = StampRecord(
            schema_version=SCHEMA_VERSION,
            capture_id=info.capture_id,
            board_id=info.board_id,
            gps_epoch_ns=gps_epoch_ns,
            gps_iso8601=gps_iso,
            gps_source=self._gps.source_name,
            stamper_observed_at_ns=gps_epoch_ns,
            capture_start_time_ns=info.capture_start_time_ns,
            samples_captured=info.samples_captured,
            actual_sample_rate_hz=info.actual_sample_rate_hz,
            duration_sec=duration_sec,
            end_time_gps_ns=gps_epoch_ns + int(duration_sec * 1e9),
            stamper_version=self._stamper_version,
        )

        self._write_atomic(stamp_path, asdict(record))
        logger.info(
            "stamped %s gps=%s rate=%.2f Hz",
            info.capture_id,
            gps_iso,
            info.actual_sample_rate_hz,
        )
        return record

    @staticmethod
    def _write_atomic(target: Path, payload: dict) -> None:
        """Write JSON atomically: write to .tmp, fsync, rename."""
        tmp = target.with_suffix(target.suffix + ".tmp")
        data = json.dumps(payload, indent=2, ensure_ascii=False)
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, target)
        dir_fd = os.open(target.parent, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
