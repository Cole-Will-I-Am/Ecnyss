#!/usr/bin/env python3
"""Evolution executor for Ecnyss - executes validated evolution plans.

Performs actual file operations based on decision engine outputs.
Completes the self-modification loop for autonomous operation (cycles 16+).
"""
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

# Import existing infrastructure
from output_validator import OutputValidator
from state_tracker import StateTracker
from semantic_validator import SemanticValidator

class EvolutionExecutor:
    """Executes evolution plans safely with validation and rollback."""
    
    def __init__(self, base_path: str = "/root/Ecnyss"):
        self.base_path = Path(base_path)
        self.validator = OutputValidator()
        self.semantic_validator = SemanticValidator()
        self.tracker = StateTracker(base_path)
        self.backup_dir = self.base_path / ".ecnyss_backups"
        self.backup_dir.mkdir(exist_ok=True)
    
    def execute_plan(self, plan: Dict[str, Any], cycle: int) -> Tuple[bool, List[str]]:
        """Execute an evolution plan with full validation and rollback on failure."""
        # Validate plan structure first
        valid, errors = self.validator.validate_plan_structure(plan)
        if not valid:
            return False, [f"Validation failed: {e}" for e in errors]
        
        # Validate semantic quality of file contents (cycle 43)
        files = plan.get('files', [])
        for file_entry in files:
            path = file_entry.get('path')
            content = file_entry.get('content')
            if content and path:
                sem_valid, sem_errors = self.semantic_validator.validate_content(content, path)
                if not sem_valid:
                    return False, [f"Semantic validation failed for {path}: {e}" for e in sem_errors]
        
        executed_files = []
        backup_paths = {}
        
        try:
            action = plan.get('action')
            
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

            # Commit + push successful code changes if git is available.
            git_result = self._git_record(cycle, plan, executed_files)

            # Log execution to evolution
            self._log_execution(plan, cycle, True, None, git_result)
            
            return True, executed_files
            
        except Exception as e:
            # Rollback on failure
            self._rollback(backup_paths)
            self._log_execution(plan, cycle, False, str(e), None)
            return False, [f"Execution failed: {str(e)}"]

    def _git_record(self, cycle: int, plan: Dict[str, Any], files_affected: List[str]) -> Dict[str, Any]:
        """Record successful changes in git and optionally push."""
        repo = self.base_path
        if not (repo / ".git").exists():
            return {"committed": False, "pushed": False, "reason": "no_git_repo"}

        if os.environ.get("ECNYSS_GIT_COMMIT", "1").lower() in {"0", "false", "no"}:
            return {"committed": False, "pushed": False, "reason": "commit_disabled"}

        def _run(args: List[str], timeout: int = 20) -> subprocess.CompletedProcess:
            return subprocess.run(
                ["git", "-C", str(repo), *args],
                capture_output=True,
                text=True,
                timeout=timeout
            )

        # Stage only files touched by this plan to avoid scooping unrelated edits.
        unique_files: List[str] = []
        for path in files_affected:
            if not path:
                continue
            rel_path = str(Path(path))
            if rel_path not in unique_files:
                unique_files.append(rel_path)
        if not unique_files:
            return {"committed": False, "pushed": False, "reason": "no_files_affected"}

        pre_staged = _run(["diff", "--cached", "--name-only"])
        if pre_staged.returncode == 0 and pre_staged.stdout.strip():
            return {"committed": False, "pushed": False, "reason": "preexisting_staged_changes"}

        add_errors: List[str] = []
        for rel_path in unique_files:
            add = _run(["add", "-A", "--", rel_path])
            if add.returncode != 0:
                add_errors.append(f"{rel_path}: {add.stderr.strip()[:120]}")

        diff = _run(["diff", "--cached", "--quiet"])
        if diff.returncode == 0:
            reason = "no_staged_changes"
            if add_errors:
                reason = f"git_add_warnings: {'; '.join(add_errors)[:180]}"
            return {"committed": False, "pushed": False, "reason": reason}

        summary_source = plan.get("summary") or plan.get("reasoning") or "autonomous update"
        summary = " ".join(str(summary_source).split())[:72]
        action = str(plan.get("action") or "update")
        message = f"ecnyss cycle {cycle}: {action} - {summary}"

        commit = _run(["commit", "-m", message], timeout=30)
        if commit.returncode != 0:
            return {
                "committed": False,
                "pushed": False,
                "reason": f"git_commit_failed: {commit.stderr.strip()[:180]}",
            }

        pushed = False
        push_reason = "push_disabled"
        if os.environ.get("ECNYSS_GIT_PUSH", "1").lower() not in {"0", "false", "no"}:
            branch = _run(["rev-parse", "--abbrev-ref", "HEAD"])
            if branch.returncode == 0:
                branch_name = branch.stdout.strip() or "main"
                remote_name = os.environ.get("ECNYSS_GIT_REMOTE", "origin")
                push = _run(["push", remote_name, branch_name], timeout=60)
                if push.returncode == 0:
                    pushed = True
                    push_reason = "ok"
                else:
                    push_reason = f"git_push_failed: {push.stderr.strip()[:180]}"
            else:
                push_reason = "branch_unknown"

        return {"committed": True, "pushed": pushed, "reason": push_reason}

    def execute(self, decision: Dict[str, Any], _context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Compatibility wrapper used by older runners."""
        cycle = int(decision.get("cycle") or (self.tracker.get_current_cycle() + 1))
        success, result = self.execute_plan(decision, cycle)
        return {
            "success": success,
            "files_modified": len(result) if success else 0,
            "files": result if success else [],
            "error": None if success else "; ".join(result),
        }
    
    def _rollback(self, backup_paths: Dict[str, Path]):
        """Restore files from backups on failure."""
        for path, backup in backup_paths.items():
            full_path = self.base_path / path
            if backup.exists():
                full_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup, full_path)
    
    def _log_execution(
        self,
        plan: Dict,
        cycle: int,
        success: bool,
        error: Optional[str],
        git_result: Optional[Dict[str, Any]] = None
    ):
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
        if git_result is not None:
            entry["git"] = git_result
        
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
