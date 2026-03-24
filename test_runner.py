#!/usr/bin/env python3
"""Test runner for Ecnyss - validates functionality of system components.

Executes tests on system modules to verify they work correctly before
marking cycles as successful. Prevents broken code from persisting (cycle 24).
"""
import importlib
import sys
import traceback
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

class TestRunner:
    """Runs functional tests on Ecnyss components."""
    
    def __init__(self, base_path: str = "/root/Ecnyss"):
        self.base_path = Path(base_path)
        self.test_results = []
    
    def test_imports(self) -> Dict[str, Any]:
        """Test that all modules can be imported without errors."""
        modules = [
            "self_reader",
            "state_tracker", 
            "output_validator",
            "code_analyzer",
            "cycle_optimizer",
            "decision_engine",
            "evolution_executor",
            "autonomous_orchestrator",
            "health_monitor",
            "recovery_engine",
            "cycle_driver",
        ]
        
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "total": len(modules),
            "passed": 0,
            "failed": [],
            "details": {}
        }
        
        for mod_name in modules:
            try:
                # Add base path to sys.path temporarily
                if str(self.base_path) not in sys.path:
                    sys.path.insert(0, str(self.base_path))
                
                module = importlib.import_module(mod_name)
                results["passed"] += 1
                results["details"][mod_name] = {"status": "ok", "error": None}
            except Exception as e:
                results["failed"].append({
                    "module": mod_name,
                    "error": str(e),
                    "traceback": traceback.format_exc()
                })
                results["details"][mod_name] = {"status": "failed", "error": str(e)}
        
        return results
    
    def test_functionality(self) -> Dict[str, Any]:
        """Test basic functionality of key components."""
        tests = []
        
        # Test self_reader
        try:
            from self_reader import EcnyssReader
            reader = EcnyssReader(self.base_path)
            files = reader.list_python_files()
            tests.append({
                "name": "self_reader.list_python_files",
                "status": "ok" if len(files) > 0 else "failed",
                "details": f"Found {len(files)} files"
            })
        except Exception as e:
            tests.append({
                "name": "self_reader",
                "status": "failed",
                "error": str(e)
            })
        
        # Test state_tracker
        try:
            from state_tracker import StateTracker
            tracker = StateTracker(self.base_path)
            state = tracker.load_state()
            tests.append({
                "name": "state_tracker.load_state",
                "status": "ok",
                "details": f"State has {len(state.get('files', []))} files"
            })
        except Exception as e:
            tests.append({
                "name": "state_tracker",
                "status": "failed",
                "error": str(e)
            })
        
        # Test output_validator
        try:
            from output_validator import OutputValidator
            validator = OutputValidator()
            plan = {
                "action": "create",
                "files": [{"path": "test.py", "content": "# test"}],
                "summary": "Test",
                "reasoning": "Testing"
            }
            valid, errors = validator.validate_plan_structure(plan)
            tests.append({
                "name": "output_validator.validate_plan_structure",
                "status": "ok" if valid else "failed",
                "details": f"Valid: {valid}"
            })
        except Exception as e:
            tests.append({
                "name": "output_validator",
                "status": "failed",
                "error": str(e)
            })
        
        # Test health_monitor
        try:
            from health_monitor import HealthMonitor
            monitor = HealthMonitor(self.base_path)
            healthy = monitor.is_system_healthy()
            tests.append({
                "name": "health_monitor.is_system_healthy",
                "status": "ok",
                "details": f"Healthy: {healthy}"
            })
        except Exception as e:
            tests.append({
                "name": "health_monitor",
                "status": "failed",
                "error": str(e)
            })
        
        passed = sum(1 for t in tests if t["status"] == "ok")
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "total": len(tests),
            "passed": passed,
            "failed": len(tests) - passed,
            "tests": tests
        }
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run complete test suite."""
        import_tests = self.test_imports()
        func_tests = self.test_functionality()
        
        all_passed = (
            import_tests["failed"] == [] and 
            func_tests["failed"] == 0
        )
        
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_status": "passed" if all_passed else "failed",
            "import_tests": import_tests,
            "functionality_tests": func_tests,
            "summary": {
                "modules_ok": import_tests["passed"],
                "modules_failed": len(import_tests["failed"]),
                "functions_ok": func_tests["passed"],
                "functions_failed": func_tests["failed"]
            }
        }
        
        self._log_results(report)
        return report
    
    def _log_results(self, report: Dict):
        """Log test results to test_results.jsonl."""
        log_path = self.base_path / "test_results.jsonl"
        with open(log_path, 'a') as f:
            f.write(json.dumps(report) + '\n')
    
    def is_system_functional(self) -> bool:
        """Quick check for integration into cycle pipeline."""
        report = self.run_all_tests()
        return report["overall_status"] == "passed"

    def run(self) -> Dict[str, Any]:
        """Compatibility wrapper used by older runners."""
        report = self.run_all_tests()
        summary = report.get("summary", {})
        return {
            "passed": int(summary.get("functions_ok", 0)) + int(summary.get("modules_ok", 0)),
            "failed": int(summary.get("functions_failed", 0)) + int(summary.get("modules_failed", 0)),
            "overall_status": report.get("overall_status"),
        }

if __name__ == "__main__":
    runner = TestRunner()
    report = runner.run_all_tests()
    
    print(json.dumps(report["summary"], indent=2))
    
    if report["overall_status"] != "passed":
        print("\nFAILED TESTS:")
        for mod in report["import_tests"].get("failed", []):
            print(f"  - {mod['module']}: {mod['error']}")
        for test in report["functionality_tests"].get("tests", []):
            if test["status"] != "ok":
                print(f"  - {test['name']}: {test.get('error', 'Unknown error')}")
        sys.exit(1)
    else:
        print("\nAll tests passed!")
        sys.exit(0)
