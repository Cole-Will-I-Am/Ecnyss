#!/usr/bin/env python3
"""Dependency analyzer for Ecnyss - maps inter-module dependencies and architecture.

Analyzes import relationships between Python files to build a dependency graph,
detect circular dependencies, identify core infrastructure files, and find
orphaned modules. Enables safe refactoring and architectural understanding
for autonomous evolution (cycle 31+).
"""
import ast
import json
from pathlib import Path
from typing import Dict, List, Set, Any, Optional, Tuple
from collections import defaultdict, deque
from datetime import datetime


class DependencyAnalyzer:
    """Analyzes Python module dependencies within the Ecnyss codebase."""
    
    def __init__(self, base_path: str = "/root/Ecnyss"):
        self.base_path = Path(base_path)
        self.dependencies: Dict[str, Set[str]] = defaultdict(set)
        self.dependents: Dict[str, Set[str]] = defaultdict(set)
        self.external_deps: Dict[str, Set[str]] = defaultdict(set)
    
    def analyze_file(self, file_path: Path) -> Tuple[Set[str], Set[str]]:
        """Extract local and external imports from a Python file.
        
        Returns:
            Tuple of (local_imports, external_imports)
        """
        local_imports = set()
        external_imports = set()
        
        try:
            content = file_path.read_text()
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module = alias.name.split('.')[0]
                        if self._is_local_module(module):
                            local_imports.add(module)
                        else:
                            external_imports.add(module)
                            
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        module = node.module.split('.')[0]
                        if self._is_local_module(module):
                            local_imports.add(module)
                        else:
                            external_imports.add(module)
        except SyntaxError:
            pass
        except Exception:
            pass
            
        return local_imports, external_imports
    
    def _is_local_module(self, module: str) -> bool:
        """Check if a module name refers to a local Ecnyss file."""
        # Check if module.py exists in base_path
        if (self.base_path / f"{module}.py").exists():
            return True
        # Check if module/__init__.py exists
        if (self.base_path / module / "__init__.py").exists():
            return True
        return False
    
    def analyze_all(self) -> Dict[str, Any]:
        """Analyze all Python files and build dependency graph."""
        py_files = list(self.base_path.glob("*.py"))
        
        for file_path in py_files:
            rel_path = file_path.name
            local_imp, external_imp = self.analyze_file(file_path)
            
            self.dependencies[rel_path] = local_imp
            self.external_deps[rel_path] = external_imp
            
            # Build reverse mapping (who depends on this file)
            for dep in local_imp:
                dep_file = f"{dep}.py"
                if (self.base_path / dep_file).exists():
                    self.dependents[dep_file].add(rel_path)
        
        return self._build_report()
    
    def _build_report(self) -> Dict[str, Any]:
        """Generate comprehensive dependency report."""
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "total_files": len(self.dependencies),
            "dependencies": {k: sorted(list(v)) for k, v in self.dependencies.items()},
            "dependents": {k: sorted(list(v)) for k, v in self.dependents.items()},
            "external_dependencies": {k: sorted(list(v)) for k, v in self.external_deps.items()},
            "circular_dependencies": self._find_circular_dependencies(),
            "orphaned_files": self._find_orphaned_files(),
            "core_infrastructure": self._identify_core_files(),
            "leaf_modules": self._identify_leaf_modules(),
            "complexity_score": self._calculate_complexity()
        }
        return report
    
    def _find_circular_dependencies(self) -> List[List[str]]:
        """Detect circular import chains using DFS."""
        cycles = []
        visited = set()
        rec_stack = set()
        path = []
        
        def dfs(node: str):
            if node in rec_stack:
                # Found cycle - extract it from current path
                cycle_start = next((i for i, x in enumerate(path) if x == node), None)
                if cycle_start is not None:
                    cycle = path[cycle_start:] + [node]
                    cycles.append(cycle)
                return
            
            if node in visited:
                return
            
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for dep in self.dependencies.get(node, []):
                dep_file = f"{dep}.py"
                if (self.base_path / dep_file).exists():
                    dfs(dep_file)
            
            path.pop()
            rec_stack.remove(node)
        
        for file in self.dependencies:
            if file not in visited:
                dfs(file)
        
        # Remove duplicate cycles (same cycle starting at different points)
        unique_cycles = []
        seen = set()
        for cycle in cycles:
            normalized = tuple(sorted(cycle))
            if normalized not in seen:
                seen.add(normalized)
                unique_cycles.append(cycle)
        
        return unique_cycles
    
    def _find_orphaned_files(self) -> List[str]:
        """Find files with no dependencies and no dependents."""
        orphans = []
        for file in self.dependencies:
            has_deps = len(self.dependencies[file]) > 0
            has_dependents = len(self.dependents.get(file, [])) > 0
            if not has_deps and not_dependents:
                orphans.append(file)
        return sorted(orphans)
    
    def _identify_core_files(self) -> List[Dict[str, Any]]:
        """Identify most critical files (most depended upon)."""
        core = []
        for file, deps in self.dependents.items():
            core.append({
                "file": file,
                "dependent_count": len(deps),
                "dependents": sorted(list(deps))
            })
        
        core.sort(key=lambda x: x["dependent_count"], reverse=True)
        return core[:5]  # Top 5 most critical
    
    def _identify_leaf_modules(self) -> List[str]:
        """Identify leaf modules (no dependencies on other local modules)."""
        leaves = []
        for file, deps in self.dependencies.items():
            if not deps:
                leaves.append(file)
        return sorted(leaves)
    
    def _calculate_complexity(self) -> Dict[str, float]:
        """Calculate architectural complexity metrics."""
        total_files = len(self.dependencies)
        if total_files == 0:
            return {"average_dependencies": 0, "average_dependents": 0, "density": 0}
        
        total_deps = sum(len(deps) for deps in self.dependencies.values())
        total_dependents = sum(len(deps) for deps in self.dependents.values())
        
        # Graph density: actual edges / possible edges
        possible_edges = total_files * (total_files - 1)
        density = total_deps / possible_edges if possible_edges > 0 else 0
        
        return {
            "average_dependencies": total_deps / total_files,
            "average_dependents": total_dependents / total_files,
            "density": density,
            "total_edges": total_deps
        }
    
    def get_refactoring_order(self, target_file: str) -> List[str]:
        """Determine safe refactoring order (reverse dependency order)."""
        # Topological sort - refactor leaves first, core files last
        order = []
        visited = set()
        
        def visit(file: str):
            if file in visited:
                return
            visited.add(file)
            
            # Visit all dependencies first
            for dep in self.dependencies.get(file, []):
                dep_file = f"{dep}.py"
                if (self.base_path / dep_file).exists():
                    visit(dep_file)
            
            order.append(file)
        
        visit(target_file)
        return order
    
    def find_impact(self, file: str) -> Set[str]:
        """Find all files that would be affected by changing a given file."""
        impacted = set()
        queue = deque([file])
        
        while queue:
            current = queue.popleft()
            for dependent in self.dependents.get(current, []):
                if dependent not in impacted:
                    impacted.add(dependent)
                    queue.append(dependent)
        
        return impacted
    
    def save_report(self, report: Dict[str, Any], cycle: int):
        """Save dependency report to evolution log."""
        entry = {
            "status": "ok",
            "action": "analyze",
            "summary": f"Dependency analysis for {report['total_files']} files",
            "files": list(self.dependencies.keys()),
            "cycle": cycle,
            "timestamp": datetime.utcnow().isoformat(),
            "model": "dependency_analyzer",
            "metrics": report["complexity_score"],
            "circular_deps_found": len(report["circular_dependencies"]),
            "orphaned_files": report["orphaned_files"]
        }
        
        with open(self.base_path / "evolution.jsonl", 'a') as f:
            f.write(json.dumps(entry) + '\n')


if __name__ == "__main__":
    analyzer = DependencyAnalyzer()
    report = analyzer.analyze_all()
    
    print(json.dumps(report, indent=2))
    
    print(f"\n=== Summary ===")
    print(f"Total files analyzed: {report['total_files']}")
    print(f"Circular dependencies: {len(report['circular_dependencies'])}")
    print(f"Orphaned files: {report['orphaned_files']}")
    print(f"\nCore infrastructure (most depended upon):")
    for core in report['core_infrastructure']:
        print(f"  {core['file']}: {core['dependent_count']} dependents")
    
    if report['circular_dependencies']:
        print(f"\nWARNING: Circular dependencies detected:")
        for cycle in report['circular_dependencies']:
            print(f"  {' -> '.join(cycle)}")
    
    if report['orphaned_files']:
        print(f"\nNOTE: Orphaned files (no deps, no dependents):")
        for orphan in report['orphaned_files']:
            print(f"  - {orphan}")