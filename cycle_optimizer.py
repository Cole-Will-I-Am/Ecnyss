#!/usr/bin/env python3
"""Cycle optimizer for Ecnyss - analyzes performance data and generates optimization recommendations.

Uses metrics collected by performance_tracker to identify bottlenecks,
analyze trends, and suggest concrete improvements for pipeline efficiency.
Completes the feedback loop from measurement to optimization (cycle 40+).
"""
import json
import statistics
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta


class CycleOptimizer:
    """Analyzes performance metrics and generates optimization recommendations."""
    
    def __init__(self, base_path: str = "/root/Ecnyss"):
        self.base_path = Path(base_path)
        self.metrics_dir = self.base_path / ".ecnyss_metrics"
        self.metrics_file = self.metrics_dir / "performance_log.jsonl"
        self.recommendations_file = self.metrics_dir / "optimization_recommendations.json"
        self.thresholds = {
            "slow_step_ms": 5000,
            "memory_leak_mb": 20,
            "high_failure_rate": 0.1,
            "trend_cycles": 5
        }
    
    def analyze_performance(self, cycle: int) -> Dict[str, Any]:
        """Analyze recent performance data and identify optimization opportunities."""
        if not self.metrics_file.exists():
            return {"status": "no_data", "recommendations": [], "cycle": cycle}
        
        metrics = self._load_metrics()
        if not metrics:
            return {"status": "no_valid_data", "recommendations": [], "cycle": cycle}
        
        recent = metrics[-self.thresholds["trend_cycles"]:]
        
        step_analysis = self._analyze_steps(recent)
        trend_analysis = self._analyze_trends(metrics)
        bottleneck_analysis = self._identify_bottlenecks(recent)
        
        recommendations = []
        recommendations.extend(self._generate_step_recommendations(step_analysis))
        recommendations.extend(self._generate_trend_recommendations(trend_analysis))
        recommendations.extend(self._generate_bottleneck_recommendations(bottleneck_analysis))
        
        recommendations.sort(key=lambda x: x.get("severity_score", 0), reverse=True)
        
        result = {
            "status": "analyzed",
            "cycle": cycle,
            "cycles_analyzed": len(recent),
            "total_cycles": len(metrics),
            "recommendations": recommendations[:10],
            "summary": {
                "total_steps_analyzed": len(step_analysis),
                "degrading_trends": len([t for t in trend_analysis if t["trend"] == "degrading"]),
                "critical_bottlenecks": len([b for b in bottleneck_analysis if b["severity"] == "critical"]),
                "estimated_time_saved_ms": sum(r.get("potential_savings_ms", 0) for r in recommendations)
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self._save_recommendations(result)
        
        return result
    
    def _load_metrics(self) -> List[Dict]:
        """Load all metrics from the log file."""
        metrics = []
        if not self.metrics_file.exists():
            return metrics
        
        with open(self.metrics_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    metrics.append(entry)
                except json.JSONDecodeError:
                    continue
        return metrics
    
    def _analyze_steps(self, metrics: List[Dict]) -> Dict[str, Dict]:
        """Analyze performance by pipeline step."""
        step_data = {}
        
        for entry in metrics:
            for step in entry.get('steps', []):
                step_name = step.get('step', 'unknown')
                if step_name not in step_data:
                    step_data[step_name] = {
                        'durations': [],
                        'memory_deltas': [],
                        'successes': [],
                        'timestamps': []
                    }
                
                step_data[step_name]['durations'].append(step.get('duration_ms', 0))
                step_data[step_name]['memory_deltas'].append(step.get('memory_delta_mb', 0))
                step_data[step_name]['successes'].append(step.get('success', True))
                step_data[step_name]['timestamps'].append(entry.get('timestamp', ''))
        
        analysis = {}
        for step_name, data in step_data.items():
            durations = data['durations']
            memory_deltas = data['memory_deltas']
            successes = data['successes']
            
            analysis[step_name] = {
                'avg_duration_ms': statistics.mean(durations) if durations else 0,
                'max_duration_ms': max(durations) if durations else 0,
                'std_duration': statistics.stdev(durations) if len(durations) > 1 else 0,
                'avg_memory_delta_mb': statistics.mean(memory_deltas) if memory_deltas else 0,
                'max_memory_delta_mb': max(memory_deltas) if memory_deltas else 0,
                'failure_rate': 1 - (sum(successes) / len(successes)) if successes else 0,
                'sample_size': len(durations)
            }
        
        return analysis
    
    def _analyze_trends(self, metrics: List[Dict]) -> List[Dict]:
        """Identify degrading performance trends over time."""
        if len(metrics) < 3:
            return []
        
        trends = []
        
        step_timeline = {}
        for entry in metrics:
            cycle = entry.get('cycle', 0)
            for step in entry.get('steps', []):
                step_name = step.get('step', 'unknown')
                if step_name not in step_timeline:
                    step_timeline[step_name] = []
                step_timeline[step_name].append({
                    'cycle': cycle,
                    'duration': step.get('duration_ms', 0),
                    'memory': step.get('memory_delta_mb', 0),
                    'success': step.get('success', True)
                })
        
        for step_name, timeline in step_timeline.items():
            if len(timeline) < 3:
                continue
            
            durations = [t['duration'] for t in timeline]
            first_half_avg = statistics.mean(durations[:len(durations)//2])
            second_half_avg = statistics.mean(durations[len(durations)//2:])
            
            if second_half_avg > first_half_avg * 1.2:
                trends.append({
                    "step": step_name,
                    "trend": "degrading",
                    "metric": "duration",
                    "increase_percent": ((second_half_avg - first_half_avg) / first_half_avg) * 100,
                    "severity": "high" if second_half_avg > first_half_avg * 1.5 else "medium"
                })
            
            memories = [t['memory'] for t in timeline]
            if all(m > 0 for m in memories[-3:]):
                trends.append({
                    "step": step_name,
                    "trend": "degrading",
                    "metric": "memory",
                    "recent_avg_mb": statistics.mean(memories[-3:]),
                    "severity": "high" if statistics.mean(memories[-3:]) > 50 else "medium"
                })
        
        return trends
    
    def _identify_bottlenecks(self, metrics: List[Dict]) -> List[Dict]:
        """Identify the slowest and most resource-intensive steps."""
        if not metrics:
            return []
        
        step_totals = {}
        for entry in metrics:
            for step in entry.get('steps', []):
                step_name = step.get('step', 'unknown')
                if step_name not in step_totals:
                    step_totals[step_name] = {'total_time': 0, 'total_memory': 0, 'count': 0}
                step_totals[step_name]['total_time'] += step.get('duration_ms', 0)
                step_totals[step_name]['total_memory'] += step.get('memory_delta_mb', 0)
                step_totals[step_name]['count'] += 1
        
        bottlenecks = []
        total_time = sum(s['total_time'] for s in step_totals.values())
        
        for step_name, totals in step_totals.items():
            avg_time = totals['total_time'] / totals['count'] if totals['count'] > 0 else 0
            time_percent = (totals['total_time'] / total_time * 100) if total_time > 0 else 0
            
            severity = "normal"
            if avg_time > self.thresholds["slow_step_ms"]:
                severity = "critical"
            elif time_percent > 30:
                severity = "high"
            elif time_percent > 15:
                severity = "medium"
            
            bottlenecks.append({
                "step": step_name,
                "avg_duration_ms": avg_time,
                "time_percent": time_percent,
                "total_memory_mb": totals['total_memory'],
                "severity": severity,
                "sample_count": totals['count']
            })
        
        bottlenecks.sort(key=lambda x: x['avg_duration_ms'], reverse=True)
        
        return bottlenecks
    
    def _generate_step_recommendations(self, step_analysis: Dict) -> List[Dict]:
        """Generate recommendations based on step performance."""
        recommendations = []
        
        for step_name, stats in step_analysis.items():
            if stats['avg_duration_ms'] > self.thresholds['slow_step_ms']:
                recommendations.append({
                    "type": "slow_step",
                    "step": step_name,
                    "issue": f"Average duration {stats['avg_duration_ms']:.0f}ms exceeds threshold",
                    "recommendation": "Profile this step, consider caching or parallelization",
                    "severity_score": 8,
                    "potential_savings_ms": stats['avg_duration_ms'] - self.thresholds['slow_step_ms']
                })
            
            if stats['failure_rate'] > self.thresholds['high_failure_rate']:
                recommendations.append({
                    "type": "high_failure",
                    "step": step_name,
                    "issue": f"Failure rate {stats['failure_rate']*100:.1f}% is too high",
                    "recommendation": "Add error handling, retry logic, or fix root cause",
                    "severity_score": 9,
                    "potential_savings_ms": 0
                })
            
            if stats['avg_memory_delta_mb'] > self.thresholds['memory_leak_mb']:
                recommendations.append({
                    "type": "memory_growth",
                    "step": step_name,
                    "issue": f"Memory growth {stats['avg_memory_delta_mb']:.1f}MB per cycle",
                    "recommendation": "Check for memory leaks, release resources properly",
                    "severity_score": 7,
                    "potential_savings_ms": 0
                })
        
        return recommendations
    
    def _generate_trend_recommendations(self, trends: List[Dict]) -> List[Dict]:
        """Generate recommendations based on performance trends."""
        recommendations = []
        
        for trend in trends:
            if trend['trend'] == 'degrading':
                severity_score = 8 if trend['severity'] == 'high' else 5
                recommendations.append({
                    "type": "degrading_trend",
                    "step": trend['step'],
                    "metric": trend['metric'],
                    "issue": f"Performance {trend['metric']} is {trend['trend']}",
                    "recommendation": "Investigate recent changes, optimize algorithm",
                    "severity_score": severity_score,
                    "potential_savings_ms": 0
                })
        
        return recommendations
    
    def _generate_bottleneck_recommendations(self, bottlenecks: List[Dict]) -> List[Dict]:
        """Generate recommendations based on identified bottlenecks."""
        recommendations = []
        
        for bottleneck in bottlenecks:
            if bottleneck['severity'] in ['critical', 'high']:
                severity_score = 9 if bottleneck['severity'] == 'critical' else 6
                recommendations.append({
                    "type": "bottleneck",
                    "step": bottleneck['step'],
                    "issue": f"Step consumes {bottleneck['time_percent']:.1f}% of total time",
                    "recommendation": "Prioritize optimization of this step",
                    "severity_score": severity_score,
                    "potential_savings_ms": bottleneck['avg_duration_ms'] * 0.3
                })
        
        return recommendations
    
    def _save_recommendations(self, result: Dict) -> None:
        """Save recommendations to file for decision engine."""
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        
        with open(self.recommendations_file, 'w') as f:
            json.dump(result, f, indent=2, default=str)
    
    def get_top_recommendation(self, cycle: int) -> Optional[Dict]:
        """Get the highest priority recommendation for a cycle."""
        result = self.analyze_performance(cycle)
        if result['recommendations']:
            return result['recommendations'][0]
        return None

    def optimize(self, cycle: Optional[int] = None) -> Dict[str, Any]:
        """Compatibility wrapper used by older runners."""
        effective_cycle = int(cycle) if cycle is not None else 0
        return self.analyze_performance(effective_cycle)


if __name__ == "__main__":
    optimizer = CycleOptimizer()
    result = optimizer.analyze_performance(40)
    print(json.dumps(result, indent=2, default=str))
