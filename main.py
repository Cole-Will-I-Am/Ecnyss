#!/usr/bin/env python3
"""Ecnyss autonomous runner - main entry point for self-evolution.

Executes pre-flight cleanup, health validation, and runs autonomous cycles.
Completes the transition to fully autonomous operation (cycle 23).
"""
import sys
from pathlib import Path
from typing import List

from health_monitor import HealthMonitor
from cycle_driver import CycleDriver


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
    """Run Ecnyss autonomous evolution."""
    base_path = Path("/root/Ecnyss")
    
    print("=" * 60)
    print("Ecnyss Autonomous System - Cycle #23")
    print("=" * 60)
    
    # Step 1: Clean corrupted artifacts from failed cycles
    print("\n[1/4] Running recovery for corrupted artifacts...")
    cleaned = clean_corrupted_artifacts(base_path)
    if cleaned:
        print(f"Recovered {len(cleaned)} corrupted file(s)")
    else:
        print("No corrupted artifacts found")
    
    # Step 2: System health validation
    print("\n[2/4] Validating system health...")
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
    
    # Step 3: Execute autonomous evolution cycle
    print("\n[3/4] Executing autonomous evolution cycle...")
    try:
        driver = CycleDriver(base_path)
        success = driver.run_cycle()
        
        if success:
            print("\n[SUCCESS] Autonomous cycle completed")
        else:
            print("\n[WARNING] Cycle completed with issues")
            return 1
            
    except Exception as e:
        print(f"\n[ERROR] Cycle execution failed: {e}")
        return 1
    
    # Step 4: Post-cycle validation
    print("\n[4/4] Post-cycle health check...")
    final_report = health.generate_health_report()
    if final_report['overall_status'] == 'healthy':
        print("[READY] System healthy and ready for next cycle")
        return 0
    else:
        print("[DEGRADED] System health issues detected post-cycle")
        return 1


if __name__ == "__main__":
    sys.exit(main())