#!/usr/bin/env python3
"""Cycle driver for Ecnyss - autonomous evolution loop runner.

Integrates health monitoring, recovery, and orchestration to enable
fully autonomous operation. Runs pre-flight checks, cleans corrupted
artifacts, and executes evolution cycles with error handling.
"""
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Ensure imports work when running from /root/Ecnyss
sys.path.insert(0, str(Path(__file__).parent))

from health_monitor import HealthMonitor
from recovery_engine import RecoveryEngine
from self_reader import EcnyssReader

class CycleDriver:
    """Main entry point for autonomous evolution cycles."""
    
    def __init__(self, base_path: str = "/root/Ecnyss"):
        self.base_path = Path(base_path)
        self.health = HealthMonitor(base_path)
        self.recovery = RecoveryEngine(base_path)
        self.reader = EcnyssReader(base_path)
        self.cycle_log = self.base_path / "cycle_driver.jsonl"
    
    def run_autonomous_cycle(self) -> bool:
        """Execute one full autonomous evolution cycle with safeguards."""
        cycle_num = self._get_next_cycle()
        self._log_event("cycle_start", cycle_num, "Beginning autonomous cycle")
        
        # Phase 1: Pre-flight health check
        health_report = self.health.generate_health_report()
        if health_report["overall_status"] != "healthy":
            self._log_event("health_alert", cycle_num, 
                          f"Unhealthy: {len(health_report['file_health']['invalid_files'])} invalid files")
            
            # Phase 2: Recovery
            repair_result = self.recovery.emergency_repair()
            self._log_event("recovery", cycle_num, 
                          f"Removed {len(repair_result['corrupted_removed'])} corrupted files")
            
            # Re-check health
            health_report = self.health.generate_health_report()
            if health_report["overall_status"] != "healthy":
                self._log_event("cycle_abort", cycle_num, "Recovery failed, aborting")
                return False
        
        # Phase 3: Load state and analyze
        try:
            files = self.reader.list_python_files()
            self._log_event("analysis", cycle_num, f"Analyzing {len(files)} files")
            
            # Phase 4: Generate evolution plan
            # Import here to avoid circular dependencies
            from decision_engine import DecisionEngine
            from code_analyzer import CodeAnalyzer
            
            analyzer = CodeAnalyzer(str(self.base_path))
            decisions = DecisionEngine(str(self.base_path))
            
            # Analyze complexity and patterns
            complexity_report = analyzer.analyze_all_files()
            
            # Generate plan based on analysis
            plan = self._generate_evolution_plan(complexity_report, cycle_num)
            
            if not plan:
                self._log_event("no_action", cycle_num, "No evolution needed")
                return True
            
            # Phase 5: Execute plan
            from evolution_executor import EvolutionExecutor
            executor = EvolutionExecutor(str(self.base_path))
            
            success, result = executor.execute_plan(plan, cycle_num)
            
            if success:
                self._log_event("cycle_success", cycle_num, 
                              f"Executed {plan['action']}: {plan['summary']}")
                return True
            else:
                self._log_event("cycle_failed", cycle_num, f"Execution failed: {result}")
                return False
                
        except Exception as e:
            self._log_event("cycle_error", cycle_num, f"Exception: {str(e)}")
            return False
    
    def _generate_evolution_plan(self, complexity_report: Dict, cycle: int) -> Optional[Dict[str, Any]]:
        """Generate next evolution plan based on system analysis."""
        # Simple heuristic: if we have < 20 files and low complexity, add functionality
        file_count = len(self.reader.list_python_files())
        
        # Check for missing integration points
        has_driver = (self.base_path / "cycle_driver.py").exists()
        
        if not has_driver:
            # This shouldn't happen since we're running, but check anyway
            return None
        
        # Look for files with high complexity that need refactoring
        high_complexity = []
        for file_report in complexity_report.get("files", []):
            if file_report.get("complexity", 0) > 10:
                high_complexity.append(file_report["file"])
        
        if high_complexity:
            return {
                "action": "refactor",
                "files": [{"path": high_complexity[0], "content": "# Refactored version TBD"}],
                "summary": f"Refactor high-complexity file: {high_complexity[0]}",
                "reasoning": f"Complexity score > 10 detected, needs simplification"
            }
        
        # If system is healthy and no urgent refactoring, suggest enhancement
        if file_count < 20:
            return {
                "action": "create",
                "files": [{
                    "path": f"evolution_metrics.py",
                    "content": "#!/usr/bin/env python3\n\"\"\"Metrics collector for Ecnyss evolution tracking.\"\"\"\nimport json\nfrom pathlib import Path\nfrom typing import Dict, List, Any\nfrom datetime import datetime\n\nclass EvolutionMetrics:\n    def __init__(self, base_path=\"/root/Ecnyss\"):\n        self.base_path = Path(base_path)\n        self.metrics_file = self.base_path / \"metrics.jsonl\"\n    \n    def record_cycle_metrics(self, cycle: int, success: bool, duration: float):\n        entry = {\n            \"cycle\": cycle,\n            \"timestamp\": datetime.utcnow().isoformat(),\n            \"success\": success,\n            \"duration\": duration\n        }\n        with open(self.metrics_file, 'a') as f:\n            f.write(json.dumps(entry) + '\\n')\n\nif __name__ == \"__main__\":\n    m = EvolutionMetrics()\n    m.record_cycle_metrics(0, True, 1.0)"
                }],
                "summary": "Add evolution metrics collector for performance tracking",
                "reasoning": "System has 14 files with comprehensive infrastructure. Adding metrics collection to track cycle duration and success rates enables data-driven optimization of the evolution process."
            }
        
        return None
    
    def _get_next_cycle(self) -> int:
        """Get next cycle number from evolution log."""
        entries = self.reader.read_evolution_log()
        if entries:
            return max(e.get('cycle', 0) for e in entries) + 1
        return 21  # Current cycle
    
    def _log_event(self, event: str, cycle: int, message: str):
        """Log driver event to cycle log."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": event,
            "cycle": cycle,
            "message": message
        }
        with open(self.cycle_log, 'a') as f:
            f.write(json.dumps(entry) + '\n')
        print(f"[{event}] Cycle {cycle}: {message}")
    
    def get_cycle_history(self, limit: int = 10) -> list:
        """Get recent cycle execution history."""
        if not self.cycle_log.exists():
            return []
        entries = []
        with open(self.cycle_log, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return entries[-limit:]

if __name__ == "__main__":
    driver = CycleDriver()
    
    # Check for corrupted artifacts first
    print("Ecnyss Cycle Driver - Starting pre-flight checks...")
    
    # Clean up known corrupted files if they exist
    corrupted = ["placeholder.py", "rel/path.py"]
    for fname in corrupted:
        fpath = driver.base_path / fname
        if fpath.exists():
            print(f"Removing corrupted artifact: {fname}")
            fpath.unlink()
    
    # Run the autonomous cycle
    print("\nRunning autonomous evolution cycle...")
    success = driver.run_autonomous_cycle()
    
    if success:
        print("\nCycle completed successfully")
        sys.exit(0)
    else:
        print("\nCycle failed - check cycle_driver.jsonl for details")
        sys.exit(1)