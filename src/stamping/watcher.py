"""Directory watcher.

Uses the `watchdog` library to detect new port1_meta.json files appearing in a
target directory. When a new file is detected:

1. Wait 200 ms for the directory to stabilize (full write).
2. Verify metadata.json also exists alongside.
3. Hand the directory to the Stamper.

This is the basic-mode trigger per Framework §14: "a new port1_meta.json is written".
"""

from __future__ import annotations

import logging
import threading
import time
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from .stamper import Stamper

logger = logging.getLogger(__name__)

DEBOUNCE_SEC = 0.2


class _PortMetaHandler(FileSystemEventHandler):
    """Triggers stamping when port1_meta.json appears, after a debounce."""

    def __init__(
        self,
        stamper: Stamper,
        counters: dict,
    ) -> None:
        self._stamper = stamper
        self._counters = counters
        self._pending: dict[Path, threading.Timer] = {}
        self._lock = threading.Lock()

    def on_created(self, event: FileSystemEvent) -> None:
        self._maybe_schedule(event)

    def on_modified(self, event: FileSystemEvent) -> None:
        self._maybe_schedule(event)

    def _maybe_schedule(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.name != "port1_meta.json":
            return

        capture_dir = path.parent
        with self._lock:
            existing = self._pending.pop(capture_dir, None)
            if existing is not None:
                existing.cancel()

            timer = threading.Timer(
                DEBOUNCE_SEC,
                self._fire,
                args=[capture_dir],
            )
            self._pending[capture_dir] = timer
            timer.start()

    def _fire(self, capture_dir: Path) -> None:
        with self._lock:
            self._pending.pop(capture_dir, None)
        try:
            metadata = capture_dir / "metadata.json"
            if not metadata.exists():
                logger.warning(
                    "%s has port1_meta.json but no metadata.json — skipping",
                    capture_dir.name,
                )
                self._counters["failed"] += 1
                return

            result = self._stamper.stamp(capture_dir)
            if result is None:
                self._counters["skipped"] += 1
            else:
                self._counters["stamped"] += 1
        except Exception as exc:  # noqa: BLE001
            logger.error("failed to stamp %s: %s", capture_dir.name, exc)
            self._counters["failed"] += 1


def watch(watch_dir: Path, stamper: Stamper, counters: dict) -> Observer:
    """Start a watchdog observer on watch_dir. Returns the observer for shutdown.

    Args:
        watch_dir: directory to monitor (recursively).
        stamper: Stamper instance to invoke on each new capture.
        counters: shared dict updated with stamped / skipped / failed counts.
    """
    handler = _PortMetaHandler(stamper, counters)
    observer = Observer()
    observer.schedule(handler, str(watch_dir), recursive=True)
    observer.start()
    logger.info("watcher started on %s", watch_dir)
    return observer


def process_existing(watch_dir: Path, stamper: Stamper, counters: dict) -> None:
    """Walk watch_dir once and stamp every capture directory found.

    Useful for replay mode: stamp everything currently on disk before starting
    to watch for new arrivals.
    """
    watch_dir = Path(watch_dir)
    found = sorted(watch_dir.glob("board_*_*/port1_meta.json"))
    logger.info("found %d existing capture(s) in %s", len(found), watch_dir)
    for port_meta in found:
        capture_dir = port_meta.parent
        try:
            metadata = capture_dir / "metadata.json"
            if not metadata.exists():
                logger.warning(
                    "%s has port1_meta.json but no metadata.json — skipping",
                    capture_dir.name,
                )
                counters["failed"] += 1
                continue
            result = stamper.stamp(capture_dir)
            if result is None:
                counters["skipped"] += 1
            else:
                counters["stamped"] += 1
        except Exception as exc:  # noqa: BLE001
            logger.error("failed to stamp %s: %s", capture_dir.name, exc)
            counters["failed"] += 1
