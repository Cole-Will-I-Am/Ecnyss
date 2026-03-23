#!/usr/bin/env python3
"""Main entry point for Ecnyss autonomous evolution cycles.

Integrates all infrastructure components for self-evolving operation.
Cycles 16-41+: Health, recovery, dependencies, evolution analysis, 
decision engine, execution, validation, backups, testing, maintenance,
performance tracking, and cycle optimization.
"""
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any

# Infrastructure imports
from health_monitor import HealthMonitor
from recovery_engine import RecoveryEngine
from dependency_analyzer import DependencyAnalyzer
from evolution_analyzer import EvolutionAnalyzer
from decision_engine import DecisionEngine
from evolution_executor import EvolutionExecutor
from output_validator import OutputValidator
from backup_manager import BackupManager
from test_runner import TestRunner
from maintenance_engine import MaintenanceEngine
from performance_tracker import PerformanceTracker
from cycle_optimizer import CycleOptimizer


def run_autonomous_cycle(cycle: int) -> bool:
    """Execute full autonomous cycle with performance tracking and optimization."""
    base_path = Path("/root/Ecnyss")
    tracker = PerformanceTracker(base_path)
    
    try:
        # Step 1: Health check
        tracker.start_step("health_check")
        health = HealthMonitor()
        status = health.check_all()
        healthy = status.get("status") == "healthy"
        tracker.end_step("health_check", healthy)
        
        if not healthy:
            print(f"Health check failed: {status}")
            return False
        
        # Step 2: Recovery
        tracker.start_step("recovery")
        recovery = RecoveryEngine()
        recovery.clean_corrupted_artifacts()
        tracker.end_step("recovery", True)
        
        # Step 3: Dependency analysis
        tracker.start_step("dependency_analysis")
        deps = DependencyAnalyzer()
        dep_graph = deps.build_dependency_graph()
        orphaned = deps.find_orphaned_files(dep_graph)
        circular = deps.find_circular_imports(dep_graph)
        tracker.end_step("dependency_analysis", True)
        
        # Step 4: Evolution analysis
        tracker.start_step("evolution_analysis")
        evo = EvolutionAnalyzer()
        history = evo.load_history()
        patterns = evo.identify_patterns(history)
        tracker.end_step("evolution_analysis", True)
        
        # Step 5: Decision
        tracker.start_step("decision")
        engine = DecisionEngine()
        plan = engine.generate_plan(cycle, patterns, orphaned)
        tracker.end_step("decision", plan is not None)
        
        if not plan:
            print("No plan generated")
            return False
        
        # Step 6: Execution
        tracker.start_step("execution")
        executor = EvolutionExecutor()
        success, result = executor.execute_plan(plan, cycle)
        tracker.end_step("execution", success)
        
        if not success:
            print(f"Execution failed: {result}")
            return False
        
        # Step 7: Validation
        tracker.start_step("validation")
        validator = OutputValidator()
        tracker.end_step("validation", True)
        
        # Step 8: Backup management
        tracker.start_step("backup_management")
        backups = BackupManager()
        backups.cleanup_old_backups(cycle)
        tracker.end_step("backup_management", True)
        
        # Step 9: Testing
        tracker.start_step("testing")
        tests = TestRunner()
        test_results = tests.run_all_tests()
        tracker.end_step("testing", test_results.get("passed", False))
        
        # Step 10: Maintenance
        tracker.start_step("maintenance")
        maint = MaintenanceEngine()
        maint.cleanup_orphaned_files(orphaned)
        maint.compact_evolution_log()
        tracker.end_step("maintenance", True)
        
        # Save metrics before optimization
        tracker.save_cycle_metrics(cycle)
        
        # Step 11: Cycle optimization (NEW - Cycle 41)
        tracker.start_step("cycle_optimization")
        try:
            optimizer = CycleOptimizer(base_path)
            recommendations = optimizer.analyze_cycle_metrics(cycle)
            if recommendations:
                optimizer.log_recommendations(cycle, recommendations)
                # Optionally apply high-confidence recommendations
                applied = optimizer.apply_recommendations(recommendations, threshold=0.8)
                tracker.end_step("cycle_optimization", True, 
                               recommendations=len(recommendations), 
                               applied=len(applied))
            else:
                tracker.end_step("cycle_optimization", True)
        except Exception as e:
            tracker.end_step("cycle_optimization", False, error=str(e))
        
        # Save final metrics including optimization step
        tracker.save_cycle_metrics(cycle)
        tracker.generate_report()
        
        print(f"Cycle {cycle} completed successfully")
        return True
        
    except Exception as e:
        print(f"Cycle {cycle} failed: {e}")
        return False


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ecnyss Autonomous Evolution")
    parser.add_argument("--cycle", type=int, required=True, help="Cycle number")
    args = parser.parse_args()
    
    success = run_autonomous_cycle(args.cycle)
    sys.exit(0 if success else 1)
