#!/usr/bin/env python3
"""Ecnyss autonomous runner - main entry point for self-evolution.

Executes pre-flight cleanup, health validation, historical analysis,
functional testing, and runs autonomous cycles with data-driven insights.
Completes the integration of evolution analyzer (cycle 27).
"""
import sys
from pathlib import Path
from typing import List

from health_monitor import HealthMonitor
from cycle_driver import CycleDriver
from test_runner import TestRunner
from evolution_analyzer import EvolutionAnalyzer
from self_reader import EcnyssReader


def clean_corrupted_artifacts(base_path: Path) -> List[str]:
    """Remove known corrupted artifacts from earlier cycles.
    
    Cycle 8: placeholder.py (incomplete plan marker)
    Cycle 16: rel/path.py (invalid 'full code' content)
    """
    corrupted = [
        "placeholder.py",
        "rel/path.py",
    ]
    
    cleaned = []
    for path_str in corrupted:
        path = base_path / path_str
        if path.exists():
            try:
                path.unlink()
                cleaned.append(path_str)
                print(f"[RECOVERY] Cleaned corrupted artifact: {path_str}")
            except Exception as e:
                print(f"[ERROR] Failed to remove {path_str}: {e}")
    
    return cleaned


def get_current_cycle(base_path: Path) -> int:
    """Determine current cycle from evolution log."""
    reader = EcnyssReader(base_path)
    entries = reader.read_evolution_log()
    if entries:
        return max(e.get('cycle', 0) for e in entries)
    return 0


def main() -> int:
    """Run Ecnyss autonomous evolution."""
    base_path = Path("/root/Ecnyss")
    
    # Get actual current cycle (fixes hardcoded #25 from cycle 22)
    current_cycle = get_current_cycle(base_path)
    
    print("=" * 60)
    print(f"Ecnyss Autonomous System - Cycle #{current_cycle}")
    print("=" * 60)
    
    # Step 1: Clean corrupted artifacts from failed cycles
    print("\n[1/6] Running recovery for corrupted artifacts...")
    cleaned = clean_corrupted_artifacts(base_path)
    if cleaned:
        print(f"Recovered {len(cleaned)} corrupted file(s)")
    else:
        print("No corrupted artifacts found")
    
    # Step 2: System health validation (syntax)
    print("\n[2/6] Validating system health...")
    health = HealthMonitor(base_path)
    report = health.generate_health_report()
    
    print(f"  Status: {report['overall_status'].upper()}")
    print(f"  Files: {report['file_health']['valid_files']}/{report['file_health']['total_files']} valid")
    
    if report['file_health']['invalid_files']:
        print("  Invalid files detected:")
        for f in report['file_health']['invalid_files']:
            print(f"    - {f['path']}: {f['error']}")
    
    if report['overall_status'] != 'healthy':
        print("\n[ABORT] System health degraded. Run recovery before evolution.")
        return 1
    
    # Step 3: Evolution analysis (NEW: integrates evolution_analyzer from cycle 26)
    print("\n[3/6] Analyzing evolution history...")
    try:
        analyzer = EvolutionAnalyzer(base_path)
        insights = analyzer.generate_insights()
        
        print(f"  Historical success rate: {insights.get('success_rate', 0):.1%}")
        print(f"  Total cycles analyzed: {insights.get('total_cycles', 0)}")
        
        if insights.get('recommendations'):
            print("  Recommendations:")
            for rec in insights['recommendations'][:3]:
                print(f"    - {rec}")
        
        if insights.get('problematic_files'):
            print("  Problematic files:")
            for f in insights['problematic_files'][:3]:
                print(f"    - {f}")
    except Exception as e:
        print(f"  [WARNING] Could not generate insights: {e}")
        insights = {}
    
    # Step 4: Functional testing
    print("\n[4/6] Running functional tests...")
    tester = TestRunner(base_path)
    test_results = tester.run_all_tests()
    
    if not test_results['overall_success']:
        print(f"\n[ABORT] Functional tests failed: {test_results['failures']} failure(s)")
        for module, result in test_results['results'].items():
            if not result['success']:
                print(f"  - {module}: {result.get('error', 'unknown error')}")
        return 1
    
    print(f"  All tests passed: {test_results['passed']}/{test_results['total']} modules")
    
    # Step 5: Execute autonomous evolution cycle
    print("\n[5/6] Executing autonomous evolution cycle...")
    try:
        driver = CycleDriver(base_path)
        # Pass insights to driver if supported (graceful degradation if not)
        try:
            success = driver.run_cycle(context=insights)
        except TypeError:
            success = driver.run_cycle()
        
        if success:
            print("\n[SUCCESS] Autonomous cycle completed")
        else:
            print("\n[WARNING] Cycle completed with issues")
            return 1
            
    except Exception as e:
        print(f"\n[ERROR] Cycle execution failed: {e}")
        return 1
    
    # Step 6: Post-cycle validation (syntax + functional)
    print("\n[6/6] Post-cycle validation...")
    final_health = health.generate_health_report()
    if final_health['overall_status'] != 'healthy':
        print("[DEGRADED] System health issues detected post-cycle")
        return 1
    
    final_tests = tester.run_all_tests()
    if not final_tests['overall_success']:
        print(f"[DEGRADED] Post-cycle tests failed: {final_tests['failures']} failure(s)")
        return 1
    
    print("[READY] System healthy, all tests passing, ready for next cycle")
    return 0


if __name__ == "__main__":
    sys.exit(main())
