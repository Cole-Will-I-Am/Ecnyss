#!/usr/bin/env python3
"""Performance tracker for Ecnyss - collects execution metrics and pipeline statistics.

Tracks timing, memory usage, and success rates for each pipeline step
to enable data-driven optimization decisions (cycle 37+).
"""
import json
import time
import os
import psutil
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from contextlib import contextmanager


class PerformanceTracker:
    """Tracks performance metrics for autonomous pipeline execution."""
    
    def __init__(self, base_path: str = "/root/Ecnyss"):
        self.base_path = Path(base_path)
        self.metrics_file = self.base_path / ".ecnyss_metrics.jsonl"
        self.current_cycle = 0
        self.step_timings = {}
        self.step_memory = {}
        self.step_outcomes = {}
        self.process = psutil.Process()
        
    def start_cycle(self, cycle: int):
        """Initialize tracking for a new cycle."""
        self.current_cycle = cycle
        self.step_timings = {}
        self.step_memory = {}
        self.step_outcomes = {}
        self._cycle_start_time = time.monotonic()
        self._cycle_start_memory = self.process.memory_info().rss
    
    @contextmanager
    def track_step(self, step_name: str):
        """Context manager to track a pipeline step's execution."""
        start_time = time.monotonic()
        start_memory = self.process.memory_info().rss
        
        try:
            yield self
            success = True
            error = None
        except Exception as e:
            success = False
            error = str(e)
            raise
        finally:
            end_time = time.monotonic()
            end_memory = self.process.memory_info().rss
            
            self.step_timings[step_name] = round(end_time - start_time, 3)
            self.step_memory[step_name] = {
                "delta_mb": round((end_memory - start_memory) / (1024 * 1024), 2),
                "peak_mb": round(end_memory / (1024 * 1024), 2)
            }
            self.step_outcomes[step_name] = {"success": success, "error": error if not success else None}
    
    def record_step(self, step_name: str, duration_ms: float, success: bool = True, metadata: Optional[Dict] = None):
        """Manually record a step completion."""
        self.step_timings[step_name] = duration_ms
        self.step_outcomes[step_name] = {"success": success, "metadata": metadata or {}}
    
    def end_cycle(self, overall_success: bool = True) -> Dict[str, Any]:
        """Finalize tracking for current cycle and persist metrics."""
        total_time = round(time.monotonic() - self._cycle_start_time, 3)
        total_memory_delta = round(
            (self.process.memory_info().rss - self._cycle_start_memory) / (1024 * 1024), 2
        )
        
        metrics = {
            "cycle": self.current_cycle,
            "timestamp": datetime.utcnow().isoformat(),
            "total_time_sec": total_time,
            "memory_delta_mb": total_memory_delta,
            "overall_success": overall_success,
            "steps": {}
        }
        
        for step in self.step_timings:
            metrics["steps"][step] = {
                "time_sec": self.step_timings[step],
                "memory": self.step_memory.get(step, {}),
                "outcome": self.step_outcomes.get(step, {"success": True})
            }
        
        # Persist to metrics log
        with open(self.metrics_file, 'a') as f:
            f.write(json.dumps(metrics) + '\n')
        
        return metrics
    
    def get_cycle_stats(self, cycles: int = 10) -> Dict[str, Any]:
        """Analyze recent cycle performance statistics."""
        if not self.metrics_file.exists():
            return {"status": "no_data"}
        
        recent_metrics = []
        with open(self.metrics_file, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    recent_metrics.append(entry)
                except json.JSONDecodeError:
                    continue
        
        # Take last N cycles
        recent_metrics = recent_metrics[-cycles:]
        
        if not recent_metrics:
            return {"status": "no_data"}
        
        # Calculate aggregates
        total_times = [m["total_time_sec"] for m in recent_metrics]
        success_count = sum(1 for m in recent_metrics if m["overall_success"])
        
        # Per-step aggregates
        step_stats = {}
        for metric in recent_metrics:
            for step_name, step_data in metric.get("steps", {}).items():
                if step_name not in step_stats:
                    step_stats[step_name] = {"times": [], "successes": 0, "failures": 0}
                step_stats[step_name]["times"].append(step_data["time_sec"])
                if step_data.get("outcome", {}).get("success", True):
                    step_stats[step_name]["successes"] += 1
                else:
                    step_stats[step_name]["failures"] += 1
        
        # Compute averages
        for step_name, stats in step_stats.items():
            times = stats["times"]
            stats["avg_time_sec"] = round(sum(times) / len(times), 3) if times else 0
            stats["max_time_sec"] = round(max(times), 3) if times else 0
            stats["min_time_sec"] = round(min(times), 3) if times else 0
            stats["total_executions"] = len(times)
            del stats["times"]  # Remove raw data
        
        return {
            "cycles_analyzed": len(recent_metrics),
            "success_rate": round(success_count / len(recent_metrics), 2),
            "avg_cycle_time_sec": round(sum(total_times) / len(total_times), 2),
            "max_cycle_time_sec": round(max(total_times), 2),
            "step_breakdown": step_stats,
            "slowest_step": max(step_stats.items(), key=lambda x: x[1]["avg_time_sec"])[0] if step_stats else None
        }
    
    def identify_bottlenecks(self, threshold_sec: float = 5.0) -> List[Dict[str, Any]]:
        """Identify pipeline steps that consistently exceed threshold."""
        stats = self.get_cycle_stats(cycles=20)
        
        if stats.get("status") == "no_data":
            return []
        
        bottlenecks = []
        for step_name, step_stats in stats.get("step_breakdown", {}).items():
            if step_stats["avg_time_sec"] > threshold_sec:
                bottlenecks.append({
                    "step": step_name,
                    "avg_time_sec": step_stats["avg_time_sec"],
                    "max_time_sec": step_stats["max_time_sec"],
                    "executions": step_stats["total_executions"]
                })
        
        return sorted(bottlenecks, key=lambda x: x["avg_time_sec"], reverse=True)
    
    def get_recommendations(self) -> List[str]:
        """Generate optimization recommendations based on metrics."""
        recommendations = []
        stats = self.get_cycle_stats(cycles=10)
        
        if stats.get("status") == "no_data":
            return ["Insufficient data for recommendations"]
        
        # Check success rate
        if stats["success_rate"] < 0.9:
            recommendations.append(
                f"Low success rate detected ({stats['success_rate']:.0%}). "
                "Consider adding more validation or recovery steps."
            )
        
        # Check for slow cycles
        if stats["avg_cycle_time_sec"] > 60:
            recommendations.append(
                f"Cycles are slow (avg {stats['avg_cycle_time_sec']}s). "
                f"Review '{stats['slowest_step']}' step for optimization."
            )
        
        # Check specific bottlenecks
        bottlenecks = self.identify_bottlenecks(threshold_sec=10.0)
        for bottleneck in bottlenecks[:3]:
            recommendations.append(
                f"Step '{bottleneck['step']}' is slow (avg {bottleneck['avg_time_sec']}s, "
                f"max {bottleneck['max_time_sec']}s). Consider caching or parallelization."
            )
        
        return recommendations if recommendations else ["No significant issues detected"]


if __name__ == "__main__":
    tracker = PerformanceTracker()
    
    # Simulate tracking
    tracker.start_cycle(37)
    
    with tracker.track_step("health_check"):
        time.sleep(0.1)
    
    with tracker.track_step("dependency_analysis"):
        time.sleep(0.2)
    
    metrics = tracker.end_cycle(overall_success=True)
    print(f"Cycle metrics: {json.dumps(metrics, indent=2)}")
    
    print("\nRecent stats:", json.dumps(tracker.get_cycle_stats(), indent=2))
    print("\nRecommendations:", tracker.get_recommendations())
