#!/usr/bin/env python3
"""Cycle optimizer for Ecnyss - analyzes evolution patterns to generate self-tuning recommendations.

Implements mid-cycle self-tuning requirement by correlating evolution outcomes
with code metrics to suggest improvements for future cycles.
"""
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# Import existing infrastructure
sys.path.insert(0, str(Path(__file__).parent))
from self_reader import EcnyssReader

class CycleOptimizer:
    """Analyzes evolution history and codebase to generate tuning recommendations."""
    
    def __init__(self, base_path: str = "/root/Ecnyss"):
        self.base_path = Path(base_path)
        self.reader = EcnyssReader(base_path)
        self._analysis_cache = None
    
    def analyze_evolution_patterns(self) -> Dict[str, Any]:
        """Analyze evolution.jsonl for success/failure patterns."""
        entries = self.reader.read_evolution_log()
        
        stats = {
            "total_entries": len(entries),
            "successful": 0,
            "failed": 0,
            "json_failures": 0,
            "incomplete_plans": 0,
            "action_distribution": {},
            "failure_reasons": {},
            "recent_trend": []
        }
        
        for entry in entries:
            status = entry.get("status", "unknown")
            cycle = entry.get("cycle", 0)
            
            # Track action distribution
            action = entry.get("action", "unknown")
            stats["action_distribution"][action] = stats["action_distribution"].get(action, 0) + 1
            
            if status == "ok":
                stats["successful"] += 1
                stats["recent_trend"].append((cycle, "success"))
            else:
                stats["failed"] += 1
                stats["recent_trend"].append((cycle, "failure"))
                
                # Categorize failures
                reason = entry.get("reason", entry.get("status", "unknown"))
                if "json" in reason.lower() or status == "json_failed":
                    stats["json_failures"] += 1
                    reason = "json_parsing"
                elif "incomplete" in reason.lower():
                    stats["incomplete_plans"] += 1
                    reason = "incomplete_plan"
                
                stats["failure_reasons"][reason] = stats["failure_reasons"].get(reason, 0) + 1
        
        # Calculate success rate
        total_attempts = stats["successful"] + stats["failed"]
        stats["success_rate"] = stats["successful"] / total_attempts if total_attempts > 0 else 0.0
        
        return stats
    
    def analyze_codebase_health(self) -> Dict[str, Any]:
        """Analyze current codebase structure and quality."""
        python_files = self.reader.list_python_files()
        
        file_metrics = []
        total_lines = 0
        runnable_files = 0
        documented_files = 0
        
        for rel_path in python_files:
            full_path = self.base_path / rel_path
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                lines = content.split('\n')
                line_count = len(lines)
                total_lines += line_count
                
                has_main = 'if __name__ == "__main__"' in content or "if __name__ == '__main__'" in content
                has_docs = '"""' in content or "'''" in content
                has_shebang = lines[0].startswith('#!') if lines else False
                
                if has_main:
                    runnable_files += 1
                if has_docs:
                    documented_files += 1
                
                file_metrics.append({
                    "path": rel_path,
                    "lines": line_count,
                    "runnable": has_main,
                    "documented": has_docs,
                    "has_shebang": has_shebang
                })
            except Exception:
                continue
        
        file_count = len(file_metrics)
        return {
            "total_files": file_count,
            "total_lines": total_lines,
            "avg_lines": total_lines / file_count if file_count > 0 else 0,
            "runnable_ratio": runnable_files / file_count if file_count > 0 else 0,
            "doc_ratio": documented_files / file_count if file_count > 0 else 0,
            "files": file_metrics
        }
    
    def identify_risks(self, patterns: Dict, health: Dict) -> List[Dict[str, Any]]:
        """Identify risks based on patterns and health metrics."""
        risks = []
        
        # Check for recurring JSON failures
        if patterns["json_failures"] > 0:
            risks.append({
                "level": "high",
                "category": "output_format",
                "description": f"{patterns['json_failures']} historical JSON parsing failures",
                "mitigation": "Ensure output_validator.py is used before all outputs"
            })
        
        # Check success rate
        if patterns["success_rate"] < 0.7:
            risks.append({
                "level": "high",
                "category": "reliability",
                "description": f"Success rate is {patterns['success_rate']:.1%}",
                "mitigation": "Reduce complexity, validate outputs strictly"
            })
        
        # Check for large files
        large_files = [f for f in health["files"] if f["lines"] > 150]
        if large_files:
            risks.append({
                "level": "medium",
                "category": "complexity",
                "description": f"{len(large_files)} files exceed 150 lines",
                "files": [f["path"] for f in large_files],
                "mitigation": "Split large files into modules"
            })
        
        # Check documentation coverage
        if health["doc_ratio"] < 0.5 and health["total_files"] > 2:
            risks.append({
                "level": "low",
                "category": "maintainability",
                "description": f"Only {health['doc_ratio']:.0%} of files have docstrings",
                "mitigation": "Add module docstrings to all Python files"
            })
        
        return risks
    
    def generate_tuning_recommendations(self) -> List[Dict[str, Any]]:
        """Generate specific tuning recommendations for next cycles."""
        patterns = self.analyze_evolution_patterns()
        health = self.analyze_codebase_health()
        risks = self.identify_risks(patterns, health)
        
        recommendations = []
        
        # Capacity tuning based on failure rate
        if patterns["success_rate"] < 0.6:
            recommendations.append({
                "priority": 1,
                "parameter": "max_files_per_cycle",
                "current_value": 3,
                "recommended_value": 2,
                "reason": "High failure rate suggests complexity reduction needed"
            })
        elif patterns["success_rate"] > 0.9 and health["total_files"] < 10:
            recommendations.append({
                "priority": 2,
                "parameter": "max_files_per_cycle",
                "current_value": 3,
                "recommended_value": 3,
                "reason": "High success rate allows maintaining current velocity"
            })
        
        # Validation strictness
        if patterns["json_failures"] > 0 or patterns["incomplete_plans"] > 0:
            recommendations.append({
                "priority": 1,
                "parameter": "validation_mode",
                "current_value": "basic",
                "recommended_value": "strict",
                "reason": "Historical output format failures require strict validation"
            })
        
        # Focus areas
        high_risk_categories = list(set(r["category"] for r in risks if r["level"] == "high"))
        if high_risk_categories:
            recommendations.append({
                "priority": 1,
                "parameter": "focus_areas",
                "value": high_risk_categories,
                "reason": "Address high-risk categories before adding features"
            })
        
        # Integration priority
        if not any("improver" in str(r) for r in recommendations):
            recommendations.append({
                "priority": 3,
                "parameter": "integration_target",
                "value": "/opt/minimax/bin/improver.py",
                "reason": "Mid-cycle phase requires improver.py integration"
            })
        
        return recommendations
    
    def export_tuning_profile(self) -> Dict[str, Any]:
        """Export complete tuning profile for improver.py integration."""
        patterns = self.analyze_evolution_patterns()
        health = self.analyze_codebase_health()
        risks = self.identify_risks(patterns, health)
        recommendations = self.generate_tuning_recommendations()
        
        return {
            "cycle": self.reader.get_last_successful_cycle() or 0,
            "timestamp": patterns.get("recent_trend", [])[-1][0] if patterns.get("recent_trend") else 0,
            "metrics": {
                "success_rate": patterns["success_rate"],
                "total_cycles": patterns["total_entries"],
                "codebase_files": health["total_files"],
                "codebase_lines": health["total_lines"],
                "avg_file_size": health["avg_lines"],
                "documentation_coverage": health["doc_ratio"]
            },
            "risks": risks,
            "tuning_recommendations": recommendations,
            "suggested_next_action": {
                "type": "create" if health["total_files"] < 15 else "refactor",
                "focus": "integration" if risks else "feature",
                "complexity": "low" if patterns["success_rate"] < 0.8 else "medium"
            }
        }
    
    def print_summary(self):
        """Print human-readable analysis summary."""
        profile = self.export_tuning_profile()
        
        print("=" * 60)
        print(f"Ecnyss Cycle Optimizer - Analysis for Cycle {profile['cycle']}")
        print("=" * 60)
        
        print(f"\nSuccess Rate: {profile['metrics']['success_rate']:.1%}")
        print(f"Codebase: {profile['metrics']['codebase_files']} files, {profile['metrics']['codebase_lines']} lines")
        print(f"Avg File Size: {profile['metrics']['avg_file_size']:.0f} lines")
        
        if profile['risks']:
            print(f"\nRisks Identified ({len(profile['risks'])}):")
            for risk in profile['risks']:
                print(f"  [{risk['level'].upper()}] {risk['category']}: {risk['description']}")
        
        if profile['tuning_recommendations']:
            print(f"\nRecommendations ({len(profile['tuning_recommendations'])}):")
            for rec in sorted(profile['tuning_recommendations'], key=lambda x: x['priority']):
                print(f"  P{rec['priority']}: {rec.get('parameter', 'action')} -> {rec.get('recommended_value', rec.get('value', 'N/A'))}")
        
        print(f"\nSuggested Next: {profile['suggested_next_action']['type']} "
              f"({profile['suggested_next_action']['complexity']} complexity, "
              f"{profile['suggested_next_action']['focus']} focus)")
        print("=" * 60)

if __name__ == "__main__":
    optimizer = CycleOptimizer()
    
    # Output JSON profile for machine consumption
    if len(sys.argv) > 1 and sys.argv[1] == "--json":
        profile = optimizer.export_tuning_profile()
        print(json.dumps(profile, indent=2))
    else:
        # Output human-readable summary
        optimizer.print_summary()
        
        # Also export to file for persistence
        profile = optimizer.export_tuning_profile()
        output_path = Path("/root/Ecnyss") / ".tuning_profile.json"
        with open(output_path, 'w') as f:
            json.dump(profile, f, indent=2)
        print(f"\nTuning profile saved to: {output_path}")