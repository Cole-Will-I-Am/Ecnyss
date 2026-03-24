#!/usr/bin/env python3
"""State tracker for Ecnyss - tracks system state across cycles.

Provides persistent state storage for mid-cycle memory requirements.
"""
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

class StateTracker:
    def __init__(self, base_path: str = "/root/Ecnyss"):
        self.base_path = Path(base_path)
        self.state_file = self.base_path / ".ecnyss_state.json"
        self._state = self._load_state()
    
    def _load_state(self) -> Dict[str, Any]:
        """Load state from disk or initialize."""
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                return json.load(f)
        return {
            "initialized": True,
            "first_cycle": 10,
            "files_created": [],
            "patterns_learned": {}
        }

    def load_state(self) -> Dict[str, Any]:
        """Compatibility wrapper used by older runners."""
        return dict(self._state)
    
    def save_state(self):
        """Persist state to disk."""
        with open(self.state_file, 'w') as f:
            json.dump(self._state, f, indent=2)
    
    def get_git_status(self) -> Dict[str, Any]:
        """Get current git status."""
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.base_path,
                capture_output=True,
                text=True
            )
            return {
                "clean": result.returncode == 0 and not result.stdout.strip(),
                "output": result.stdout if result.stdout else None
            }
        except Exception as e:
            return {"clean": False, "error": str(e)}
    
    def get_current_cycle(self) -> int:
        """Determine current cycle from git log or state."""
        try:
            result = subprocess.run(
                ["git", "log", "--oneline"],
                cwd=self.base_path,
                capture_output=True,
                text=True
            )
            lines = [l for l in result.stdout.split('\n') if l.strip()]
            # Look for cycle markers in commit messages
            for line in lines:
                if 'cycle #' in line.lower():
                    import re
                    match = re.search(r'cycle #(\d+)', line.lower())
                    if match:
                        return int(match.group(1))
            return len(lines)  # Fallback to commit count
        except Exception:
            return self._state.get("last_known_cycle", 0)
    
    def record_file_creation(self, filename: str, cycle: int):
        """Record that a file was created in a cycle."""
        self._state.setdefault("files_created", []).append({
            "file": filename,
            "cycle": cycle,
            "timestamp": datetime.utcnow().isoformat()
        })
        self.save_state()
    
    def get_system_summary(self) -> Dict[str, Any]:
        """Get complete system state summary."""
        return {
            "current_cycle": self.get_current_cycle(),
            "base_path": str(self.base_path),
            "files_tracked": self._state.get("files_created", []),
            "git_status": self.get_git_status(),
            "timestamp": datetime.utcnow().isoformat()
        }

    def capture_state(self, context_files: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Compatibility wrapper used by older runners."""
        summary = self.get_system_summary()
        summary["context_files"] = context_files or []
        return summary

if __name__ == "__main__":
    tracker = StateTracker()
    summary = tracker.get_system_summary()
    print(json.dumps(summary, indent=2))
