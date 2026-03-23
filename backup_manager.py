#!/usr/bin/env python3
"""Backup manager for Ecnyss - manages backup lifecycle and storage cleanup.

Prevents disk bloat from accumulated cycle backups and maintains 
storage health for long-running autonomous operation (cycle 33+).
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import shutil


class BackupManager:
    """Manages backup retention, cleanup, and storage health."""
    
    def __init__(self, base_path: str = "/root/Ecnyss", retention_cycles: int = 10):
        self.base_path = Path(base_path)
        self.backup_dir = self.base_path / ".ecnyss_backups"
        self.retention_cycles = retention_cycles
        self.stats = {
            "backups_removed": 0,
            "space_reclaimed_mb": 0,
            "last_cleanup": None
        }
    
    def cleanup_old_backups(self, current_cycle: int) -> Dict[str, Any]:
        """Remove backups older than retention policy."""
        if not self.backup_dir.exists():
            return {"status": "no_backups", "removed": 0}
        
        removed = []
        space_reclaimed = 0
        
        # Parse backup files: format is {path}.{cycle}.bak
        for backup_file in self.backup_dir.rglob("*.bak"):
            try:
                # Extract cycle number from filename
                cycle_str = backup_file.stem.split('.')[-1]
                backup_cycle = int(cycle_str)
                
                if current_cycle - backup_cycle > self.retention_cycles:
                    size = backup_file.stat().st_size
                    backup_file.unlink()
                    removed.append(str(backup_file.name))
                    space_reclaimed += size
                    
            except (ValueError, IndexError):
                continue
        
        # Remove empty directories
        self._remove_empty_dirs(self.backup_dir)
        
        self.stats["backups_removed"] += len(removed)
        self.stats["space_reclaimed_mb"] += space_reclaimed / (1024 * 1024)
        self.stats["last_cleanup"] = datetime.utcnow().isoformat()
        
        return {
            "status": "cleaned",
            "removed": len(removed),
            "files": removed,
            "space_reclaimed_mb": round(space_reclaimed / (1024 * 1024), 2)
        }
    
    def _remove_empty_dirs(self, path: Path):
        """Recursively remove empty directories."""
        for dir_path in path.rglob("*"):
            if dir_path.is_dir():
                try:
                    dir_path.rmdir()  # Only removes if empty
                except OSError:
                    pass
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get current backup storage statistics."""
        if not self.backup_dir.exists():
            return {"status": "no_backups", "total_size_mb": 0, "file_count": 0}
        
        total_size = 0
        file_count = 0
        oldest_backup = None
        newest_backup = None
        
        for file in self.backup_dir.rglob("*.bak"):
            stat = file.stat()
            total_size += stat.st_size
            file_count += 1
            
            mtime = datetime.fromtimestamp(stat.st_mtime)
            if oldest_backup is None or mtime < oldest_backup:
                oldest_backup = mtime
            if newest_backup is None or mtime > newest_backup:
                newest_backup = mtime
        
        return {
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "file_count": file_count,
            "oldest_backup": oldest_backup.isoformat() if oldest_backup else None,
            "newest_backup": newest_backup.isoformat() if newest_backup else None,
            "retention_policy": f"{self.retention_cycles} cycles"
        }
    
    def emergency_cleanup(self, max_size_mb: float = 100.0) -> Dict[str, Any]:
        """Aggressive cleanup if storage exceeds threshold."""
        stats = self.get_storage_stats()
        
        if stats["total_size_mb"] <= max_size_mb:
            return {"status": "within_limits", "action": "none"}
        
        # Remove oldest backups first until under limit
        backups = []
        for file in self.backup_dir.rglob("*.bak"):
            stat = file.stat()
            backups.append((file, stat.st_mtime, stat.st_size))
        
        # Sort by modification time (oldest first)
        backups.sort(key=lambda x: x[1])
        
        removed = []
        current_size = stats["total_size_mb"]
        
        for file, mtime, size in backups:
            if current_size <= max_size_mb * 0.8:  # Target 80% of limit
                break
            
            file.unlink()
            removed.append(str(file.name))
            current_size -= size / (1024 * 1024)
        
        return {
            "status": "emergency_cleaned",
            "removed": len(removed),
            "space_reclaimed_mb": round(stats["total_size_mb"] - current_size, 2),
            "files": removed
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cleanup statistics."""
        return self.stats.copy()


if __name__ == "__main__":
    manager = BackupManager()
    
    # Show current stats
    print("Storage stats:", manager.get_storage_stats())
    
    # Test cleanup
    result = manager.cleanup_old_backups(33)
    print(f"Cleanup result: {result}")
    print(f"Manager stats: {manager.get_stats()}")
