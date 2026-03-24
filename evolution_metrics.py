#!/usr/bin/env python3
"""Metrics collector for Ecnyss evolution tracking."""
import json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime, timezone


class EvolutionMetrics:
    """Collect and query per-cycle metrics."""

    def __init__(self, base_path: str = "/root/Ecnyss"):
        self.base_path = Path(base_path)
        self.metrics_file = self.base_path / "metrics.jsonl"

    def record(self, cycle: int, success: bool, duration: float, extra: Dict[str, Any] | None = None) -> None:
        entry = {
            "cycle": cycle,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "success": success,
            "duration": round(duration, 3),
        }
        if extra:
            entry.update(extra)
        with open(self.metrics_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def recent(self, n: int = 10) -> list:
        if not self.metrics_file.exists():
            return []
        entries = []
        with open(self.metrics_file) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return entries[-n:]


if __name__ == "__main__":
    m = EvolutionMetrics()
    m.record(0, True, 1.0)
    print(m.recent())
