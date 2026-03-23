#!/usr/bin/env python3
"""Context manager for Ecnyss - optimizes LLM context window usage.

Intelligently selects relevant files and history to prevent context overflow
as the system scales (cycle 44+). Ensures high-value information is
prioritized while staying within token limits.
"""
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime, timedelta
from collections import defaultdict

from dependency_analyzer import DependencyAnalyzer
from self_reader import EcnyssReader


class ContextManager:
    """Manages context window optimization for autonomous evolution."""
    
    def __init__(self, base_path: str = "/root/Ecnyss", max_files: int = 15, 
                 max_history_cycles: int = 10, max_tokens_estimate: int = 8000):
        self.base_path = Path(base_path)
        self.max_files = max_files
        self.max_history_cycles = max_history_cycles
        self.max_tokens = max_tokens_estimate
        self.reader = EcnyssReader(base_path)
        self.dependency_analyzer = DependencyAnalyzer(base_path)
        self._file_scores: Dict[str, float] = {}
        self._dependency_graph: Dict[str, Set[str]] = {}
    
    def build_dependency_graph(self) -> Dict[str, Set[str]]:
        """Build a graph of file dependencies for relevance scoring."""
        analysis = self.dependency_analyzer.analyze_all_files()
        graph = defaultdict(set)
        
        # Add import relationships
        for path, deps in analysis.get('dependencies', {}).items():
            for dep in deps.get('imports', []):
                # Map import to likely file path
                dep_path = dep.replace('.', '/') + '.py'
                if (self.base_path / dep_path).exists():
                    graph[path].add(dep_path)
                    graph[dep_path].add(path)  # Bidirectional
        
        self._dependency_graph = dict(graph)
        return self._dependency_graph
    
    def score_file_relevance(self, target_files: List[str], 
                            current_cycle: int) -> Dict[str, float]:
        """Score all files by relevance to target files and recent activity."""
        scores = defaultdict(float)
        
        # Build dependency graph if needed
        if not self._dependency_graph:
            self.build_dependency_graph()
        
        # Read evolution history for recent changes
        history = self.reader.read_evolution_log()
        recent_cycles = [e for e in history 
                        if current_cycle - e.get('cycle', 0) <= self.max_history_cycles]
        
        # Score based on recent modifications
        for entry in recent_cycles:
            cycle_num = entry.get('cycle', 0)
            age_factor = 1.0 - (current_cycle - cycle_num) / self.max_history_cycles
            
            for file in entry.get('files', []):
                scores[file] += 10.0 * age_factor
                
                # Boost score for files that depend on or are depended upon
                if file in self._dependency_graph:
                    for related in self._dependency_graph[file]:
                        scores[related] += 5.0 * age_factor
        
        # Boost target files specifically
        for target in target_files:
            scores[target] += 100.0
            # Boost neighbors in dependency graph
            if target in self._dependency_graph:
                for neighbor in self._dependency_graph[target]:
                    scores[neighbor] += 20.0
        
        # Boost core infrastructure files
        core_files = ['main.py', 'autonomous_orchestrator.py', 'decision_engine.py',
                     'evolution_executor.py', 'evolution_analyzer.py']
        for core in core_files:
            scores[core] += 15.0
        
        self._file_scores = dict(scores)
        return self._file_scores
    
    def select_relevant_files(self, target_files: List[str], 
                             current_cycle: int) -> List[Dict[str, Any]]:
        """Select the most relevant files for the current context."""
        scores = self.score_file_relevance(target_files, current_cycle)
        
        # Get all Python files
        all_files = list(self.base_path.rglob("*.py"))
        all_files = [f for f in all_files if '.ecnyss_backups' not in str(f)]
        
        # Score and sort
        scored_files = []
        for file_path in all_files:
            rel_path = str(file_path.relative_to(self.base_path))
            score = scores.get(rel_path, 0)
            
            # Add size penalty (prefer smaller files for context efficiency)
            try:
                size = file_path.stat().st_size
                size_penalty = size / 10000  # Penalty per 10KB
                score -= size_penalty
            except OSError:
                pass
            
            scored_files.append((rel_path, score, file_path))
        
        # Sort by score descending
        scored_files.sort(key=lambda x: x[1], reverse=True)
        
        # Take top N
        selected = []
        for rel_path, score, full_path in scored_files[:self.max_files]:
            try:
                content = full_path.read_text()
                selected.append({
                    'path': rel_path,
                    'content': content,
                    'relevance_score': round(score, 2),
                    'size_bytes': full_path.stat().st_size
                })
            except Exception:
                continue
        
        return selected
    
    def summarize_history(self, current_cycle: int, 
                          focus_patterns: List[str] = None) -> List[Dict[str, Any]]:
        """Summarize evolution history, focusing on relevant patterns."""
        history = self.reader.read_evolution_log()
        
        # Filter to recent cycles
        recent = [e for e in history 
                 if current_cycle - e.get('cycle', 0) <= self.max_history_cycles * 2]
        
        # Group by action type
        by_action = defaultdict(list)
        for entry in recent:
            action = entry.get('action', 'unknown')
            by_action[action].append(entry)
        
        # Extract patterns
        summary = []
        
        # Recent failures (always include)
        failures = [e for e in recent if e.get('status') != 'ok']
        for f in failures[-3:]:  # Last 3 failures
            summary.append({
                'type': 'recent_failure',
                'cycle': f.get('cycle'),
                'action': f.get('action'),
                'files': f.get('files', []),
                'error': f.get('error', 'unknown'),
                'priority': 'high'
            })
        
        # Recent successes of same action type
        if focus_patterns:
            for pattern in focus_patterns:
                matches = [e for e in recent 
                        if e.get('action') == pattern and e.get('status') == 'ok']
                if matches:
                    latest = matches[-1]
                    summary.append({
                        'type': 'pattern_precedent',
                        'pattern': pattern,
                        'cycle': latest.get('cycle'),
                        'files': latest.get('files', []),
                        'summary': latest.get('summary', '')[:100],
                        'priority': 'medium'
                    })
        
        # Trend analysis
        success_rate = len([e for e in recent if e.get('status') == 'ok']) / len(recent) if recent else 0
        summary.append({
            'type': 'trend',
            'recent_cycles': len(recent),
            'success_rate': round(success_rate, 2),
            'failure_count': len(failures),
            'priority': 'low'
        })
        
        return summary
    
    def get_optimized_context(self, current_cycle: int, 
                             target_files: List[str] = None,
                             task_type: str = "evolution") -> Dict[str, Any]:
        """Get fully optimized context for the current cycle."""
        target_files = target_files or []
        
        # Select relevant files
        relevant_files = self.select_relevant_files(target_files, current_cycle)
        
        # Summarize history based on task type
        focus_patterns = []
        if task_type == "create":
            focus_patterns = ["create", "modify"]
        elif task_type == "integrate":
            focus_patterns = ["modify", "refactor"]
        elif task_type == "fix":
            focus_patterns = ["modify", "create"]
        
        history_summary = self.summarize_history(current_cycle, focus_patterns)
        
        # Calculate token estimate (rough: 4 chars per token)
        total_chars = sum(len(f['content']) for f in relevant_files)
        total_chars += sum(len(str(h)) for h in history_summary) * 10
        estimated_tokens = total_chars // 4
        
        return {
            'files': relevant_files,
            'file_count': len(relevant_files),
            'history_summary': history_summary,
            'history_entries': len(history_summary),
            'estimated_tokens': estimated_tokens,
            'token_budget': self.max_tokens,
            'utilization': round(estimated_tokens / self.max_tokens * 100, 1),
            'cycle': current_cycle,
            'task_type': task_type
        }
    
    def get_critical_context_only(self, current_cycle: int) -> Dict[str, Any]:
        """Get minimal critical context for emergency/recovery situations."""
        # Only most essential files
        critical_files = [
            'main.py', 'autonomous_orchestrator.py', 'decision_engine.py',
            'evolution_executor.py', 'health_monitor.py', 'recovery_engine.py'
        ]
        
        files = []
        for cf in critical_files:
            path = self.base_path / cf
            if path.exists():
                try:
                    content = path.read_text()
                    files.append({
                        'path': cf,
                        'content': content[:5000],  # Truncate to first 5KB
                        'truncated': len(content) > 5000
                    })
                except Exception:
                    continue
        
        # Only last 3 history entries
        history = self.reader.read_evolution_log()
        recent = history[-3:] if len(history) > 3 else history
        
        return {
            'files': files,
            'history': recent,
            'mode': 'critical_only',
            'cycle': current_cycle
        }


if __name__ == "__main__":
    manager = ContextManager()
    
    # Test context optimization
    context = manager.get_optimized_context(
        current_cycle=44,
        target_files=["evolution_executor.py"],
        task_type="integrate"
    )
    
    print(f"Context optimization for cycle {context['cycle']}")
    print(f"Files selected: {context['file_count']}")
    print(f"Estimated tokens: {context['estimated_tokens']}/{context['token_budget']}")
    print(f"Utilization: {context['utilization']}%")
    print(f"\nSelected files:")
    for f in context['files'][:5]:
        print(f"  - {f['path']} (score: {f['relevance_score']})")
    print(f"\nHistory summary items: {context['history_entries']}")