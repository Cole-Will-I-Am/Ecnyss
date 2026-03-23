#!/usr/bin/env python3
"""Robust self-reader for Ecnyss evolution log and source files.

Handles malformed entries in evolution.jsonl that caused cycles 5-8 failures.
"""
import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

class EcnyssReader:
    def __init__(self, base_path: str = "/root/Ecnyss"):
        self.base_path = Path(base_path)
        self.evolution_path = self.base_path / "evolution.jsonl"
    
    def read_evolution_log(self) -> List[Dict[str, Any]]:
        """Read evolution.jsonl, skipping malformed entries."""
        entries = []
        if not self.evolution_path.exists():
            return entries
        
        with open(self.evolution_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    entries.append(entry)
                except json.JSONDecodeError:
                    # Skip malformed lines (like 'Learned patterns' sections)
                    continue
        return entries
    
    def get_last_successful_cycle(self) -> Optional[int]:
        """Find the last cycle that succeeded."""
        entries = self.read_evolution_log()
        for entry in reversed(entries):
            if entry.get('status') == 'ok' or 'cycle' in entry:
                return entry.get('cycle')
        return None
    
    def read_source_file(self, relative_path: str) -> Optional[str]:
        """Read a source file from the base path."""
        file_path = self.base_path / relative_path
        try:
            with open(file_path, 'r') as f:
                return f.read()
        except FileNotFoundError:
            return None
    
    def list_python_files(self) -> List[str]:
        """List all Python files in the base path."""
        return [str(p.relative_to(self.base_path)) 
                for p in self.base_path.rglob("*.py")]

if __name__ == "__main__":
    reader = EcnyssReader()
    print(f"Python files: {reader.list_python_files()}")
    print(f"Last successful cycle: {reader.get_last_successful_cycle()}")
    print(f"Total log entries: {len(reader.read_evolution_log())}")
