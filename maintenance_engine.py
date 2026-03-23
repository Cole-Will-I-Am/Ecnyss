#!/usr/bin/env python3
"""Maintenance engine for Ecnyss - performs periodic housekeeping and cleanup.

Manages log compaction, orphaned file cleanup, and system hygiene
to prevent degradation during long-running autonomous operation (cycle 35+).
"""
import json
import os
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import gzip


class MaintenanceEngine:
    """Performs system maintenance: log compaction, orphaned file cleanup, hygiene checks."""
    
    def __init__(self, base_path: str = "/root/Ecnyss", retention_days: int = 30):
        self.base_path = Path(base_path)
        self.retention_days = retention_days
        self.archive_dir = self.base_path / ".ecnyss_archive"
        self.archive_dir.mkdir(exist_ok=True)
        self.stats = {
            "logs_archived": 0,
            "orphans_removed": 0,
            "space_reclaimed_mb": 0,
            "last_maintenance": None
        }
    
    def compact_evolution_log(self, max_entries: int = 1000) -> Dict[str, Any]:
        """Archive old evolution.jsonl entries to prevent unbounded growth."""
        log_path = self.base_path / "evolution.jsonl"
        if not log_path.exists():
            return {"status": "no_log", "archived": 0}
        
        # Read all entries
        entries = []
        with open(log_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        
        if len(entries) <= max_entries:
            return {"status": "within_limits", "total_entries": len(entries)}
        
        # Split into keep and archive
        entries_to_archive = entries[:-max_entries]
        entries_to_keep = entries[-max_entries:]
        
        # Archive old entries
        archive_file = self.archive_dir / f"evolution_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.jsonl.gz"
        with gzip.open(archive_file, 'wt') as f:
            for entry in entries_to_archive:
                f.write(json.dumps(entry) + '\n')
        
        # Rewrite log with recent entries
        with open(log_path, 'w') as f:
            for entry in entries_to_keep:
                f.write(json.dumps(entry) + '\n')
        
        archived_size = len(entries_to_archive)
        self.stats["logs_archived"] += archived_size
        
        return {
            "status": "compacted",
            "archived": archived_size,
            "retained": len(entries_to_keep),
            "archive_file": str(archive_file.name)
        }
    
    def cleanup_orphaned_files(self, dependency_report: Dict[str, Any]) -> Dict[str, Any]:
        """Remove files identified as orphaned by dependency analyzer."""
        orphaned = dependency_report.get('orphaned_files', [])
        removed = []
        errors = []
        
        for filepath in orphaned:
            full_path = self.base_path / filepath
            if full_path.exists() and full_path.is_file():
                try:
                    size = full_path.stat().st_size
                    full_path.unlink()
                    removed.append(filepath)
                    self.stats["orphans_removed"] += 1
                    self.stats["space_reclaimed_mb"] += size / (1024 * 1024)
                except Exception as e:
                    errors.append(f"{filepath}: {str(e)}")
        
        return {
            "status": "cleaned" if removed else "no_action",
            "removed": removed,
            "count": len(removed),
            "errors": errors
        }
    
    def archive_old_cycles(self, current_cycle: int, keep_cycles: int = 20) -> Dict[str, Any]:
        """Archive backup files from cycles older than retention policy."""
        backup_dir = self.base_path / ".ecnyss_backups"
        if not backup_dir.exists():
            return {"status": "no_backups", "archived": 0}
        
        archived = []
        total_size = 0
        
        for backup_file in backup_dir.rglob("*.bak"):
            try:
                # Extract cycle number
                cycle_str = backup_file.stem.split('.')[-1]
                backup_cycle = int(cycle_str)
                
                if current_cycle - backup_cycle > keep_cycles:
                    # Move to archive instead of deleting
                    rel_path = backup_file.relative_to(backup_dir)
                    archive_path = self.archive_dir / "backups" / rel_path
                    archive_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    size = backup_file.stat().st_size
                    shutil.move(str(backup_file), str(archive_path))
                    archived.append(str(rel_path))
                    total_size += size
                    
            except (ValueError, IndexError, Exception):
                continue
        
        return {
            "status": "archived",
            "files": archived,
            "count": len(archived),
            "space_reclaimed_mb": round(total_size / (1024 * 1024), 2)
        }
    
    def run_maintenance(self, current_cycle: int, dependency_report: Optional[Dict] = None) -> Dict[str, Any]:
        """Run full maintenance suite."""
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "cycle": current_cycle,
            "tasks": {}
        }
        
        # Compact evolution log
        results["tasks"]["log_compaction"] = self.compact_evolution_log()
        
        # Archive old backups
        results["tasks"]["backup_archival"] = self.archive_old_cycles(current_cycle)
        
        # Cleanup orphaned files if report provided
        if dependency_report:
            results["tasks"]["orphan_cleanup"] = self.cleanup_orphaned_files(dependency_report)
        
        self.stats["last_maintenance"] = datetime.utcnow().isoformat()
        results["stats"] = self.stats.copy()
        
        return results
    
    def get_storage_summary(self) -> Dict[str, Any]:
        """Get summary of storage usage across all system components."""
        components = {
            "backups": self.base_path / ".ecnyss_backups",
            "archive": self.archive_dir,
            "logs": self.base_path / "evolution.jsonl"
        }
        
        summary = {}
        total_size = 0
        
        for name, path in components.items():
            if path.is_file():
                size = path.stat().st_size if path.exists() else 0
                summary[name] = {"size_mb": round(size / (1024 * 1024), 2), "type": "file"}
                total_size += size
            elif path.is_dir():
                size = sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
                file_count = sum(1 for _ in path.rglob('*') if _.is_file())
                summary[name] = {
                    "size_mb": round(size / (1024 * 1024), 2),
                    "files": file_count,
                    "type": "directory"
                }
                total_size += size
            else:
                summary[name] = {"size_mb": 0, "type": "missing"}
        
        summary["total_mb"] = round(total_size / (1024 * 1024), 2)
        return summary
    
    def get_stats(self) -> Dict[str, Any]:
        """Get maintenance statistics."""
        return self.stats.copy()


if __name__ == "__main__":
    engine = MaintenanceEngine()
    
    # Show storage summary
    print("Storage summary:", json.dumps(engine.get_storage_summary(), indent=2))
    
    # Test maintenance run
    result = engine.run_maintenance(35)
    print(f"\nMaintenance result: {json.dumps(result, indent=2)}")
