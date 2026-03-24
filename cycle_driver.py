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
        file_count = len(self.reader.list_python_files())
        existing_files = {f.name for f in self.base_path.glob("*.py")}

        # Enhancement candidates — each is only proposed if the file doesn't already exist
        enhancements = [
            {
                "path": "evolution_metrics.py",
                "summary": "Add evolution metrics collector for cycle performance tracking",
                "content": '#!/usr/bin/env python3\n"""Metrics collector for Ecnyss evolution tracking."""\nimport json\nfrom pathlib import Path\nfrom typing import Dict, Any\nfrom datetime import datetime, timezone\n\n\nclass EvolutionMetrics:\n    """Collect and query per-cycle metrics."""\n\n    def __init__(self, base_path: str = "/root/Ecnyss"):\n        self.base_path = Path(base_path)\n        self.metrics_file = self.base_path / "metrics.jsonl"\n\n    def record(self, cycle: int, success: bool, duration: float, extra: Dict[str, Any] | None = None) -> None:\n        entry = {\n            "cycle": cycle,\n            "timestamp": datetime.now(timezone.utc).isoformat(),\n            "success": success,\n            "duration": round(duration, 3),\n        }\n        if extra:\n            entry.update(extra)\n        with open(self.metrics_file, "a") as f:\n            f.write(json.dumps(entry) + "\\n")\n\n    def recent(self, n: int = 10) -> list:\n        if not self.metrics_file.exists():\n            return []\n        entries = []\n        with open(self.metrics_file) as f:\n            for line in f:\n                line = line.strip()\n                if line:\n                    try:\n                        entries.append(json.loads(line))\n                    except json.JSONDecodeError:\n                        continue\n        return entries[-n:]\n\n\nif __name__ == "__main__":\n    m = EvolutionMetrics()\n    m.record(0, True, 1.0)\n    print(m.recent())\n',
            },
            {
                "path": "cycle_scheduler.py",
                "summary": "Add cron-style scheduler for timed autonomous evolution cycles",
                "content": '#!/usr/bin/env python3\n"""Scheduler for running Ecnyss evolution cycles on a timer."""\nimport time\nimport sys\nfrom pathlib import Path\nfrom datetime import datetime, timezone\n\nsys.path.insert(0, str(Path(__file__).parent))\n\nfrom cycle_driver import CycleDriver\n\n\ndef run_loop(interval_seconds: int = 420, max_cycles: int = 0) -> None:\n    """Run evolution cycles in a loop with a sleep interval.\n\n    Args:\n        interval_seconds: Pause between cycles (default 7 minutes).\n        max_cycles: Stop after this many cycles (0 = unlimited).\n    """\n    driver = CycleDriver()\n    completed = 0\n    while max_cycles == 0 or completed < max_cycles:\n        ts = datetime.now(timezone.utc).isoformat()\n        print(f"[scheduler] {ts} — starting cycle")\n        try:\n            success = driver.run_autonomous_cycle()\n            status = "ok" if success else "failed"\n        except Exception as exc:\n            status = f"error: {exc}"\n        completed += 1\n        print(f"[scheduler] cycle {completed} {status}, sleeping {interval_seconds}s")\n        time.sleep(interval_seconds)\n\n\nif __name__ == "__main__":\n    interval = int(sys.argv[1]) if len(sys.argv) > 1 else 420\n    run_loop(interval_seconds=interval)\n',
            },
            {
                "path": "git_integrator.py",
                "summary": "Add standalone git integration for auto-committing evolution results",
                "content": '#!/usr/bin/env python3\n"""Git integration helper for Ecnyss autonomous commits."""\nimport subprocess\nfrom pathlib import Path\nfrom typing import List, Optional\n\n\nclass GitIntegrator:\n    """Lightweight git operations scoped to the Ecnyss repo."""\n\n    def __init__(self, repo_path: str = "/root/Ecnyss"):\n        self.repo = Path(repo_path)\n\n    def _run(self, args: List[str], timeout: int = 30) -> subprocess.CompletedProcess:\n        return subprocess.run(\n            ["git", "-C", str(self.repo), *args],\n            capture_output=True, text=True, timeout=timeout,\n        )\n\n    def has_changes(self) -> bool:\n        r = self._run(["status", "--porcelain"])\n        return bool(r.stdout.strip())\n\n    def stage_files(self, paths: List[str]) -> None:\n        for p in paths:\n            self._run(["add", "--", p])\n\n    def commit(self, message: str) -> bool:\n        r = self._run(["commit", "-m", message])\n        return r.returncode == 0\n\n    def push(self, remote: str = "origin", branch: Optional[str] = None) -> bool:\n        if branch is None:\n            r = self._run(["rev-parse", "--abbrev-ref", "HEAD"])\n            branch = r.stdout.strip() or "main"\n        r = self._run(["push", remote, branch], timeout=60)\n        return r.returncode == 0\n\n    def log(self, n: int = 5) -> str:\n        r = self._run(["log", "--oneline", f"-{n}"])\n        return r.stdout.strip()\n\n\nif __name__ == "__main__":\n    gi = GitIntegrator()\n    print("Has changes:", gi.has_changes())\n    print("Recent commits:")\n    print(gi.log())\n',
            },
        ]

        for enh in enhancements:
            if enh["path"] not in existing_files:
                return {
                    "action": "create",
                    "files": [{"path": enh["path"], "content": enh["content"]}],
                    "summary": enh["summary"],
                    "reasoning": f"Cycle {cycle}: system has {file_count} files. Adding {enh['path']} to improve autonomous capabilities.",
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
