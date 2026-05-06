"""Tests for the basic-mode watcher trigger."""

from __future__ import annotations

import threading
import time
from pathlib import Path

from watchdog.events import FileCreatedEvent

from stamping.watcher import _PortMetaHandler


class _FakeStamper:
    def __init__(self) -> None:
        self.calls: list[Path] = []

    def stamp(self, capture_dir: Path) -> object:
        self.calls.append(capture_dir)
        return object()


def test_port_meta_event_waits_for_metadata(tmp_path):
    capture = tmp_path / "board_0_test"
    capture.mkdir()
    port_meta = capture / "port1_meta.json"
    port_meta.write_text("{}", encoding="utf-8")

    stamper = _FakeStamper()
    counters = {"stamped": 0, "skipped": 0, "failed": 0}
    handler = _PortMetaHandler(stamper, counters)

    threading.Timer(
        0.1,
        lambda: (capture / "metadata.json").write_text("{}", encoding="utf-8"),
    ).start()

    handler.on_created(FileCreatedEvent(str(port_meta)))

    deadline = time.monotonic() + 1.0
    while counters["stamped"] == 0 and time.monotonic() < deadline:
        time.sleep(0.02)

    assert counters == {"stamped": 1, "skipped": 0, "failed": 0}
    assert stamper.calls == [capture]
