"""
Metrics collection module for Prometheus/OpenTelemetry.
Provides application metrics for monitoring and observability.
"""
import time
import asyncio
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from collections import defaultdict
from functools import wraps

from app.core.logging.logger import get_logger

logger = get_logger("metrics")


@dataclass
class HistogramSnapshot:
    """Snapshot of histogram data."""
    count: int
    sum: float
    buckets: Dict[str, int]
    p50: float
    p95: float
    p99: float


class Histogram:
    """Simple histogram for latency measurements."""
    
    def __init__(self, name: str, buckets: Optional[list] = None):
        self.name = name
        self.buckets: list = buckets if buckets is not None else [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
        self._values: list = []
        self._sum: float = 0.0
        self._count: int = 0
        self._lock = asyncio.Lock()
    
    async def observe(self, value: float):
        """Record a value."""
        async with self._lock:
            self._values.append(value)
            self._sum += value
            self._count += 1
            
            # Keep only last 10000 values to prevent memory growth
            if len(self._values) > 10000:
                self._values = list(self._values[-5000:])
    
    async def get_snapshot(self) -> HistogramSnapshot:
        """Get histogram snapshot."""
        async with self._lock:
            if not self._values:
                return HistogramSnapshot(0, 0.0, {}, 0.0, 0.0, 0.0)
            
            sorted_values = sorted(self._values)
            n = len(sorted_values)
            
            # Calculate percentiles
            p50 = sorted_values[int(n * 0.5)]
            p95 = sorted_values[int(n * 0.95)] if n > 1 else sorted_values[0]
            p99 = sorted_values[int(n * 0.99)] if n > 1 else sorted_values[0]
            
            # Calculate buckets
            bucket_counts = {}
            cumulative = 0
            for bucket in self.buckets:
                count = sum(1 for v in self._values if v <= bucket)
                cumulative = count
                bucket_counts[f"le_{bucket}"] = count
            
            # Add +Inf bucket
            bucket_counts["le_inf"] = self._count
            
            return HistogramSnapshot(
                count=self._count,
                sum=self._sum,
                buckets=bucket_counts,
                p50=p50,
                p95=p95,
                p99=p99
            )


class Counter:
    """Simple counter metric."""
    
    def __init__(self, name: str, labels: Optional[list] = None):
        self.name = name
        self.labels: list = labels if labels is not None else []
        self._counts: Dict[str, int] = defaultdict(int)
        self._lock = asyncio.Lock()
    
    async def inc(self, amount: int = 1, **label_values):
        """Increment counter."""
        label_key = self._format_labels(label_values)
        async with self._lock:
            self._counts[label_key] += amount
    
    def _format_labels(self, labels: Dict[str, str]) -> str:
        """Format labels for storage."""
        if not labels:
            return ""
        return ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
    
    async def get_value(self, **label_values) -> int:
        """Get counter value."""
        label_key = self._format_labels(label_values)
        async with self._lock:
            return self._counts.get(label_key, 0)
    
    async def get_all(self) -> Dict[str, int]:
        """Get all counter values."""
        async with self._lock:
            return dict(self._counts)


class Gauge:
    """Simple gauge metric."""
    
    def __init__(self, name: str):
        self.name = name
        self._value: float = 0.0
        self._lock = asyncio.Lock()
    
    async def set(self, value: float):
        """Set gauge value."""
        async with self._lock:
            self._value = value
    
    async def inc(self, amount: float = 1.0):
        """Increment gauge."""
        async with self._lock:
            self._value += amount
    
    async def dec(self, amount: float = 1.0):
        """Decrement gauge."""
        async with self._lock:
            self._value -= amount
    
    async def get_value(self) -> float:
        """Get gauge value."""
        async with self._lock:
            return self._value


class MetricsCollector:
    """
    Central metrics collector for the application.
    """
    
    def __init__(self):
        self._counters: Dict[str, Counter] = {}
        self._histograms: Dict[str, Histogram] = {}
        self._gauges: Dict[str, Gauge] = {}
        self._lock = asyncio.Lock()
    
    async def get_or_create_counter(self, name: str, labels: Optional[list] = None) -> Counter:
        """Get or create a counter."""
        async with self._lock:
            if name not in self._counters:
                self._counters[name] = Counter(name, labels)
            return self._counters[name]
    
    async def get_or_create_histogram(self, name: str, buckets: Optional[list] = None) -> Histogram:
        """Get or create a histogram."""
        async with self._lock:
            if name not in self._histograms:
                self._histograms[name] = Histogram(name, buckets)
            return self._histograms[name]
    
    async def get_or_create_gauge(self, name: str) -> Gauge:
        """Get or create a gauge."""
        async with self._lock:
            if name not in self._gauges:
                self._gauges[name] = Gauge(name)
            return self._gauges[name]
    
    def counter(self, name: str, labels: Optional[list] = None):
        """Decorator to track counter."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                counter = await self.get_or_create_counter(name, labels)
                await counter.inc()
                return await func(*args, **kwargs)
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                # Fire and forget for sync functions
                asyncio.create_task(self._inc_counter(name, labels))
                return func(*args, **kwargs)
            
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            return sync_wrapper
        return decorator
    
    async def _inc_counter(self, name: str, labels: Optional[list]):
        """Helper to increment counter."""
        counter = await self.get_or_create_counter(name, labels)
        await counter.inc()
    
    def histogram(self, name: str, buckets: Optional[list] = None):
        """Decorator to track histogram."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                hist = await self.get_or_create_histogram(name, buckets)
                start = time.time()
                try:
                    return await func(*args, **kwargs)
                finally:
                    duration = time.time() - start
                    await hist.observe(duration)
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                start = time.time()
                try:
                    return func(*args, **kwargs)
                finally:
                    duration = time.time() - start
                    asyncio.create_task(self._observe_histogram(name, buckets, duration))
            
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            return sync_wrapper
        return decorator
    
    async def _observe_histogram(self, name: str, buckets: Optional[list], duration: float):
        """Helper to observe histogram."""
        hist = await self.get_or_create_histogram(name, buckets)
        await hist.observe(duration)
    
    async def generate_prometheus_format(self) -> str:
        """Generate metrics in Prometheus exposition format."""
        lines = []
        
        # Counters
        async with self._lock:
            for name, counter in self._counters.items():
                lines.append(f"# HELP {name} Total count")
                lines.append(f"# TYPE {name} counter")
                values = await counter.get_all()
                for labels, value in values.items():
                    if labels:
                        lines.append(f'{name}{{{labels}}} {value}')
                    else:
                        lines.append(f'{name} {value}')
        
        # Histograms
        async with self._lock:
            for name, hist in self._histograms.items():
                lines.append(f"# HELP {name} Duration in seconds")
                lines.append(f"# TYPE {name} histogram")
                snapshot = await hist.get_snapshot()
                if snapshot.count > 0:
                    for bucket_name, count in snapshot.buckets.items():
                        bucket = bucket_name.replace("le_", "").replace("_", ".")
                        if bucket == "inf":
                            bucket = "+Inf"
                        lines.append(f'{name}_bucket{{le="{bucket}"}} {count}')
                    lines.append(f'{name}_sum {snapshot.sum}')
                    lines.append(f'{name}_count {snapshot.count}')
        
        # Gauges
        async with self._lock:
            for name, gauge in self._gauges.items():
                lines.append(f"# HELP {name} Current value")
                lines.append(f"# TYPE {name} gauge")
                value = await gauge.get_value()
                lines.append(f'{name} {value}')
        
        return "\n".join(lines) + "\n"
    
    async def get_metrics_dict(self) -> Dict[str, Any]:
        """Get all metrics as a dictionary."""
        metrics = {}
        
        # Counters
        async with self._lock:
            for name, counter in self._counters.items():
                metrics[f"{name}_total"] = await counter.get_all()
        
        # Histograms
        async with self._lock:
            for name, hist in self._histograms.items():
                snapshot = await hist.get_snapshot()
                metrics[name] = {
                    "count": snapshot.count,
                    "sum": snapshot.sum,
                    "p50": snapshot.p50,
                    "p95": snapshot.p95,
                    "p99": snapshot.p99
                }
        
        # Gauges
        async with self._lock:
            for name, gauge in self._gauges.items():
                metrics[name] = await gauge.get_value()
        
        return metrics


# Global metrics collector
metrics_collector = MetricsCollector()


# Predefined metrics
async def get_ocr_counter() -> Counter:
    """Get OCR request counter."""
    return await metrics_collector.get_or_create_counter(
        "ocr_requests_total",
        ["provider", "status"]
    )


async def get_ocr_histogram() -> Histogram:
    """Get OCR duration histogram."""
    return await metrics_collector.get_or_create_histogram(
        "ocr_duration_seconds",
        [0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0]
    )


async def get_chat_counter() -> Counter:
    """Get chat request counter."""
    return await metrics_collector.get_or_create_counter(
        "chat_requests_total",
        ["provider", "status"]
    )


async def get_chat_histogram() -> Histogram:
    """Get chat duration histogram."""
    return await metrics_collector.get_or_create_histogram(
        "chat_duration_seconds",
        [0.1, 0.5, 1.0, 2.5, 5.0, 10.0]
    )


async def get_cache_counter() -> Counter:
    """Get cache operation counter."""
    return await metrics_collector.get_or_create_counter(
        "cache_operations_total",
        ["cache_type", "operation", "result"]
    )


async def get_circuit_breaker_gauge() -> Gauge:
    """Get circuit breaker state gauge."""
    return await metrics_collector.get_or_create_gauge("circuit_breaker_state")


# Decorators for easy metric collection
def track_ocr(provider: str):
    """Decorator to track OCR metrics."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            counter = await get_ocr_counter()
            histogram = await get_ocr_histogram()
            
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                await counter.inc(provider=provider, status="success")
                return result
            except Exception:
                await counter.inc(provider=provider, status="error")
                raise
            finally:
                duration = time.time() - start
                await histogram.observe(duration)
        
        return wrapper
    return decorator


def track_chat(provider: str):
    """Decorator to track chat metrics."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            counter = await get_chat_counter()
            histogram = await get_chat_histogram()
            
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                await counter.inc(provider=provider, status="success")
                return result
            except Exception:
                await counter.inc(provider=provider, status="error")
                raise
            finally:
                duration = time.time() - start
                await histogram.observe(duration)
        
        return wrapper
    return decorator