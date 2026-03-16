"""
System telemetry and metrics collection for monitoring and observability.
Provides system metrics, latency tracking, and performance monitoring.
"""

import os
import time
import platform
import psutil
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from collections import defaultdict
from datetime import datetime, timezone

from app.core.logging.logger import get_logger

logger = get_logger("telemetry")


@dataclass
class LatencyMetrics:
    """Container for latency statistics."""
    p50: float = 0.0
    p95: float = 0.0
    p99: float = 0.0
    count: int = 0
    total_ms: float = 0.0
    min_ms: float = float('inf')
    max_ms: float = 0.0
    
    def add(self, latency_ms: float) -> None:
        """Add a latency measurement."""
        self.count += 1
        self.total_ms += latency_ms
        self.min_ms = min(self.min_ms, latency_ms)
        self.max_ms = max(self.max_ms, latency_ms)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "p50_ms": round(self.p50, 2),
            "p95_ms": round(self.p95, 2),
            "p99_ms": round(self.p99, 2),
            "count": self.count,
            "avg_ms": round(self.total_ms / self.count, 2) if self.count > 0 else 0,
            "min_ms": round(self.min_ms, 2) if self.min_ms != float('inf') else 0,
            "max_ms": round(self.max_ms, 2),
        }


class LatencyCollector:
    """
    Collect and calculate latency statistics for API endpoints.
    Uses a sliding window approach to maintain recent metrics.
    """
    
    def __init__(self, max_samples: int = 1000):
        self._latencies: Dict[str, List[float]] = defaultdict(list)
        self._max_samples = max_samples
        self._lock = False  # Simple lock flag for thread safety
    
    def add_latency(self, endpoint: str, latency_ms: float) -> None:
        """
        Add a latency measurement for an endpoint.
        
        Args:
            endpoint: Endpoint identifier (e.g., "GET /health")
            latency_ms: Latency in milliseconds
        """
        # Simple thread-safety (in production, use threading.Lock)
        latencies = self._latencies[endpoint]
        latencies.append(latency_ms)
        
        # Maintain sliding window
        if len(latencies) > self._max_samples:
            latencies.pop(0)
    
    def _calculate_percentile(self, values: List[float], percentile: float) -> float:
        """Calculate percentile from a list of values."""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = int(len(sorted_values) * (percentile / 100.0))
        return sorted_values[min(index, len(sorted_values) - 1)]
    
    def get_stats(self, endpoint: Optional[str] = None) -> Dict[str, Any]:
        """
        Get latency statistics.
        
        Args:
            endpoint: Optional endpoint to filter by. If None, returns stats for all endpoints.
        
        Returns:
            Dictionary with latency statistics
        """
        if endpoint:
            latencies = self._latencies.get(endpoint, [])
            if not latencies:
                return {endpoint: LatencyMetrics().to_dict()}
            
            metrics = LatencyMetrics()
            for lat in latencies:
                metrics.add(lat)
            
            metrics.p50 = self._calculate_percentile(latencies, 50)
            metrics.p95 = self._calculate_percentile(latencies, 95)
            metrics.p99 = self._calculate_percentile(latencies, 99)
            
            return {endpoint: metrics.to_dict()}
        
        # Return stats for all endpoints
        all_stats = {}
        for ep, latencies in self._latencies.items():
            if latencies:
                metrics = LatencyMetrics()
                for lat in latencies:
                    metrics.add(lat)
                
                metrics.p50 = self._calculate_percentile(latencies, 50)
                metrics.p95 = self._calculate_percentile(latencies, 95)
                metrics.p99 = self._calculate_percentile(latencies, 99)
                
                all_stats[ep] = metrics.to_dict()
        
        return all_stats
    
    def reset(self, endpoint: Optional[str] = None) -> None:
        """Reset latency statistics."""
        if endpoint:
            self._latencies[endpoint] = []
        else:
            self._latencies.clear()


class SystemTelemetry:
    """
    System telemetry collector for monitoring system health and performance.
    Provides CPU, memory, disk, and network metrics.
    """
    
    _instance: Optional['SystemTelemetry'] = None
    _initialized: bool = False
    
    def __new__(cls) -> 'SystemTelemetry':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._start_time = time.time()
        self._initialized = True
    
    @staticmethod
    def get_metrics() -> Dict[str, Any]:
        """
        Get current system telemetry metrics.
        
        Returns:
            Dictionary with system metrics including:
            - cpu_percent
            - memory_percent
            - disk_usage
            - network_io
            - uptime_seconds
            - platform_info
        """
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_count = psutil.cpu_count()
            
            # Memory metrics
            memory = psutil.virtual_memory()
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            
            # Network metrics
            net_io = psutil.net_io_counters()
            
            # Process info
            process = psutil.Process()
            
            metrics = {
                "cpu": {
                    "percent": cpu_percent,
                    "count": cpu_count,
                    "per_cpu": psutil.cpu_percent(interval=0.1, percpu=True),
                },
                "memory": {
                    "percent": memory.percent,
                    "available_mb": round(memory.available / (1024 * 1024), 2),
                    "used_mb": round(memory.used / (1024 * 1024), 2),
                    "total_mb": round(memory.total / (1024 * 1024), 2),
                },
                "disk": {
                    "percent": round((disk.used / disk.total) * 100, 2),
                    "used_gb": round(disk.used / (1024**3), 2),
                    "total_gb": round(disk.total / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                },
                "network": {
                    "bytes_sent_mb": round(net_io.bytes_sent / (1024 * 1024), 2),  # type: ignore
                    "bytes_recv_mb": round(net_io.bytes_recv / (1024 * 1024), 2),  # type: ignore
                    "packets_sent": net_io.packets_sent,  # type: ignore
                    "packets_recv": net_io.packets_recv,  # type: ignore
                } if net_io else {},
                "process": {
                    "memory_mb": round(process.memory_info().rss / (1024 * 1024), 2),
                    "cpu_percent": process.cpu_percent(interval=0.1),
                    "threads": process.num_threads(),
                    "open_files": len(process.open_files()),
                    "connections": len(process.connections()),
                },
                "platform": {
                    "system": platform.system(),
                    "release": platform.release(),
                    "version": platform.version(),
                    "machine": platform.machine(),
                    "processor": platform.processor(),
                    "python_version": platform.python_version(),
                },
                "timestamp": datetime.utcnow().isoformat(),
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
    
    @staticmethod
    def get_uptime() -> Dict[str, Any]:
        """Get system and process uptime information."""
        instance = SystemTelemetry()
        uptime_seconds = time.time() - instance._start_time
        
        return {
            "uptime_seconds": int(uptime_seconds),
            "uptime_formatted": _format_duration(uptime_seconds),
            "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat(),
        }
    
    @staticmethod
    def check_health() -> Dict[str, Any]:
        """
        Perform a health check on system resources.
        
        Returns:
            Health status with warnings if resources are constrained
        """
        metrics = SystemTelemetry.get_metrics()
        warnings = []
        status = "healthy"
        
        # Check CPU
        if metrics["cpu"]["percent"] > 90:
            warnings.append("High CPU usage")
            status = "warning"
        
        # Check Memory
        if metrics["memory"]["percent"] > 90:
            warnings.append("High memory usage")
            status = "critical"
        elif metrics["memory"]["percent"] > 80:
            warnings.append("Elevated memory usage")
            status = "warning"
        
        # Check Disk
        if metrics["disk"]["percent"] > 90:
            warnings.append("Low disk space")
            status = "critical"
        elif metrics["disk"]["percent"] > 80:
            warnings.append("Disk space running low")
            status = "warning"
        
        return {
            "status": status,
            "warnings": warnings,
            "metrics": metrics,
        }


def _format_duration(seconds: float) -> str:
    """Format seconds into human-readable duration."""
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")
    
    return " ".join(parts)


# Global latency collector instance
latency_collector = LatencyCollector()