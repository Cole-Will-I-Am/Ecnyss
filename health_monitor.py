#!/usr/bin/env python3
"""Health monitor for Ecnyss - system integrity and health checking.

Validates system state, detects corruption, and reports health metrics.
Integrates with autonomous_orchestrator to prevent evolution of broken states.
"""
import ast
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from self_reader import EcnyssReader

class HealthMonitor:
    """Monitors Ecnyss system health and integrity."""
    
    def __init__(self, base_path: str = "/root/Ecnyss"):
        self.base_path = Path(base_path)
        self.reader = EcnyssReader(base_path)
        self.health_log = self.base_path / "health.jsonl"
    
    def check_python_syntax(self, file_path: Path) -> Tuple[bool, Optional[str]]:
        """Check if a Python file has valid syntax."""
        try:
            content = file_path.read_text()
            ast.parse(content)
            return True, None
        except SyntaxError as e:
            return False, f"Syntax error: {e}"
        except Exception as e:
            return False, str(e)
    
    def check_all_files(self) -> Dict[str, Any]:
        """Check all Python files for syntax errors."""
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "total_files": 0,
            "valid_files": 0,
            "invalid_files": [],
            "missing_critical": []
        }
        
        py_files = self.reader.list_python_files()
        results["total_files"] = len(py_files)
        
        critical_files = [
            "self_reader.py",
            "state_tracker.py", 
            "output_validator.py",
            "code_analyzer.py",
            "cycle_optimizer.py",
            "decision_engine.py",
            "evolution_executor.py",
            "autonomous_orchestrator.py"
        ]
        
        for rel_path in py_files:
            full_path = self.base_path / rel_path
            valid, error = self.check_python_syntax(full_path)
            
            if valid:
                results["valid_files"] += 1
            else:
                results["invalid_files"].append({
                    "path": rel_path,
                    "error": error
                })
        
        for critical in critical_files:
            if not (self.base_path / critical).exists():
                results["missing_critical"].append(critical)
        
        return results
    
    def check_evolution_health(self, window: int = 5) -> Dict[str, Any]:
        """Check recent evolution health."""
        entries = self.reader.read_evolution_log()
        recent = entries[-window:] if len(entries) >= window else entries
        
        failures = [e for e in recent if e.get('status') != 'ok']
        
        return {
            "recent_cycles": len(recent),
            "failures": len(failures),
            "failure_rate": len(failures) / len(recent) if recent else 0,
            "last_failure": failures[-1] if failures else None,
            "consecutive_failures": self._count_consecutive_failures(entries)
        }
    
    def _count_consecutive_failures(self, entries: List[Dict]) -> int:
        """Count consecutive failures at the end of the log."""
        count = 0
        for entry in reversed(entries):
            if entry.get('status') != 'ok':
                count += 1
            else:
                break
        return count
    
    def generate_health_report(self) -> Dict[str, Any]:
        """Generate comprehensive health report."""
        file_health = self.check_all_files()
        evolution_health = self.check_evolution_health()
        
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "cycle": self._get_current_cycle(),
            "file_health": file_health,
            "evolution_health": evolution_health,
            "overall_status": "healthy" if self._is_healthy(file_health, evolution_health) else "degraded"
        }
        
        self._log_health(report)
        return report
    
    def _get_current_cycle(self) -> int:
        """Get current cycle from evolution log."""
        entries = self.reader.read_evolution_log()
        if entries:
            return max(e.get('cycle', 0) for e in entries)
        return 0
    
    def _is_healthy(self, file_health: Dict, evolution_health: Dict) -> bool:
        """Determine if system is healthy."""
        if file_health.get("invalid_files"):
            return False
        if file_health.get("missing_critical"):
            return False
        if evolution_health.get("consecutive_failures", 0) >= 2:
            return False
        if evolution_health.get("failure_rate", 0) > 0.5:
            return False
        return True
    
    def _log_health(self, report: Dict):
        """Log health report to health.jsonl."""
        with open(self.health_log, 'a') as f:
            f.write(json.dumps(report) + '\n')
    
    def get_health_history(self, limit: int = 10) -> List[Dict]:
        """Get recent health reports."""
        if not self.health_log.exists():
            return []
        
        entries = []
        with open(self.health_log, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return entries[-limit:]
    
    def is_system_healthy(self) -> bool:
        """Quick check for orchestrator integration."""
        report = self.generate_health_report()
        return report["overall_status"] == "healthy"

if __name__ == "__main__":
    monitor = HealthMonitor()
    report = monitor.generate_health_report()
    print(json.dumps(report, indent=2))
    
    if report["overall_status"] != "healthy":
        print("\nWARNING: System health is degraded!")
        if report["file_health"]["invalid_files"]:
            print("Invalid files detected:")
            for f in report["file_health"]["invalid_files"]:
                print(f"  - {f['path']}: {f['error']}")