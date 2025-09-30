"""
Performance monitoring and optimization tracking for Macro Dashboard.
"""
import time
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from collections import defaultdict, deque
import pandas as pd

from src.config.settings import get_settings

logger = logging.getLogger(__name__)

# Optional psutil import for system monitoring
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.warning("psutil not available - system monitoring features will be limited")


@dataclass
class PerformanceSnapshot:
    """Snapshot of system performance at a point in time."""
    timestamp: float
    cpu_percent: float
    memory_mb: float
    execution_time: float
    operation_name: str
    data_size: int = 0
    cache_hit: bool = False


@dataclass
class AlgorithmBenchmark:
    """Benchmark results for algorithm performance."""
    algorithm_name: str
    avg_execution_time: float
    min_execution_time: float
    max_execution_time: float
    total_calls: int
    total_data_points: int
    cache_hit_rate: float
    memory_efficiency: float


class PerformanceMonitor:
    """Monitor and track performance metrics for the dashboard."""

    def __init__(self, settings=None, max_snapshots: int = 1000):
        self.settings = settings or get_settings()
        self.max_snapshots = max_snapshots

        # Performance tracking
        self.snapshots: deque = deque(maxlen=max_snapshots)
        self.operation_times: Dict[str, List[float]] = defaultdict(list)
        self.operation_data_sizes: Dict[str, List[int]] = defaultdict(list)
        self.cache_hits: Dict[str, int] = defaultdict(int)
        self.cache_misses: Dict[str, int] = defaultdict(int)

        # System monitoring
        if PSUTIL_AVAILABLE:
            self.process = psutil.Process()
            self.baseline_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        else:
            self.process = None
            self.baseline_memory = 0  # No system monitoring available

    def start_operation(self, operation_name: str) -> float:
        """Start timing an operation."""
        return time.time()

    def end_operation(self, operation_name: str, start_time: float,
                     data_size: int = 0, cache_hit: bool = False) -> PerformanceSnapshot:
        """End timing an operation and record metrics."""
        end_time = time.time()
        execution_time = end_time - start_time

        # Get system metrics
        if PSUTIL_AVAILABLE and self.process:
            cpu_percent = self.process.cpu_percent()
            memory_mb = self.process.memory_info().rss / 1024 / 1024
        else:
            cpu_percent = 0.0  # No system monitoring available
            memory_mb = 0.0

        # Create snapshot
        snapshot = PerformanceSnapshot(
            timestamp=end_time,
            cpu_percent=cpu_percent,
            memory_mb=memory_mb,
            execution_time=execution_time,
            operation_name=operation_name,
            data_size=data_size,
            cache_hit=cache_hit
        )

        # Store snapshot
        self.snapshots.append(snapshot)

        # Update operation statistics
        self.operation_times[operation_name].append(execution_time)
        self.operation_data_sizes[operation_name].append(data_size)

        if cache_hit:
            self.cache_hits[operation_name] += 1
        else:
            self.cache_misses[operation_name] += 1

        # Keep only recent data (last 100 operations per type)
        if len(self.operation_times[operation_name]) > 100:
            self.operation_times[operation_name] = self.operation_times[operation_name][-100:]
            self.operation_data_sizes[operation_name] = self.operation_data_sizes[operation_name][-100:]

        return snapshot

    def get_operation_benchmark(self, operation_name: str) -> Optional[AlgorithmBenchmark]:
        """Get benchmark statistics for a specific operation."""
        if operation_name not in self.operation_times:
            return None

        times = self.operation_times[operation_name]
        # Ensure data_sizes list matches times list length
        current_data_sizes = self.operation_data_sizes.get(operation_name, [])
        if len(current_data_sizes) < len(times):
            # Pad with zeros if needed
            current_data_sizes.extend([0] * (len(times) - len(current_data_sizes)))
        data_sizes = current_data_sizes

        total_calls = len(times)
        if total_calls == 0:
            return None

        total_data_points = sum(data_sizes)

        # Calculate cache hit rate
        total_cache_ops = self.cache_hits[operation_name] + self.cache_misses[operation_name]
        cache_hit_rate = (self.cache_hits[operation_name] / total_cache_ops * 100) if total_cache_ops > 0 else 0

        # Memory efficiency (MB per data point) - safer calculation
        memory_efficiency = 0.0
        if total_data_points > 0 and self.snapshots:
            recent_snapshots = list(self.snapshots)[-min(10, len(self.snapshots)):]
            if recent_snapshots:
                recent_memory = sum(s.memory_mb for s in recent_snapshots) / len(recent_snapshots)
                memory_efficiency = recent_memory / max(total_data_points, 1)

        return AlgorithmBenchmark(
            algorithm_name=operation_name,
            avg_execution_time=sum(times) / max(total_calls, 1),
            min_execution_time=min(times) if times else 0,
            max_execution_time=max(times) if times else 0,
            total_calls=total_calls,
            total_data_points=total_data_points,
            cache_hit_rate=cache_hit_rate,
            memory_efficiency=memory_efficiency
        )

    def get_all_benchmarks(self) -> Dict[str, AlgorithmBenchmark]:
        """Get benchmarks for all tracked operations."""
        benchmarks = {}

        for operation_name in self.operation_times.keys():
            benchmark = self.get_operation_benchmark(operation_name)
            if benchmark:
                benchmarks[operation_name] = benchmark

        return benchmarks

    def get_system_performance_summary(self) -> Dict[str, Any]:
        """Get overall system performance summary."""
        if not self.snapshots:
            return {"error": "No performance data available"}

        recent_snapshots = list(self.snapshots)[-50:]  # Last 50 operations

        avg_cpu = sum(s.cpu_percent for s in recent_snapshots) / len(recent_snapshots)
        avg_memory = sum(s.memory_mb for s in recent_snapshots) / len(recent_snapshots)
        total_execution_time = sum(s.execution_time for s in recent_snapshots)

        # Performance trends
        older_half = recent_snapshots[:len(recent_snapshots)//2]
        newer_half = recent_snapshots[len(recent_snapshots)//2:]

        older_avg_time = sum(s.execution_time for s in older_half) / len(older_half)
        newer_avg_time = sum(s.execution_time for s in newer_half) / len(newer_half)

        performance_trend = "improving" if newer_avg_time < older_avg_time else "degrading"

        return {
            "average_cpu_percent": round(avg_cpu, 2),
            "average_memory_mb": round(avg_memory, 2),
            "total_execution_time_seconds": round(total_execution_time, 2),
            "total_operations": len(recent_snapshots),
            "performance_trend": performance_trend,
            "memory_increase_mb": round(avg_memory - self.baseline_memory, 2),
            "operations_per_second": round(len(recent_snapshots) / max(total_execution_time, 0.001), 2)
        }

    def get_cache_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive cache performance report."""
        total_operations = sum(self.cache_hits.values()) + sum(self.cache_misses.values())

        if total_operations == 0:
            return {"error": "No cache operations recorded"}

        overall_hit_rate = (sum(self.cache_hits.values()) / total_operations) * 100

        # Per-operation cache performance
        operation_cache_stats = {}
        for operation in set(self.cache_hits.keys()) | set(self.cache_misses.keys()):
            hits = self.cache_hits[operation]
            misses = self.cache_misses[operation]
            total = hits + misses
            hit_rate = (hits / total * 100) if total > 0 else 0

            operation_cache_stats[operation] = {
                "hits": hits,
                "misses": misses,
                "total": total,
                "hit_rate_percent": round(hit_rate, 2)
            }

        return {
            "overall_cache_hit_rate_percent": round(overall_hit_rate, 2),
            "total_cache_operations": total_operations,
            "operation_cache_stats": operation_cache_stats
        }

    def export_performance_data(self) -> pd.DataFrame:
        """Export performance data as DataFrame for analysis."""
        if not self.snapshots:
            return pd.DataFrame()

        data = []
        for snapshot in self.snapshots:
            data.append({
                "timestamp": snapshot.timestamp,
                "operation": snapshot.operation_name,
                "execution_time": snapshot.execution_time,
                "cpu_percent": snapshot.cpu_percent,
                "memory_mb": snapshot.memory_mb,
                "data_size": snapshot.data_size,
                "cache_hit": snapshot.cache_hit
            })

        return pd.DataFrame(data)

    def reset_monitoring(self) -> None:
        """Reset all performance monitoring data."""
        self.snapshots.clear()
        self.operation_times.clear()
        self.operation_data_sizes.clear()
        self.cache_hits.clear()
        self.cache_misses.clear()
        if PSUTIL_AVAILABLE and self.process:
            self.baseline_memory = self.process.memory_info().rss / 1024 / 1024
        else:
            self.baseline_memory = 0

    def get_memory_usage_trend(self) -> Dict[str, Any]:
        """Analyze memory usage trends."""
        if len(self.snapshots) < 10:
            return {"error": "Insufficient data for trend analysis"}

        # Get memory usage over time
        memory_values = [s.memory_mb for s in self.snapshots]
        timestamps = [s.timestamp for s in self.snapshots]

        # Calculate trend
        if len(memory_values) >= 2:
            first_half = memory_values[:len(memory_values)//2]
            second_half = memory_values[len(memory_values)//2:]

            first_avg = sum(first_half) / len(first_half)
            second_avg = sum(second_half) / len(second_half)

            memory_trend = "increasing" if second_avg > first_avg else "decreasing"
            memory_change = second_avg - first_avg
        else:
            memory_trend = "stable"
            memory_change = 0

        return {
            "current_memory_mb": memory_values[-1],
            "baseline_memory_mb": self.baseline_memory,
            "peak_memory_mb": max(memory_values),
            "memory_trend": memory_trend,
            "memory_change_mb": round(memory_change, 2),
            "memory_efficiency": "good" if memory_change < 50 else "concerning"
        }


# Global performance monitor instance
_performance_monitor = None

def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance."""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor

def reset_performance_monitor() -> None:
    """Reset the global performance monitor."""
    global _performance_monitor
    if _performance_monitor:
        _performance_monitor.reset_monitoring()
    _performance_monitor = None