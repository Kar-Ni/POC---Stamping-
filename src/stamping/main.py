"""CLI entrypoint for the stamping POC.

Usage:
    python -m stamping.main --watch-dir samples/
    python -m stamping.main --single-capture samples/board_0_<UUID>/
    python -m stamping.main --watch-dir samples/ --process-existing
    python -m stamping.main --version
"""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import time
from pathlib import Path

from . import __version__
from .gps import SimulatedGPS
from .stamper import Stamper
from .watcher import process_existing, watch


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
        datefmt="%H:%M:%S",
    )


def _print_summary(counters: dict) -> None:
    print(
        f"\nSummary: stamped={counters['stamped']} "
        f"skipped={counters['skipped']} "
        f"failed={counters['failed']}",
        file=sys.stderr,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="stamping",
        description="ID-IQ Stamping POC v1 — basic-mode stamper",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--watch-dir", type=Path, help="watch this directory for new captures")
    group.add_argument("--single-capture", type=Path, help="stamp exactly one directory and exit")
    group.add_argument("--version", action="store_true", help="print version and exit")
    parser.add_argument(
        "--process-existing",
        action="store_true",
        help="with --watch-dir, also process captures already on disk before watching",
    )
    parser.add_argument("--verbose", action="store_true", help="DEBUG-level logging")
    args = parser.parse_args()

    if args.version:
        print(f"stamping {__version__}")
        return 0

    _setup_logging(args.verbose)

    gps = SimulatedGPS()
    stamper = Stamper(gps=gps)
    counters = {"stamped": 0, "skipped": 0, "failed": 0}

    if args.single_capture is not None:
        try:
            result = stamper.stamp(args.single_capture)
            if result is None:
                counters["skipped"] += 1
            else:
                counters["stamped"] += 1
        except Exception as exc:  # noqa: BLE001
            logging.error("failed to stamp %s: %s", args.single_capture, exc)
            counters["failed"] += 1
        _print_summary(counters)
        return 0 if counters["failed"] == 0 else 1

    # watch-dir mode
    if not args.watch_dir.exists():
        logging.error("watch directory does not exist: %s", args.watch_dir)
        return 2

    if args.process_existing:
        process_existing(args.watch_dir, stamper, counters)

    observer = watch(args.watch_dir, stamper, counters)

    stop = {"flag": False}

    def _on_signal(signum, frame):  # noqa: ARG001
        stop["flag"] = True

    signal.signal(signal.SIGINT, _on_signal)
    signal.signal(signal.SIGTERM, _on_signal)

    try:
        while not stop["flag"]:
            time.sleep(0.1)
    finally:
        observer.stop()
        observer.join(timeout=2.0)
        _print_summary(counters)

    return 0


if __name__ == "__main__":
    sys.exit(main())
