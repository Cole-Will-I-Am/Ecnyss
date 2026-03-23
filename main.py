#!/usr/bin/env python3
"""Main entry point for Ecnyss autonomous evolution system.

Cycle 39: Integrated performance tracking for data-driven optimization.
"""
import sys
import os
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from performance_tracker import PerformanceTracker
from health_monitor import HealthMonitor
from recovery_engine import RecoveryEngine
from autonomous_orchestrator import AutonomousOrchestrator
from backup_manager import BackupManager
from maintenance_engine import MaintenanceEngine
from dependency_analyzer import DependencyAnalyzer
from evolution_analyzer import EvolutionAnalyzer
from decision_engine import DecisionEngine
from evolution_executor import EvolutionExecutor
from output_validator import OutputValidator
from test_runner import TestRunner


def main():
    """Execute autonomous evolution cycle with performance tracking."""
    cycle = 39
    
    # Initialize performance tracker
    tracker = PerformanceTracker()
    tracker.start_step("cycle_init")
    tracker.end_step("cycle_init", success=True)
    
    try:
        # Step 1: Health check with performance tracking
        tracker.start_step("health_check")
        health = HealthMonitor()
        health_status = health.check_all()
        healthy = health_status.get('healthy', False)
        tracker.end_step("health_check", success=healthy, metadata=health_status)
        
        if not healthy:
            # Step 2: Recovery if needed
            tracker.start_step("recovery")
            recovery = RecoveryEngine()
            recovery_status = recovery.repair_all()
            tracker.end_step("recovery", success=recovery_status.get('repaired', False), metadata=recovery_status)
        
        # Step 3: Dependency analysis
        tracker.start_step("dependency_analysis")
        deps = DependencyAnalyzer()
        dep_report = deps.analyze_all()
        tracker.end_step("dependency_analysis", success=True, metadata={"orphaned_count": len(dep_report.get('orphaned', []))})
        
        # Step 4: Evolution analysis
        tracker.start_step("evolution_analysis")
        evo = EvolutionAnalyzer()
        patterns = evo.analyze_patterns()
        tracker.end_step("evolution_analysis", success=True, metadata={"patterns_found": len(patterns)})
        
        # Step 5: Decision engine
        tracker.start_step("decision_engine")
        decision = DecisionEngine()
        plan = decision.generate_next_action(cycle, patterns, dep_report)
        has_plan = plan is not None and plan.get('action') is not None
        tracker.end_step("decision_engine", success=has_plan, metadata={"action": plan.get('action') if has_plan else None})
        
        if has_plan:
            # Step 6: Evolution execution
            tracker.start_step("evolution_execution")
            executor = EvolutionExecutor()
            success, result = executor.execute_plan(plan, cycle)
            tracker.end_step("evolution_execution", success=success, metadata={"files_modified": len(result) if isinstance(result, list) else 0})
            
            # Step 7: Validation
            tracker.start_step("validation")
            validator = OutputValidator()
            valid, errors = validator.validate_plan_structure(plan)
            tracker.end_step("validation", success=valid, metadata={"errors": len(errors) if errors else 0})
        
        # Step 8: Backup management
        tracker.start_step("backup_management")
        backup = BackupManager()
        cleanup_result = backup.cleanup_old_backups(cycle)
        stats = backup.get_storage_stats()
        tracker.end_step("backup_management", success=True, metadata={"space_mb": stats.get('total_size_mb', 0)})
        
        # Step 9: Test running
        tracker.start_step("test_runner")
        runner = TestRunner()
        test_results = runner.run_all_tests()
        passed = test_results.get('passed', 0)
        total = test_results.get('total', 0)
        tracker.end_step("test_runner", success=passed > 0, metadata={"passed": passed, "total": total})
        
        # Step 10: Maintenance
        tracker.start_step("maintenance")
        maint = MaintenanceEngine()
        maint.compact_evolution_log()
        maint.cleanup_orphaned_files(dep_report.get('orphaned', []))
        tracker.end_step("maintenance", success=True)
        
        # Save performance metrics and generate report
        tracker.save_metrics(cycle)
        report = tracker.generate_report()
        
        print(f"\n=== Cycle {cycle} Complete ===")
        for line in report:
            print(line)
        
        # Identify bottlenecks for next cycle
        bottlenecks = tracker.identify_bottlenecks()
        if bottlenecks:
            print("\nBottlenecks detected:")
            for b in bottlenecks:
                print(f"  - {b}")
            
        return 0
        
    except Exception as e:
        tracker.end_step("cycle", success=False, metadata={"error": str(e)})
        tracker.save_metrics(cycle)
        print(f"Cycle failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())