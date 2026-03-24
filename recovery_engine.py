#!/usr/bin/env python3
"""Recovery engine for Ecnyss - self-healing and failure recovery.

Handles cleanup of corrupted artifacts, recovery from failed cycles,
and emergency repairs to restore system health.
"""
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

from health_monitor import HealthMonitor
from evolution_executor import EvolutionExecutor
from self_reader import EcnyssReader

class RecoveryEngine:
    """Self-healing engine for Ecnyss."""
    
    def __init__(self, base_path: str = "/root/Ecnyss"):
        self.base_path = Path(base_path)
        self.monitor = HealthMonitor(base_path)
        self.executor = EvolutionExecutor(base_path)
        self.reader = EcnyssReader(base_path)
    
    def clean_corrupted_artifacts(self) -> List[str]:
        """Remove known corrupted files from failed cycles."""
        corrupted = [
            "placeholder.py",  # Cycle 8 incomplete plan
            "rel/path.py"      # Cycle 16 invalid output
        ]
        
        removed = []
        for rel_path in corrupted:
            full_path = self.base_path / rel_path
            if full_path.exists():
                try:
                    full_path.unlink()
                    removed.append(rel_path)
                    self._log_recovery("remove_corrupted", rel_path, "Removed corrupted artifact")
                except Exception as e:
                    self._log_recovery("remove_corrupted", rel_path, f"Failed to remove: {e}")
        
        return removed
    
    def handle_failed_cycle(self, cycle: int, error: str) -> bool:
        """Recover from a failed evolution cycle."""
        self._log_recovery("cycle_failure", str(cycle), f"Recovering from: {error}")
        
        # Clean up corrupted artifacts
        cleaned = self.clean_corrupted_artifacts()
        
        # Check health
        health = self.monitor.generate_health_report()
        
        if health["overall_status"] == "healthy":
            self._log_recovery("cycle_recovery", str(cycle), "System healthy after cleanup")
            return True
        
        # Attempt repairs if still unhealthy
        repairs = self._attempt_repairs(health)
        self._log_recovery("cycle_recovery", str(cycle), f"Repairs attempted: {len(repairs)}")
        
        return len(repairs) > 0
    
    def _attempt_repairs(self, health_report: Dict) -> List[str]:
        """Attempt to repair detected issues."""
        repairs = []
        
        # Remove invalid files
        for invalid in health_report.get("file_health", {}).get("invalid_files", []):
            path = invalid["path"]
            full_path = self.base_path / path
            if full_path.exists():
                try:
                    full_path.unlink()
                    repairs.append(f"removed_invalid:{path}")
                except Exception:
                    pass
        
        return repairs
    
    def _log_recovery(self, action: str, target: str, result: str):
        """Log recovery action to evolution.jsonl."""
        entry = {
            "status": "recovery",
            "action": action,
            "target": target,
            "result": result,
            "timestamp": datetime.utcnow().isoformat(),
            "cycle": self._get_current_cycle(),
            "model": "recovery_engine"
        }
        
        with open(self.base_path / "evolution.jsonl", 'a') as f:
            f.write(json.dumps(entry) + '\n')
    
    def _get_current_cycle(self) -> int:
        """Get current cycle from evolution log."""
        entries = self.reader.read_evolution_log()
        if entries:
            return max(e.get('cycle', 0) for e in entries)
        return 0
    
    def emergency_repair(self) -> Dict[str, Any]:
        """Perform emergency repair when system is broken."""
        results = {
            "corrupted_removed": [],
            "health_before": None,
            "health_after": None,
            "success": False
        }
        
        results["health_before"] = self.monitor.generate_health_report()
        results["corrupted_removed"] = self.clean_corrupted_artifacts()
        results["health_after"] = self.monitor.generate_health_report()
        results["success"] = results["health_after"]["overall_status"] == "healthy"
        
        return results

    def recover(self) -> Dict[str, Any]:
        """Compatibility wrapper used by older runners."""
        return self.emergency_repair()

if __name__ == "__main__":
    engine = RecoveryEngine()
    results = engine.emergency_repair()
    print(json.dumps(results, indent=2))
    
    if results["success"]:
        print("\nSystem repaired successfully")
    else:
        print("\nSystem requires further attention")
