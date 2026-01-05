"""
Resource Monitor - Track system resource metrics non-blockingly.

Provides CPU, memory, and disk monitoring with async-safe operations.
Uses psutil with interval=0 (non-blocking) to avoid blocking event loops.
"""

import psutil
import logging
import time
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ResourceLevel(str, Enum):
    """Resource health levels"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class ResourceMetrics:
    """Current system resource metrics"""
    cpu_percent: float
    memory_percent: float
    memory_available_mb: float
    disk_percent: float
    timestamp: float

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "memory_available_mb": self.memory_available_mb,
            "disk_percent": self.disk_percent,
            "timestamp": self.timestamp,
        }


class ResourceThresholds:
    """Configurable thresholds for resource warnings/criticality"""

    def __init__(
        self,
        cpu_warning: float = 70.0,
        cpu_critical: float = 90.0,
        memory_warning: float = 75.0,
        memory_critical: float = 90.0,
        disk_warning: float = 80.0,
        disk_critical: float = 95.0,
    ):
        self.cpu_warning = cpu_warning
        self.cpu_critical = cpu_critical
        self.memory_warning = memory_warning
        self.memory_critical = memory_critical
        self.disk_warning = disk_warning
        self.disk_critical = disk_critical


class ResourceMonitor:
    """Monitor system resources without blocking the event loop"""

    def __init__(self, thresholds: Optional[ResourceThresholds] = None):
        """
        Initialize resource monitor.

        Args:
            thresholds: Custom resource thresholds (uses defaults if None)
        """
        self.thresholds = thresholds or ResourceThresholds()
        self.metrics_history: List[ResourceMetrics] = []
        self.max_history = 100
        self._monitoring_enabled = True

    def get_current_metrics(self) -> ResourceMetrics:
        """
        Get current resource metrics WITHOUT blocking.

        Uses interval=0 to avoid blocking the event loop.
        Returns cached value from last call, updated non-blockingly.
        """
        try:
            # Use interval=0 for non-blocking CPU percent check
            # This returns the CPU usage since the last call
            cpu_percent = psutil.cpu_percent(interval=0)

            # Memory info (always non-blocking)
            memory_info = psutil.virtual_memory()
            memory_percent = memory_info.percent
            memory_available_mb = memory_info.available / (1024 * 1024)

            # Disk info (always non-blocking)
            disk_info = psutil.disk_usage("/")
            disk_percent = disk_info.percent

            metrics = ResourceMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_available_mb=memory_available_mb,
                disk_percent=disk_percent,
                timestamp=time.time(),
            )

            # Store in history
            self.metrics_history.append(metrics)
            if len(self.metrics_history) > self.max_history:
                self.metrics_history.pop(0)

            return metrics

        except Exception as e:
            logger.error(f"Failed to get resource metrics: {e}")
            # Return safe defaults on error
            return ResourceMetrics(
                cpu_percent=0,
                memory_percent=0,
                memory_available_mb=0,
                disk_percent=0,
                timestamp=time.time(),
            )

    def check_resource_health(self) -> Dict[str, str]:
        """
        Check resource health status.

        Returns:
            Dict with health status for each resource
        """
        if not self._monitoring_enabled:
            return {"status": "monitoring_disabled"}

        metrics = self.get_current_metrics()
        health = {}

        # Check CPU
        if metrics.cpu_percent >= self.thresholds.cpu_critical:
            health["cpu"] = ResourceLevel.CRITICAL
            logger.critical(f"CPU critical: {metrics.cpu_percent}%")
        elif metrics.cpu_percent >= self.thresholds.cpu_warning:
            health["cpu"] = ResourceLevel.WARNING
            logger.warning(f"CPU warning: {metrics.cpu_percent}%")
        else:
            health["cpu"] = ResourceLevel.HEALTHY

        # Check Memory
        if metrics.memory_percent >= self.thresholds.memory_critical:
            health["memory"] = ResourceLevel.CRITICAL
            logger.critical(
                f"Memory critical: {metrics.memory_percent}% "
                f"({metrics.memory_available_mb:.0f} MB available)"
            )
        elif metrics.memory_percent >= self.thresholds.memory_warning:
            health["memory"] = ResourceLevel.WARNING
            logger.warning(
                f"Memory warning: {metrics.memory_percent}% "
                f"({metrics.memory_available_mb:.0f} MB available)"
            )
        else:
            health["memory"] = ResourceLevel.HEALTHY

        # Check Disk
        if metrics.disk_percent >= self.thresholds.disk_critical:
            health["disk"] = ResourceLevel.CRITICAL
            logger.critical(f"Disk critical: {metrics.disk_percent}%")
        elif metrics.disk_percent >= self.thresholds.disk_warning:
            health["disk"] = ResourceLevel.WARNING
            logger.warning(f"Disk warning: {metrics.disk_percent}%")
        else:
            health["disk"] = ResourceLevel.HEALTHY

        return health

    def is_resource_available(self) -> bool:
        """Check if resources are available (not in critical state)"""
        health = self.check_resource_health()
        return not any(v == ResourceLevel.CRITICAL for v in health.values())

    def get_metrics_summary(self) -> Dict:
        """Get summary of recent metrics"""
        if not self.metrics_history:
            return {}

        latest = self.metrics_history[-1]
        return {
            "latest": latest.to_dict(),
            "history_size": len(self.metrics_history),
            "health_status": self.check_resource_health(),
        }

    def set_monitoring_enabled(self, enabled: bool):
        """Enable or disable resource monitoring"""
        self._monitoring_enabled = enabled


# Global singleton instance
_resource_monitor: Optional[ResourceMonitor] = None


def get_resource_monitor(
    custom_thresholds: Optional[ResourceThresholds] = None,
) -> ResourceMonitor:
    """Get or create the global resource monitor singleton"""
    global _resource_monitor

    if _resource_monitor is None:
        _resource_monitor = ResourceMonitor(thresholds=custom_thresholds)

    return _resource_monitor
