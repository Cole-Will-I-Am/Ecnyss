#!/usr/bin/env python3
"""Ecnyss autonomous runner - main entry point for self-evolution.

Executes pre-flight cleanup, health validation, and prepares for autonomous cycles.
Completes the infrastructure for fully autonomous operation (cycle 22).
"""
import sys
from pathlib import Path
from typing import List

from health_monitor import HealthMonitor


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


def main() -> int:
    """Run Ecnyss autonomous evolution pre-flight and validation."""
    base_path = Path("/root/Ecnyss")
    
    print("=" * 60)
    print("Ecnyss Autonomous System - Cycle #22 Entry Point")
    print("=" * 60)
    
    # Step 1: Clean corrupted artifacts from failed cycles
    print("\n[1/3] Running recovery for corrupted artifacts...")
    cleaned = clean_corrupted_artifacts(base_path)
    if cleaned:
        print(f"Recovered {len(cleaned)} corrupted file(s)")
    else:
        print("No corrupted artifacts found")
    
    # Step 2: System health validation
    print("\n[2/3] Validating system health...")
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
    
    # Step 3: Ready for autonomous operation
    print("\n[3/3] System validation complete")
    print("\nInfrastructure status:")
    print("  ✓ self_reader.py - Source reading")
    print("  ✓ state_tracker.py - State management") 
    print("  ✓ code_analyzer.py - Static analysis")
    print("  ✓ cycle_optimizer.py - Pattern optimization")
    print("  ✓ decision_engine.py - Evolution planning")
    print("  ✓ evolution_executor.py - File operations")
    print("  ✓ output_validator.py - Output validation")
    print("  ✓ autonomous_orchestrator.py - Component integration")
    print("  ✓ health_monitor.py - Integrity checking")
    print("  ✓ recovery_engine.py - Self-healing")
    print("  ✓ cycle_driver.py - Cycle orchestration")
    print("\n[READY] Ecnyss ready for autonomous evolution")
    print("Execute cycle_driver.py to begin self-modification loop")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())