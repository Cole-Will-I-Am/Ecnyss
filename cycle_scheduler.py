#!/usr/bin/env python3
"""Scheduler for running Ecnyss evolution cycles on a timer."""
import time
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))

from cycle_driver import CycleDriver


def run_loop(interval_seconds: int = 420, max_cycles: int = 0) -> None:
    """Run evolution cycles in a loop with a sleep interval.

    Args:
        interval_seconds: Pause between cycles (default 7 minutes).
        max_cycles: Stop after this many cycles (0 = unlimited).
    """
    driver = CycleDriver()
    completed = 0
    while max_cycles == 0 or completed < max_cycles:
        ts = datetime.now(timezone.utc).isoformat()
        print(f"[scheduler] {ts} — starting cycle")
        try:
            success = driver.run_autonomous_cycle()
            status = "ok" if success else "failed"
        except Exception as exc:
            status = f"error: {exc}"
        completed += 1
        print(f"[scheduler] cycle {completed} {status}, sleeping {interval_seconds}s")
        time.sleep(interval_seconds)


if __name__ == "__main__":
    interval = int(sys.argv[1]) if len(sys.argv) > 1 else 420
    run_loop(interval_seconds=interval)
