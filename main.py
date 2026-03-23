#!/usr/bin/env python3
"""Main entry point for Ecnyss autonomous evolution (Cycle 32).

Integrates dependency analysis into the autonomous pipeline to detect
architectural issues like orphaned files (e.g., rel/path.py) and circular 
imports before they cause evolution failures.
"""
import sys
import json
from pathlib import Path

def main():
    base_path = Path("/root/Ecnyss")
    
    # Import Ecnyss infrastructure
    from health_monitor import HealthMonitor
    from dependency_analyzer import DependencyAnalyzer
    from decision_engine import DecisionEngine
    from extraction_repair import ExtractionRepair
    from evolution_executor import EvolutionExecutor
    from test_runner import TestRunner
    from state_tracker import StateTracker
    
    # Initialize components
    health = HealthMonitor(str(base_path))
    tracker = StateTracker(str(base_path))
    
    # Get current cycle
    current_cycle = tracker.get_current_cycle()
    print(f"=== Ecnyss Cycle #{current_cycle} ===")
    
    # Step 1: Health check
    print("\n[1/7] Health Check...")
    healthy, issues = health.check_system_health()
    if not healthy:
        print(f"Health issues detected: {issues}")
        from recovery_engine import RecoveryEngine
        recovery = RecoveryEngine(str(base_path))
        recovery.recover_from_failure(current_cycle, "health_check_failed")
        return 1
    print("System healthy")
    
    # Step 2: Dependency Analysis (Cycle 32 Integration)
    print("\n[2/7] Dependency Analysis...")
    arch_context = {}
    try:
        deps = DependencyAnalyzer(str(base_path))
        dep_report = deps.analyze_all()
        
        orphaned = dep_report.get('orphaned_files', [])
        circular = dep_report.get('circular_dependencies', [])
        core_files = dep_report.get('core_files', [])
        
        if orphaned:
            print(f"WARNING: Found {len(orphaned)} orphaned files: {orphaned}")
        if circular:
            print(f"WARNING: Detected {len(circular)} circular dependencies")
        print(f"Core infrastructure files: {len(core_files)}")
        
        arch_context = {
            "orphaned_files": orphaned,
            "circular_dependencies": circular,
            "core_files": core_files,
            "total_files": dep_report.get('total_files', 0),
            "total_dependencies": dep_report.get('total_dependencies', 0)
        }
        
    except Exception as e:
        print(f"Dependency analysis error (non-fatal): {e}")
        arch_context = {"error": str(e)}
    
    # Step 3: Evolution Analysis
    print("\n[3/7] Evolution Analysis...")
    try:
        from self_reader import EcnyssReader
        reader = EcnyssReader(str(base_path))
        history = reader.read_evolution_log()
        recent = history[-10:] if len(history) >= 10 else history
        successes = sum(1 for e in recent if e.get('status') == 'ok')
        print(f"Recent success rate: {successes}/{len(recent)}")
    except Exception as e:
        print(f"Evolution analysis error: {e}")
        history = []
    
    # Step 4: Decision Engine
    print("\n[4/7] Decision Engine...")
    engine = DecisionEngine(str(base_path))
    context = {
        "cycle": current_cycle,
        "architectural_analysis": arch_context,
        "recent_history": history[-5:] if 'history' in locals() else []
    }
    decision = engine.generate_evolution_plan(context)
    
    # Step 5: Extraction Repair (handles malformed JSON)
    print("\n[5/7] Parsing Decision Output...")
    repair = ExtractionRepair()
    decision_str = json.dumps(decision) if isinstance(decision, dict) else str(decision)
    plan, repairs_made = repair.extract_and_repair(decision_str)
    
    if not plan:
        print("Failed to parse decision output, using fallback plan")
        plan = repair.get_fallback_plan("Decision parsing failed after repairs")
    
    print(f"Plan: {plan.get('action', 'unknown')} - {plan.get('summary', 'no summary')}")
    if repairs_made:
        print(f"Applied repairs: {repairs_made}")
    
    # Step 6: Execution
    print("\n[6/7] Execution...")
    executor = EvolutionExecutor(str(base_path))
    success, results = executor.execute_plan(plan, current_cycle)
    
    if not success:
        print(f"Execution failed: {results}")
        return 1
    
    print(f"Successfully executed: {results}")
    
    # Step 7: Validation
    print("\n[7/7] Post-cycle Validation...")
    runner = TestRunner(str(base_path))
    test_results = runner.run_all_tests()
    
    if test_results.get('success'):
        print("All tests passed - cycle complete")
        tracker.record_cycle_completion(current_cycle, "success")
    else:
        print(f"Tests failed: {test_results.get('failures', [])}")
        tracker.record_cycle_completion(current_cycle, "test_failure")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
