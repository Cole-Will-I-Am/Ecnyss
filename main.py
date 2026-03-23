#!/usr/bin/env python3
"""Main entry point for Ecnyss autonomous evolution system.

Cycle 23: Execute autonomous cycles instead of just validating
Cycle 24-25: Integrated test runner for pre/post validation
Cycle 26-27: Integrated evolution analyzer for historical learning
Cycle 28-29: Integrated extraction repair for JSON robustness
Cycle 30-31: Integrated dependency analyzer for architectural awareness
Cycle 32-33: Integrated backup manager for storage health
"""
import json
import sys
import os
from pathlib import Path
from datetime import datetime

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from self_reader import EcnyssReader
from state_tracker import StateTracker
from code_analyzer import CodeAnalyzer
from cycle_optimizer import CycleOptimizer
from decision_engine import DecisionEngine
from evolution_executor import EvolutionExecutor
from health_monitor import HealthMonitor
from recovery_engine import RecoveryEngine
from cycle_driver import CycleDriver
from evolution_analyzer import EvolutionAnalyzer
from extraction_repair import ExtractionRepair
from dependency_analyzer import DependencyAnalyzer
from backup_manager import BackupManager


def main():
    """Execute autonomous evolution cycle."""
    base_path = Path("/root/Ecnyss")
    
    # Initialize all infrastructure components
    reader = EcnyssReader(base_path)
    tracker = StateTracker(base_path)
    analyzer = CodeAnalyzer(base_path)
    optimizer = CycleOptimizer(base_path)
    health = HealthMonitor(base_path)
    recovery = RecoveryEngine(base_path)
    executor = EvolutionExecutor(base_path)
    evo_analyzer = EvolutionAnalyzer(base_path)
    repair = ExtractionRepair()
    deps = DependencyAnalyzer(base_path)
    backup_mgr = BackupManager(base_path)
    
    # Get current cycle number
    current_cycle = tracker.get_current_cycle()
    print(f"=== Ecnyss Autonomous Evolution Cycle #{current_cycle} ===")
    
    # Step 0: Health check and recovery if needed
    print("\n[0/8] Health check...")
    health_report = health.full_system_check()
    if health_report['status'] != 'healthy':
        print(f"  Issues detected: {health_report['issues']}")
        recovery_report = recovery.attempt_recovery()
        print(f"  Recovery: {recovery_report}")
        if recovery_report.get('status') == 'failed':
            print("FATAL: Recovery failed, halting")
            return 1
    else:
        print("  System healthy")
    
    # Step 1: Read current state
    print("\n[1/8] Reading system state...")
    manifest = reader.generate_manifest()
    file_contents = {}
    for file_path in manifest['files']:
        content = reader.read_file(file_path)
        if content:
            file_contents[file_path] = content
    print(f"  Loaded {len(file_contents)} files")
    
    # Step 2: Dependency analysis (cycle 32)
    print("\n[2/8] Analyzing dependencies...")
    dep_report = deps.analyze_all()
    orphaned = dep_report.get('orphaned_files', [])
    circular = dep_report.get('circular_imports', [])
    core_files = dep_report.get('core_infrastructure', [])
    print(f"  Found {len(orphaned)} orphaned files, {len(circular)} circular dependencies")
    print(f"  Core infrastructure: {len(core_files)} files")
    
    # Step 3: Analyze code quality
    print("\n[3/8] Analyzing code quality...")
    quality_report = analyzer.analyze_all_files()
    print(f"  Analyzed {quality_report['summary']['files_analyzed']} files")
    print(f"  Total complexity: {quality_report['summary']['total_complexity']}")
    
    # Step 4: Analyze evolution history
    print("\n[4/8] Analyzing evolution patterns...")
    evo_insights = evo_analyzer.analyze_patterns()
    failure_patterns = evo_analyzer.get_failure_patterns()
    print(f"  Learned patterns: {len(evo_insights.get('learned_patterns', []))}")
    if failure_patterns:
        print(f"  Recent failures: {[f['type'] for f in failure_patterns[-3:]]}")
    
    # Step 5: Generate evolution plan
    print("\n[5/8] Generating evolution plan...")
    engine = DecisionEngine(
        file_contents=file_contents,
        quality_report=quality_report,
        cycle_history=evo_insights,
        dependency_report=dep_report
    )
    plan = engine.generate_plan(current_cycle)
    print(f"  Action: {plan.get('action', 'unknown')}")
    print(f"  Files: {[f.get('path') for f in plan.get('files', [])]}")
    print(f"  Summary: {plan.get('summary', 'N/A')}")
    
    # Step 6: Extract and repair JSON if needed (cycle 30)
    print("\n[6/8] Validating plan format...")
    if isinstance(plan, str):
        plan, repair_info = repair.extract_and_repair(plan)
        if repair_info['success']:
            print(f"  Repaired JSON using: {repair_info['method']}")
        else:
            print(f"  JSON repair failed, using fallback plan")
            plan = repair.get_fallback_plan(current_cycle)
    else:
        print("  Plan format valid")
    
    # Step 7: Execute plan
    print("\n[7/8] Executing evolution plan...")
    success, result = executor.execute_plan(plan, current_cycle)
    if success:
        print(f"  Success: {result}")
        tracker.record_cycle(plan, result)
    else:
        print(f"  Failed: {result}")
        tracker.record_failure('execution_failed', {'errors': result})
        return 1
    
    # Step 8: Cleanup old backups (cycle 34)
    print("\n[8/8] Managing backup storage...")
    cleanup_result = backup_mgr.cleanup_old_backups(current_cycle)
    storage_stats = backup_mgr.get_storage_stats()
    print(f"  Backups cleaned: {cleanup_result.get('removed', 0)}")
    print(f"  Space reclaimed: {cleanup_result.get('space_reclaimed_mb', 0)} MB")
    print(f"  Current backup storage: {storage_stats.get('total_size_mb', 0)} MB")
    
    # Emergency cleanup if needed
    if storage_stats.get('total_size_mb', 0) > 50:  # Threshold 50MB
        emergency = backup_mgr.emergency_cleanup(max_size_mb=30)
        if emergency.get('status') == 'emergency_cleaned':
            print(f"  Emergency cleanup: removed {emergency.get('removed', 0)} old backups")
    
    print(f"\n=== Cycle #{current_cycle} Complete ===")
    print(f"Next cycle will be: {current_cycle + 1}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
