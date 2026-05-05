"""Tests for the simulated GPS clock."""

from __future__ import annotations

import re
import time

from stamping.gps import SimulatedGPS, gps_iso8601


def test_simulated_gps_returns_valid_pair():
    gps = SimulatedGPS()
    epoch_ns, iso = gps.now()
    assert isinstance(epoch_ns, int)
    assert epoch_ns > 1_700_000_000_000_000_000  # post-2023 sanity
    assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$", iso)


def test_simulated_gps_source_name_is_simulated():
    gps = SimulatedGPS()
    assert gps.source_name == "simulated"


def test_simulated_gps_advances_with_time():
    gps = SimulatedGPS()
    a, _ = gps.now()
    time.sleep(0.01)
    b, _ = gps.now()
    assert b > a


def test_iso_formatter_round_trip():
    # Known epoch ns: 2025-04-02 18:26:32.536 UTC = 1743618392536000000
    s = gps_iso8601(1743618392536000000)
    assert s.startswith("2025-04-02T18:26:32.536")
    assert s.endswith("Z")
