#!/usr/bin/env python3
"""Git integration helper for Ecnyss autonomous commits."""
import subprocess
from pathlib import Path
from typing import List, Optional


class GitIntegrator:
    """Lightweight git operations scoped to the Ecnyss repo."""

    def __init__(self, repo_path: str = "/root/Ecnyss"):
        self.repo = Path(repo_path)

    def _run(self, args: List[str], timeout: int = 30) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", "-C", str(self.repo), *args],
            capture_output=True, text=True, timeout=timeout,
        )

    def has_changes(self) -> bool:
        r = self._run(["status", "--porcelain"])
        return bool(r.stdout.strip())

    def stage_files(self, paths: List[str]) -> None:
        for p in paths:
            self._run(["add", "--", p])

    def commit(self, message: str) -> bool:
        r = self._run(["commit", "-m", message])
        return r.returncode == 0

    def push(self, remote: str = "origin", branch: Optional[str] = None) -> bool:
        if branch is None:
            r = self._run(["rev-parse", "--abbrev-ref", "HEAD"])
            branch = r.stdout.strip() or "main"
        r = self._run(["push", remote, branch], timeout=60)
        return r.returncode == 0

    def log(self, n: int = 5) -> str:
        r = self._run(["log", "--oneline", f"-{n}"])
        return r.stdout.strip()


if __name__ == "__main__":
    gi = GitIntegrator()
    print("Has changes:", gi.has_changes())
    print("Recent commits:")
    print(gi.log())
