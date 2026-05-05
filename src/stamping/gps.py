"""GPS clock source for the stamping POC.

POC v1: SimulatedGPS uses Python's time.time_ns() as a stand-in for a real
GPS-disciplined clock. This is intentional — the POC validates the stamping
mechanism, not the GPS hardware integration.

In v3, this module gains a HardwareGPS class that reads NMEA from a connected
ZED-F9P (or similar). The Stamper does not need to change.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone


def gps_iso8601(epoch_ns: int) -> str:
    """Format a ns-precision GPS timestamp as ISO-8601 UTC with ms resolution.

    Examples:
        >>> gps_iso8601(1743618392536000000)
        '2026-04-02T18:06:32.536000Z'
    """
    dt = datetime.fromtimestamp(epoch_ns / 1e9, tz=timezone.utc)
    # Trim to microsecond precision for cleaner output
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "000Z"


class SimulatedGPS:
    """A stand-in GPS clock source for POC v1.

    DO NOT ship in production. This uses the laptop's wall-clock time, which is
    NTP-disciplined at best (~ms precision). A real GPS receiver provides
    sub-microsecond precision via the PPS edge + OCXO discipline described in
    Framework_of_the_IQ_Data.md §11.

    To replace in v3: define a class with the same now() / source_name interface
    that reads from real hardware. The Stamper consumes only this interface,
    so nothing else changes.
    """

    source_name: str = "simulated"

    def now(self) -> tuple[int, str]:
        """Return (gps_epoch_ns, iso8601_string) at the moment of call.

        Returns:
            Tuple of:
              - epoch_ns: nanoseconds since Unix epoch (stand-in for GPS epoch)
              - iso8601: human-readable string at ms resolution
        """
        epoch_ns = time.time_ns()
        return epoch_ns, gps_iso8601(epoch_ns)
