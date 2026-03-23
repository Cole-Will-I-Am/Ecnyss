#!/usr/bin/env python3
"""Main entry point for Ecnyss autonomous evolution system.

Cycle 45: Integrated ContextManager for intelligent context selection
to optimize LLM context window usage as system scales beyond 25 files.
"""
import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

# Ecnyss components
from context_manager import ContextManager
from state_tracker import StateTracker
from decision_engine import DecisionEngine
from evolution_executor import EvolutionExecutor
from evolution_analyzer import EvolutionAnalyzer
from test_runner import TestRunner
from health_monitor import HealthMonitor
from backup_manager import BackupManager
from maintenance_engine import MaintenanceEngine
from performance_tracker import PerformanceTracker
from cycle_optimizer import CycleOptimizer
from semantic_validator import SemanticValidator
from dependency_analyzer import DependencyAnalyzer
from extraction_repair import ExtractionRepair
from recovery_engine import RecoveryEngine
from code_analyzer import CodeAnalyzer
from output_validator import OutputValidator


class EcnyssRunner:
    """Main runner for autonomous evolution cycles with context optimization."""
    
    def __init__(self, base_path: str = "/root/Ecnyss"):
        self.base_path = Path(base_path)
        self.cycle = self._get_current_cycle()
        
        # Initialize all components
        self.context_manager = ContextManager(base_path=str(base_path))
        self.state_tracker = StateTracker(base_path=str(base_path))
        self.decision_engine = DecisionEngine()
        self.evolution_executor = EvolutionExecutor()
        self.evolution_analyzer = EvolutionAnalyzer()
        self.test_runner = TestRunner()
        self.health_monitor = HealthMonitor()
        self.backup_manager = BackupManager(base_path=str(base_path))
        self.maintenance_engine = MaintenanceEngine()
        self.performance_tracker = PerformanceTracker()
        self.cycle_optimizer = CycleOptimizer()
        self.semantic_validator = SemanticValidator()
        self.dependency_analyzer = DependencyAnalyzer()
        self.extraction_repair = ExtractionRepair()
        self.recovery_engine = RecoveryEngine()
        self.code_analyzer = CodeAnalyzer()
        self.output_validator = OutputValidator()
        
        print(f"[Ecnyss] Initialized for cycle #{self.cycle}")
    
    def _get_current_cycle(self) -> int:
        """Determine current cycle from evolution log."""
        evolution_file = self.base_path / "evolution.jsonl"
        if not evolution_file.exists():
            return 1
        
        try:
            with open(evolution_file, 'r') as f:
                lines = f.readlines()
                if not lines:
                    return 1
                last_line = lines[-1].strip()
                if not last_line:
                    return 1
                entry = json.loads(last_line)
                return entry.get("cycle", 1)
        except (json.JSONDecodeError, IOError):
            return 1
    
    def run_cycle(self) -> Dict[str, Any]:
        """Execute one autonomous evolution cycle."""
        start_time = time.time()
        
        try:
            # Get context-optimized file list
            context_files = self.context_manager.get_optimized_context()
            
            # Track state
            state = self.state_tracker.capture_state(context_files)
            
            # Make evolution decision
            decision = self.decision_engine.decide(state)
            
            # Execute evolution
            result = self.evolution_executor.execute(decision, context_files)
            
            # Analyze evolution
            analysis = self.evolution_analyzer.analyze(result)
            
            # Run tests
            test_results = self.test_runner.run()
            
            # Monitor health
            health = self.health_monitor.check()
            
            # Backup if needed
            if analysis.get("success"):
                self.backup_manager.create_backup()
            
            # Track performance
            duration = time.time() - start_time
            self.performance_tracker.record_cycle(self.cycle, duration, analysis)
            
            # Optimize next cycle
            self.cycle_optimizer.optimize()
            
            # Validate semantically
            semantic_valid = self.semantic_validator.validate(result)
            
            # Analyze dependencies
            deps = self.dependency_analyzer.analyze()
            
            # Repair if needed
            if not semantic_valid:
                self.extraction_repair.repair(result)
            
            # Recovery if health issues
            if not health.get("healthy"):
                self.recovery_engine.recover()
            
            # Analyze code quality
            code_quality = self.code_analyzer.analyze()
            
            # Validate output
            output_valid = self.output_validator.validate(result)
            
            # Log evolution
            self._log_evolution(analysis, test_results, health)
            
            self.cycle += 1
            
            return {
                "cycle": self.cycle - 1,
                "success": analysis.get("success", False),
                "duration": duration,
                "files_modified": result.get("files_modified", 0),
                "tests_passed": test_results.get("passed", 0),
                "health": health.get("healthy", False)
            }
            
        except Exception as e:
            print(f"[Ecnyss] Cycle error: {str(e)}")
            self.recovery_engine.recover()
            return {
                "cycle": self.cycle,
                "success": False,
                "error": str(e)
            }
    
    def _log_evolution(self, analysis: Dict, tests: Dict, health: Dict) -> None:
        """Log evolution entry to JSONL file."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "cycle": self.cycle,
            "analysis": analysis,
            "tests": tests,
            "health": health,
            "context_files": self.context_manager.get_optimized_context()
        }
        
        evolution_file = self.base_path / "evolution.jsonl"
        with open(evolution_file, 'a') as f:
            f.write(json.dumps(entry) + "\n")
    
    def run_multiple_cycles(self, count: int = 1) -> List[Dict[str, Any]]:
        """Run multiple evolution cycles."""
        results = []
        for i in range(count):
            print(f"[Ecnyss] Starting cycle #{self.cycle}")
            result = self.run_cycle()
            results.append(result)
            print(f"[Ecnyss] Cycle #{self.cycle - 1} complete: {result.get('success')}")
        return results


def main():
    """Main entry point."""
    base_path = sys.argv[1] if len(sys.argv) > 1 else "/root/Ecnyss"
    cycles = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    
    runner = EcnyssRunner(base_path=base_path)
    results = runner.run_multiple_cycles(count=cycles)
    
    print(f"[Ecnyss] Completed {len(results)} cycles")
    successful = sum(1 for r in results if r.get("success"))
    print(f"[Ecnyss] Success rate: {successful}/{len(results)}")


if __name__ == "__main__":
    main()
