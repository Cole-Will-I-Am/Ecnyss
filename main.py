#!/usr/bin/env python3
"""Main entry point for Ecnyss autonomous evolution (cycle 36).

Integrates maintenance engine for log compaction, orphaned file cleanup,
and sustainable long-term autonomous operation.
"""
import sys
import json
from pathlib import Path
from datetime import datetime

# Import all infrastructure components
from health_monitor import HealthMonitor
from recovery_engine import RecoveryEngine
from dependency_analyzer import DependencyAnalyzer
from self_reader import EcnyssReader
from code_analyzer import CodeAnalyzer
from decision_engine import DecisionEngine
from output_validator import OutputValidator
from evolution_executor import EvolutionExecutor
from backup_manager import BackupManager
from maintenance_engine import MaintenanceEngine
from evolution_analyzer import EvolutionAnalyzer

def get_current_cycle(base_path: Path) -> int:
    """Determine current cycle from evolution log."""
    log_path = base_path / "evolution.jsonl"
    if not log_path.exists():
        return 1
    
    max_cycle = 0
    try:
        with open(log_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    cycle = entry.get('cycle', 0)
                    if cycle > max_cycle:
                        max_cycle = cycle
                except json.JSONDecodeError:
                    continue
    except Exception:
        pass
    
    return max_cycle + 1

def main():
    """Execute autonomous evolution cycle with full maintenance integration."""
    base_path = Path("/root/Ecnyss")
    current_cycle = get_current_cycle(base_path)
    
    print(f"=== Ecnyss Cycle #{current_cycle} ===")
    print(f"Started at: {datetime.utcnow().isoformat()}")
    
    # Initialize all components
    health = HealthMonitor(str(base_path))
    recovery = RecoveryEngine(str(base_path))
    deps = DependencyAnalyzer(str(base_path))
    reader = EcnyssReader(str(base_path))
    analyzer = CodeAnalyzer()
    decision = DecisionEngine()
    validator = OutputValidator()
    executor = EvolutionExecutor(str(base_path))
    backup = BackupManager(str(base_path), retention_cycles=10)
    maintenance = MaintenanceEngine(str(base_path))
    evo_analyzer = EvolutionAnalyzer(str(base_path))
    
    orphaned_files = []
    
    try:
        # Step 1: Health check
        print("\n[1/9] Health monitoring...")
        health_status = health.full_system_check()
        if not health_status.get("healthy", False):
            print("Health issues detected, attempting recovery...")
            recovery.clean_corrupted_artifacts()
            health_status = health.full_system_check()
        print(f"Health status: {'HEALTHY' if health_status.get('healthy') else 'DEGRADED'}")
        
        # Step 2: Dependency analysis (capture orphans for maintenance)
        print("\n[2/9] Dependency analysis...")
        dep_analysis = deps.analyze_dependencies()
        orphaned_files = dep_analysis.get("orphaned_files", [])
        circular_deps = dep_analysis.get("circular_dependencies", [])
        core_files = dep_analysis.get("core_files", [])
        
        print(f"Dependencies: {len(dep_analysis.get('dependencies', {}))} files")
        print(f"Orphaned files: {len(orphaned_files)}")
        print(f"Circular dependencies: {len(circular_deps)}")
        print(f"Core infrastructure files: {len(core_files)}")
        
        # Step 3: Self-reading
        print("\n[3/9] Self-reading...")
        context = reader.gather_context_for_evolution()
        print(f"Read {len(context.get('files', []))} files")
        
        # Step 4: Code analysis
        print("\n[4/9] Code analysis...")
        analysis_results = []
        for file_path in context.get("files", []):
            if file_path in orphaned_files:
                continue  # Skip orphaned files
            content = reader.read_file(file_path)
            if content:
                issues = analyzer.analyze_file(content, file_path)
                analysis_results.extend(issues)
        print(f"Found {len(analysis_results)} code issues")
        
        # Step 5: Evolution analysis (learn from history)
        print("\n[5/9] Evolution analysis...")
        patterns = evo_analyzer.analyze_patterns()
        recent_failures = evo_analyzer.detect_failure_patterns()
        if recent_failures:
            print(f"Warning: {len(recent_failures)} recent failures detected")
        
        # Step 6: Decision making
        print("\n[6/9] Decision making...")
        plan = decision.generate_evolution_plan(context, analysis_results)
        plan['cycle'] = current_cycle
        print(f"Decision: {plan.get('action', 'none')} - {plan.get('summary', 'No action')}")
        
        # Step 7: Plan validation
        print("\n[7/9] Plan validation...")
        valid, errors = validator.validate_plan_structure(plan)
        if not valid:
            print(f"Validation failed: {errors}")
            return 1
        print("Plan validation passed")
        
        # Step 8: Evolution execution
        print("\n[8/9] Evolution execution...")
        success, executed = executor.execute_plan(plan, current_cycle)
        if not success:
            print(f"Execution failed: {executed}")
            return 1
        print(f"Successfully executed: {executed}")
        
        # Step 9: Backup cleanup
        print("\n[9/9] Backup management...")
        cleanup_result = backup.cleanup_old_backups(current_cycle)
        storage_stats = backup.get_storage_stats()
        print(f"Backups: {cleanup_result.get('removed', 0)} removed, {storage_stats.get('total_size_mb', 0):.2f}MB total")
        
        # Step 10: Maintenance (NEW - Cycle 36)
        print("\n[10/10] Maintenance...")
        
        # Remove orphaned files identified in step 2
        if orphaned_files:
            maintenance_result = maintenance.cleanup_orphaned_files(orphaned_files)
            print(f"Removed {maintenance_result.get('removed', 0)} orphaned files")
        
        # Compact evolution log to prevent unbounded growth
        compact_result = maintenance.compact_evolution_log(current_cycle)
        if compact_result.get('compacted', False):
            print(f"Compacted evolution log: {compact_result.get('archived_entries', 0)} entries archived")
        
        # Archive old backups for audit trails
        archive_result = maintenance.archive_old_backups(current_cycle, retention_cycles=20)
        if archive_result.get('archived', 0) > 0:
            print(f"Archived {archive_result.get('archived', 0)} old backups")
        
        print(f"\n=== Cycle #{current_cycle} completed successfully ===")
        return 0
        
    except Exception as e:
        print(f"\n!!! Critical error in cycle execution: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())