#!/usr/bin/env python3
"""Main entry point for Ecnyss - executes autonomous evolution cycles.

Integrates health monitoring, evolution analysis, decision engine,
extraction repair, and execution pipeline for fully autonomous operation.
"""
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

# Import Ecnyss infrastructure
from health_monitor import HealthMonitor
from evolution_analyzer import EvolutionAnalyzer
from evolution_executor import EvolutionExecutor
from extraction_repair import ExtractionRepair
from test_runner import TestRunner
from self_reader import EcnyssReader


class CycleDriver:
    """Drives autonomous evolution cycles with full integration."""
    
    def __init__(self, base_path: str = "/root/Ecnyss"):
        self.base_path = Path(base_path)
        self.health = HealthMonitor(base_path)
        self.analyzer = EvolutionAnalyzer(base_path)
        self.executor = EvolutionExecutor(base_path)
        self.repair = ExtractionRepair()
        self.tester = TestRunner(base_path)
        self.reader = EcnyssReader(base_path)
        self.decision_engine_path = self.base_path / "decision_engine.py"
    
    def get_current_cycle(self) -> int:
        """Get current cycle from evolution log."""
        entries = self.reader.read_evolution_log()
        if entries:
            return max(e.get('cycle', 0) for e in entries)
        return 0
    
    def run_cycle(self) -> Dict[str, Any]:
        """Execute one full autonomous cycle."""
        cycle = self.get_current_cycle() + 1
        print(f"=== Ecnyss Cycle #{cycle} ===")
        
        results = {
            "cycle": cycle,
            "timestamp": datetime.utcnow().isoformat(),
            "steps": []
        }
        
        # Step 1/6: Health check
        print("[1/6] Running health checks...")
        health_report = self.health.generate_health_report()
        results["steps"].append({"step": 1, "name": "health_check", "status": health_report["overall_status"]})
        
        if health_report["overall_status"] != "healthy":
            print(f"WARNING: System health is {health_report['overall_status']}")
            if health_report["file_health"]["invalid_files"]:
                print("Invalid files detected, attempting recovery...")
                # Trigger recovery via health monitor's findings
        
        # Step 2/6: Pre-cycle testing
        print("[2/6] Running pre-cycle functional tests...")
        pre_test_results = self.tester.run_all_tests()
        results["steps"].append({
            "step": 2, 
            "name": "pre_cycle_tests", 
            "status": "passed" if pre_test_results["success"] else "failed",
            "details": pre_test_results
        })
        
        # Step 3/6: Evolution analysis
        print("[3/6] Analyzing evolution history...")
        analysis = self.analyzer.analyze_patterns()
        recommendations = self.analyzer.generate_recommendations(analysis)
        results["steps"].append({
            "step": 3,
            "name": "evolution_analysis",
            "success_rate": analysis.get("success_rate", 0),
            "recommendations": len(recommendations)
        })
        
        if recommendations:
            print(f"Recommendations: {recommendations[0]['message']}")
        
        # Step 4/6: Decision engine with extraction repair
        print("[4/6] Running decision engine...")
        decision_output = self._run_decision_engine(cycle, analysis)
        
        # Use extraction repair to parse decision output
        parsed_plan, repairs = self.repair.extract_and_repair(decision_output)
        
        if parsed_plan:
            print(f"  Parsed plan successfully (repairs: {len(repairs)})")
            if repairs:
                print(f"  Repair strategies used: {repairs}")
        else:
            print("  WARNING: Could not parse decision output, using fallback plan")
            parsed_plan = self.repair.get_fallback_plan(f"Failed repairs: {repairs}")
        
        results["steps"].append({
            "step": 4,
            "name": "decision",
            "action": parsed_plan.get("action"),
            "files": parsed_plan.get("files", []),
            "repairs_needed": len(repairs),
            "repair_types": repairs
        })
        
        # Step 5/6: Execute evolution plan
        print("[5/6] Executing evolution plan...")
        success, executed = self.executor.execute_plan(parsed_plan, cycle)
        results["steps"].append({
            "step": 5,
            "name": "execution",
            "success": success,
            "files": executed
        })
        
        if not success:
            print(f"  Execution failed: {executed}")
            results["status"] = "execution_failed"
            return results
        
        print(f"  Executed: {executed}")
        
        # Step 6/6: Post-cycle testing
        print("[6/6] Running post-cycle validation...")
        post_test_results = self.tester.run_all_tests()
        results["steps"].append({
            "step": 6,
            "name": "post_cycle_tests",
            "status": "passed" if post_test_results["success"] else "failed",
            "regressions": post_test_results.get("failed", [])
        })
        
        if not post_test_results["success"]:
            print("  WARNING: Post-cycle tests failed, potential regression")
            results["status"] = "test_failure"
        else:
            results["status"] = "ok"
        
        # Log extraction repair stats if any repairs were made
        if repairs:
            stats = self.repair.get_stats()
            print(f"  Extraction repair stats: {stats['successful_repairs']}/{stats['total_attempts']} successful")
        
        print(f"=== Cycle #{cycle} Complete: {results['status']} ===")
        return results
    
    def _run_decision_engine(self, cycle: int, analysis: Dict) -> str:
        """Run decision engine and return raw output."""
        # Import decision engine dynamically to handle changes
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("decision_engine", self.decision_engine_path)
            decision_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(decision_module)
            
            # Assume decision engine has a generate_decision function
            if hasattr(decision_module, 'generate_decision'):
                return decision_module.generate_decision(cycle, analysis)
            else:
                # Fallback: return a default plan as JSON string
                return json.dumps({
                    "action": "create",
                    "files": [],
                    "summary": "No decision engine available",
                    "reasoning": "Decision engine module not found or incompatible"
                })
        except Exception as e:
            # Return error as string for extraction repair to handle
            return f'{"action": "create", "files": [], "error": "{str(e)}"}'
    
    def run_autonomous_cycles(self, max_cycles: Optional[int] = None):
        """Run continuous autonomous cycles."""
        cycle_count = 0
        
        while max_cycles is None or cycle_count < max_cycles:
            try:
                result = self.run_cycle()
                cycle_count += 1
                
                # Stop on consecutive failures
                if result["status"] != "ok":
                    recent = self.health.check_evolution_health(window=3)
                    if recent.get("consecutive_failures", 0) >= 2:
                        print("Too many consecutive failures, stopping")
                        break
                        
            except Exception as e:
                print(f"Critical error in cycle: {e}")
                break


def main():
    """Entry point for autonomous operation."""
    driver = CycleDriver()
    
    # Check if we should run one cycle or continuous
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        driver.run_cycle()
    else:
        print("Starting autonomous evolution (press Ctrl+C to stop)...")
        driver.run_autonomous_cycles()


if __name__ == "__main__":
    main()
