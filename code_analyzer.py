#!/usr/bin/env python3
"""Code analyzer for Ecnyss - static analysis and complexity metrics.

Integrates with self_reader and state_tracker to provide codebase intelligence
for mid-cycle self-tuning requirements. Outputs data compatible with
/opt/minimax/bin/improver.py format.
"""
import ast
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from self_reader import EcnyssReader
from state_tracker import StateTracker


class ComplexityAnalyzer(ast.NodeVisitor):
    """Calculate cyclomatic complexity using AST traversal."""
    
    def __init__(self):
        self.complexity = 1
        self.functions = []
        self.classes = []
        self.imports = []
    
    def visit_FunctionDef(self, node):
        func_complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.And, ast.Or)):
                func_complexity += 1
            elif isinstance(child, ast.For):
                func_complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                func_complexity += 1
        self.functions.append({
            "name": node.name,
            "complexity": func_complexity,
            "lineno": node.lineno
        })
        self.generic_visit(node)
    
    def visit_ClassDef(self, node):
        self.classes.append({
            "name": node.name,
            "methods": len([n for n in node.body if isinstance(n, ast.FunctionDef)]),
            "lineno": node.lineno
        })
        self.generic_visit(node)
    
    def visit_Import(self, node):
        for alias in node.names:
            self.imports.append(alias.name)
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node):
        if node.module:
            self.imports.append(node.module)
        self.generic_visit(node)


class CodeAnalyzer:
    """Analyzes Python codebase structure and extracts metrics for self-tuning."""
    
    def __init__(self, base_path: str = "/root/Ecnyss"):
        self.reader = EcnyssReader(base_path)
        self.tracker = StateTracker(base_path)
        self.base_path = Path(base_path)
    
    def analyze_file(self, filepath: str) -> Dict[str, Any]:
        """Perform deep analysis of a single Python file."""
        content = self.reader.read_source_file(filepath)
        if not content:
            return {"path": filepath, "error": "File not found or unreadable"}
        
        lines = content.split('\n')
        total_lines = len(lines)
        loc = len([l for l in lines if l.strip()])
        sloc = len([l for l in lines if l.strip() and not l.strip().startswith('#')])
        comments = len([l for l in lines if l.strip().startswith('#')])
        
        result = {
            "path": filepath,
            "metrics": {
                "total_lines": total_lines,
                "loc": loc,
                "sloc": sloc,
                "comments": comments,
                "comment_ratio": comments / loc if loc > 0 else 0
            },
            "structure": {
                "functions": [],
                "classes": [],
                "imports": []
            },
            "complexity": {
                "total": 0,
                "average": 0,
                "max": 0
            }
        }
        
        try:
            tree = ast.parse(content)
            analyzer = ComplexityAnalyzer()
            analyzer.visit(tree)
            
            result["structure"]["functions"] = analyzer.functions
            result["structure"]["classes"] = analyzer.classes
            result["structure"]["imports"] = analyzer.imports
            
            if analyzer.functions:
                complexities = [f["complexity"] for f in analyzer.functions]
                result["complexity"]["total"] = sum(complexities)
                result["complexity"]["average"] = sum(complexities) / len(complexities)
                result["complexity"]["max"] = max(complexities)
            
        except SyntaxError as e:
            result["syntax_error"] = str(e)
            result["syntax_line"] = e.lineno
        
        return result
    
    def analyze_all(self) -> Dict[str, Any]:
        """Analyze entire codebase and generate aggregate metrics."""
        files = self.reader.list_python_files()
        file_analyses = []
        
        totals = {
            "files": 0,
            "loc": 0,
            "sloc": 0,
            "functions": 0,
            "classes": 0,
            "imports": 0,
            "total_complexity": 0,
            "max_complexity": 0
        }
        
        for filepath in files:
            analysis = self.analyze_file(filepath)
            file_analyses.append(analysis)
            
            if "error" not in analysis:
                totals["files"] += 1
                totals["loc"] += analysis["metrics"]["loc"]
                totals["sloc"] += analysis["metrics"]["sloc"]
                totals["functions"] += len(analysis["structure"]["functions"])
                totals["classes"] += len(analysis["structure"]["classes"])
                totals["imports"] += len(analysis["structure"]["imports"])
                totals["total_complexity"] += analysis["complexity"]["total"]
                totals["max_complexity"] = max(
                    totals["max_complexity"],
                    analysis["complexity"]["max"]
                )
        
        return {
            "timestamp": self.tracker.get_system_summary()["timestamp"],
            "cycle": self.tracker.get_current_cycle(),
            "summary": totals,
            "averages": {
                "loc_per_file": totals["loc"] / totals["files"] if totals["files"] > 0 else 0,
                "complexity_per_function": totals["total_complexity"] / totals["functions"] if totals["functions"] > 0 else 0
            },
            "files": file_analyses
        }
    
    def store_analysis(self) -> Dict[str, Any]:
        """Persist analysis results to state tracker for cross-cycle memory."""
        analysis = self.analyze_all()
        self.tracker._state["code_analysis"] = analysis
        self.tracker._state["analysis_history"] = self.tracker._state.get("analysis_history", [])
        self.tracker._state["analysis_history"].append({
            "cycle": analysis["cycle"],
            "timestamp": analysis["timestamp"],
            "loc": analysis["summary"]["loc"],
            "files": analysis["summary"]["files"]
        })
        self.tracker.save_state()
        return analysis
    
    def generate_improver_input(self) -> Dict[str, Any]:
        """Generate tuning data for /opt/minimax/bin/improver.py integration."""
        analysis = self.analyze_all()
        summary = analysis["summary"]
        
        recommendations = []
        
        if summary["files"] > 0:
            avg_complexity = summary["total_complexity"] / summary["functions"] if summary["functions"] > 0 else 0
            
            if avg_complexity > 10:
                recommendations.append("high_complexity: Refactor functions with complexity > 10")
            if summary["max_complexity"] > 15:
                recommendations.append("complex_hotspot: Simplify most complex function")
            if summary["loc"] / summary["files"] > 200:
                recommendations.append("large_files: Split files exceeding 200 LOC")
            if summary["functions"] == 0 and summary["files"] > 2:
                recommendations.append("no_functions: Add function definitions for modularity")
            if summary["classes"] == 0 and summary["files"] > 3:
                recommendations.append("no_classes: Consider OOP structure for organization")
        
        return {
            "system": "Ecnyss",
            "cycle": analysis["cycle"],
            "metrics": {
                "files": summary["files"],
                "loc": summary["loc"],
                "sloc": summary["sloc"],
                "functions": summary["functions"],
                "classes": summary["classes"],
                "avg_complexity": summary["total_complexity"] / summary["functions"] if summary["functions"] > 0 else 0,
                "max_complexity": summary["max_complexity"]
            },
            "tuning_recommendations": recommendations,
            "target": "/opt/minimax/bin/improver.py"
        }
    
    def detect_patterns(self) -> List[Dict[str, Any]]:
        """Detect architectural patterns in existing code."""
        analysis = self.analyze_all()
        patterns = []
        
        files_with_classes = sum(1 for f in analysis["files"] if f["structure"]["classes"])
        files_with_functions = sum(1 for f in analysis["files"] if f["structure"]["functions"])
        
        if files_with_classes > 0:
            patterns.append({"type": "oop", "strength": files_with_classes / len(analysis["files"])})
        if files_with_functions > files_with_classes:
            patterns.append({"type": "functional", "strength": files_with_functions / len(analysis["files"])})
        
        import_counts = {}
        for f in analysis["files"]:
            for imp in f["structure"]["imports"]:
                import_counts[imp] = import_counts.get(imp, 0) + 1
        
        common_imports = {k: v for k, v in import_counts.items() if v > 1}
        if common_imports:
            patterns.append({"type": "dependency_cluster", "modules": list(common_imports.keys())})
        
        return patterns


if __name__ == "__main__":
    analyzer = CodeAnalyzer()
    
    print("=" * 50)
    print("ECNYSS CODE ANALYZER")
    print("=" * 50)
    
    analysis = analyzer.store_analysis()
    
    print(f"\nAnalyzed {analysis['summary']['files']} files")
    print(f"Total LOC: {analysis['summary']['loc']}")
    print(f"Total Functions: {analysis['summary']['functions']}")
    print(f"Total Classes: {analysis['summary']['classes']}")
    
    if analysis['summary']['functions'] > 0:
        avg_comp = analysis['summary']['total_complexity'] / analysis['summary']['functions']
        print(f"Average Complexity: {avg_comp:.2f}")
        print(f"Max Complexity: {analysis['summary']['max_complexity']}")
    
    print("\n" + "=" * 50)
    print("IMPROVER INPUT")
    print("=" * 50)
    
    improver_data = analyzer.generate_improver_input()
    print(json.dumps(improver_data, indent=2))
    
    patterns = analyzer.detect_patterns()
    if patterns:
        print("\n" + "=" * 50)
        print("DETECTED PATTERNS")
        print("=" * 50)
        for p in patterns:
            print(f"  - {p['type']}: {p}")