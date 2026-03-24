#!/usr/bin/env python3
"""Evolution analyzer for Ecnyss - learns from historical cycle data.

Analyzes evolution.jsonl and health.jsonl to identify patterns,
predict success factors, and guide future evolution decisions.
Completes the learning feedback loop for intelligent self-tuning (cycle 26+).
"""
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Counter
from collections import defaultdict
from datetime import datetime

from self_reader import EcnyssReader


class EvolutionAnalyzer:
    """Analyzes evolution history to extract insights and guide decisions."""
    
    def __init__(self, base_path: str = "/root/Ecnyss"):
        self.base_path = Path(base_path)
        self.reader = EcnyssReader(base_path)
        self.health_log = self.base_path / "health.jsonl"
    
    def load_evolution_history(self) -> List[Dict]:
        """Load all evolution entries."""
        return self.reader.read_evolution_log()
    
    def load_health_history(self) -> List[Dict]:
        """Load all health reports."""
        if not self.health_log.exists():
            return []
        
        entries = []
        with open(self.health_log, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return entries
    
    def analyze_success_patterns(self) -> Dict[str, Any]:
        """Analyze what factors correlate with successful cycles."""
        entries = self.load_evolution_history()
        if not entries:
            return {"error": "No evolution history available"}
        
        total = len(entries)
        successful = [e for e in entries if e.get('status') == 'ok']
        failed = [e for e in entries if e.get('status') != 'ok']
        
        # Success rate by action type
        action_stats = defaultdict(lambda: {"total": 0, "success": 0})
        for entry in entries:
            action = entry.get('action', 'unknown')
            action_stats[action]["total"] += 1
            if entry.get('status') == 'ok':
                action_stats[action]["success"] += 1
        
        action_rates = {
            action: {
                "rate": stats["success"] / stats["total"] if stats["total"] > 0 else 0,
                "total": stats["total"],
                "success": stats["success"]
            }
            for action, stats in action_stats.items()
        }
        
        # File volatility (files that change often)
        file_changes = Counter()
        for entry in entries:
            for file_path in entry.get('files', []):
                file_changes[file_path] += 1
        
        volatile_files = [
            {"path": path, "changes": count}
            for path, count in file_changes.most_common(10)
            if count > 1
        ]
        
        return {
            "total_cycles": total,
            "success_count": len(successful),
            "failure_count": len(failed),
            "overall_success_rate": len(successful) / total if total > 0 else 0,
            "success_by_action": action_rates,
            "volatile_files": volatile_files,
            "most_problematic": self._identify_problematic_files(entries)
        }
    
    def _identify_problematic_files(self, entries: List[Dict]) -> List[Dict]:
        """Identify files that correlate with failures."""
        file_stats = defaultdict(lambda: {"success": 0, "failure": 0})
        
        for entry in entries:
            status = entry.get('status')
            for file_path in entry.get('files', []):
                if status == 'ok':
                    file_stats[file_path]["success"] += 1
                else:
                    file_stats[file_path]["failure"] += 1
        
        # Calculate failure rate for files with multiple changes
        problematic = []
        for path, stats in file_stats.items():
            total = stats["success"] + stats["failure"]
            if total >= 2:
                failure_rate = stats["failure"] / total
                if failure_rate > 0.3:  # More than 30% failure rate
                    problematic.append({
                        "path": path,
                        "failure_rate": failure_rate,
                        "total_changes": total,
                        "failures": stats["failure"]
                    })
        
        return sorted(problematic, key=lambda x: x["failure_rate"], reverse=True)[:5]
    
    def analyze_health_trends(self) -> Dict[str, Any]:
        """Analyze health trends over time."""
        health_entries = self.load_health_history()
        if len(health_entries) < 2:
            return {"error": "Insufficient health history"}
        
        # Track file validity trends
        valid_counts = [e.get('file_health', {}).get('valid_files', 0) for e in health_entries]
        total_counts = [e.get('file_health', {}).get('total_files', 0) for e in health_entries]
        
        if valid_counts and total_counts:
            current_valid = valid_counts[-1]
            current_total = total_counts[-1]
            initial_valid = valid_counts[0]
            initial_total = total_counts[0]
            
            return {
                "current_valid_files": current_valid,
                "current_total_files": current_total,
                "initial_valid_files": initial_valid,
                "initial_total_files": initial_total,
                "valid_file_growth": current_valid - initial_valid,
                "trend": "improving" if current_valid > initial_valid else "stable" if current_valid == initial_valid else "degrading",
                "health_checks_count": len(health_entries)
            }
        
        return {"error": "Could not analyze trends"}
    
    def generate_recommendations(self) -> List[Dict]:
        """Generate data-driven recommendations for next cycle."""
        recommendations = []
        
        # Analyze patterns
        patterns = self.analyze_success_patterns()
        health = self.analyze_health_trends()
        
        # Recommendation 1: Action type with highest success rate
        if "success_by_action" in patterns:
            best_action = max(
                patterns["success_by_action"].items(),
                key=lambda x: x[1]["rate"]
            )
            if best_action[1]["total"] >= 3:  # Minimum sample size
                recommendations.append({
                    "type": "action_strategy",
                    "recommendation": f"Prioritize '{best_action[0]}' actions",
                    "confidence": best_action[1]["rate"],
                    "reasoning": f"'{best_action[0]}' has {best_action[1]['rate']:.1%} success rate over {best_action[1]['total']} attempts"
                })
        
        # Recommendation 2: Avoid volatile files
        if patterns.get("volatile_files"):
            top_volatile = patterns["volatile_files"][:3]
            recommendations.append({
                "type": "stability_focus",
                "recommendation": "Minimize changes to frequently modified files",
                "files_to_stabilize": [f["path"] for f in top_volatile],
                "reasoning": f"Files {[f['path'] for f in top_volatile]} have been modified {sum(f['changes'] for f in top_volatile)} times total, indicating instability"
            })
        
        # Recommendation 3: Address problematic files
        if patterns.get("most_problematic"):
            problematic = patterns["most_problematic"][:2]
            recommendations.append({
                "type": "refactor_priority",
                "recommendation": "Refactor or stabilize problematic files",
                "files": [p["path"] for p in problematic],
                "reasoning": f"Files have high failure rates: {[(p['path'], f'{p['failure_rate']:.1%}') for p in problematic]}"
            })
        
        # Recommendation 4: Health trend
        if "trend" in health:
            if health["trend"] == "degrading":
                recommendations.append({
                    "type": "urgent",
                    "recommendation": "HALT feature addition, focus on stability",
                    "reasoning": f"Valid file count decreased from {health['initial_valid_files']} to {health['current_valid_files']}"
                })
            elif health["trend"] == "improving":
                recommendations.append({
                    "type": "opportunity",
                    "recommendation": "System is stable, good time for architectural improvements",
                    "reasoning": f"Gained {health['valid_file_growth']} valid files since start"
                })
        
        return recommendations
    
    def export_analysis_report(self) -> Dict[str, Any]:
        """Generate comprehensive analysis report."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "cycle": self._get_current_cycle(),
            "success_patterns": self.analyze_success_patterns(),
            "health_trends": self.analyze_health_trends(),
            "recommendations": self.generate_recommendations()
        }
    
    def _get_current_cycle(self) -> int:
        """Get current cycle from evolution log."""
        entries = self.load_evolution_history()
        if entries:
            return max(e.get('cycle', 0) for e in entries)
        return 0
    
    def get_decision_context(self) -> str:
        """Generate context string for decision engine."""
        report = self.export_analysis_report()
        recs = report.get("recommendations", [])
        
        context_parts = ["EVOLUTION ANALYSIS CONTEXT:"]
        
        if recs:
            context_parts.append("\nHistorical Pattern Recommendations:")
            for i, rec in enumerate(recs[:3], 1):
                context_parts.append(f"  {i}. {rec['recommendation']}")
                context_parts.append(f"     Reason: {rec['reasoning']}")
        
        patterns = report.get("success_patterns", {})
        if "overall_success_rate" in patterns:
            context_parts.append(f"\nOverall Success Rate: {patterns['overall_success_rate']:.1%}")

        return "\n".join(context_parts)

    def analyze(self, execution_result: Dict[str, Any]) -> Dict[str, Any]:
        """Compatibility wrapper used by older runners."""
        success = bool(execution_result.get("success"))
        patterns = self.analyze_success_patterns()
        return {
            "success": success,
            "success_rate": patterns.get("overall_success_rate"),
            "volatile_files": patterns.get("volatile_files", []),
        }


if __name__ == "__main__":
    analyzer = EvolutionAnalyzer()
    
    print("=" * 60)
    print("Ecnyss Evolution Analysis Report")
    print("=" * 60)
    
    report = analyzer.export_analysis_report()
    print(json.dumps(report, indent=2))
    
    print("\n" + "=" * 60)
    print("Decision Context for Next Cycle:")
    print("=" * 60)
    print(analyzer.get_decision_context())
