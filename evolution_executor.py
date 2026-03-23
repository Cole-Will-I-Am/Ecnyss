#!/usr/bin/env python3
"""Evolution executor for Ecnyss - executes validated evolution plans.

Performs actual file operations based on decision engine outputs.
Completes the self-modification loop for autonomous operation (cycles 16+).
"""
import json
import os
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

# Import existing infrastructure
from output_validator import OutputValidator
from state_tracker import StateTracker

class EvolutionExecutor:
    """Executes evolution plans safely with validation and rollback."""
    
    def __init__(self, base_path: str = "/root/Ecnyss"):
        self.base_path = Path(base_path)
        self.validator = OutputValidator()
        self.tracker = StateTracker(base_path)
        self.backup_dir = self.base_path / ".ecnyss_backups"
        self.backup_dir.mkdir(exist_ok=True)
    
    def execute_plan(self, plan: Dict[str, Any], cycle: int) -> Tuple[bool, List[str]]:
        """Execute an evolution plan with full validation and rollback on failure."""
        # Validate plan structure first
        valid, errors = self.validator.validate_plan_structure(plan)
        if not valid:
            return False, [f"Validation failed: {e}" for e in errors]
        
        executed_files = []
        backup_paths = {}
        
        try:
            action = plan.get('action')
            files = plan.get('files', [])
            
            for file_entry in files:
                path = file_entry.get('path')
                content = file_entry.get('content')
                
                if not path:
                    continue
                
                full_path = self.base_path / path
                
                # Backup existing file if modifying
                if action in ['modify', 'refactor'] and full_path.exists():
                    backup_path = self.backup_dir / f"{path}.{cycle}.bak"
                    backup_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(full_path, backup_path)
                    backup_paths[path] = backup_path
                
                # Execute based on action
                if action == 'create':
                    if full_path.exists():
                        return False, [f"File already exists: {path}"]
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    full_path.write_text(content)
                    executed_files.append(path)
                    
                elif action == 'modify' or action == 'refactor':
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    full_path.write_text(content)
                    executed_files.append(path)
                    
                elif action == 'delete':
                    if full_path.exists():
                        backup_path = self.backup_dir / f"{path}.{cycle}.bak"
                        shutil.copy2(full_path, backup_path)
                        backup_paths[path] = backup_path
                        full_path.unlink()
                        executed_files.append(path)
            
            # Record successful execution
            for filepath in executed_files:
                self.tracker.record_file_creation(filepath, cycle)
            
            # Log execution to evolution
            self._log_execution(plan, cycle, True, None)
            
            return True, executed_files
            
        except Exception as e:
            # Rollback on failure
            self._rollback(backup_paths)
            self._log_execution(plan, cycle, False, str(e))
            return False, [f"Execution failed: {str(e)}"]
    
    def _rollback(self, backup_paths: Dict[str, Path]):
        """Restore files from backups on failure."""
        for path, backup in backup_paths.items():
            full_path = self.base_path / path
            if backup.exists():
                full_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup, full_path)
    
    def _log_execution(self, plan: Dict, cycle: int, success: bool, error: Optional[str]):
        """Log execution result to evolution.jsonl."""
        entry = {
            "status": "ok" if success else "failed",
            "action": plan.get('action'),
            "files": [f.get('path') for f in plan.get('files', [])],
            "cycle": cycle,
            "timestamp": datetime.utcnow().isoformat(),
            "model": "evolution_executor",
            "error": error
        }
        
        with open(self.base_path / "evolution.jsonl", 'a') as f:
            f.write(json.dumps(entry) + '\n')
    
    def get_execution_history(self, limit: int = 10) -> List[Dict]:
        """Get recent execution history from evolution log."""
        from self_reader import EcnyssReader
        reader = EcnyssReader(self.base_path)
        entries = reader.read_evolution_log()
        return [e for e in entries if e.get('model') == 'evolution_executor'][-limit:]

if __name__ == "__main__":
    executor = EvolutionExecutor()
    
    # Test with a sample plan
    test_plan = {
        "action": "create",
        "files": [{"path": "test_output.txt", "content": "# Test file created by executor\n"}],
        "summary": "Test execution",
        "reasoning": "Testing the executor before cycle 16 autonomous operation"
    }
    
    success, result = executor.execute_plan(test_plan, 15)
    print(f"Execution success: {success}")
    print(f"Result: {result}")