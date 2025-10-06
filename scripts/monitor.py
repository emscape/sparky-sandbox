#!/usr/bin/env python3
"""System health monitoring for AI Memory System."""

import asyncio
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import statistics
from dataclasses import dataclass, asdict

from config import config
from helpers import get_embedding
from supabase import create_client, Client
from openai import AsyncOpenAI


@dataclass
class HealthMetric:
    """Represents a health metric measurement."""
    timestamp: str
    metric_name: str
    value: float
    unit: str
    status: str  # "healthy", "warning", "critical"
    details: Optional[Dict[str, Any]] = None


@dataclass
class SystemHealth:
    """Overall system health status."""
    timestamp: str
    overall_status: str
    metrics: List[HealthMetric]
    summary: Dict[str, Any]


class HealthMonitor:
    """Monitors system health and performance metrics."""
    
    def __init__(self, metrics_file: str = "health_metrics.json"):
        """Initialize health monitor."""
        self.metrics_file = Path(metrics_file)
        self.supabase_client = None
        self.openai_client = None
        
        # Health thresholds
        self.thresholds = {
            "embedding_response_time": {"warning": 3.0, "critical": 10.0},
            "database_response_time": {"warning": 2.0, "critical": 5.0},
            "error_rate": {"warning": 0.05, "critical": 0.15},  # 5% warning, 15% critical
            "memory_usage": {"warning": 80.0, "critical": 95.0}  # percentage
        }
        
        print("📊 Health Monitor initialized")
    
    def get_clients(self):
        """Initialize API clients if not already done."""
        if self.supabase_client is None:
            self.supabase_client = create_client(config.supabase_url, config.supabase_key)
        
        if self.openai_client is None:
            self.openai_client = AsyncOpenAI(api_key=config.openai_api_key)
    
    async def measure_embedding_performance(self) -> HealthMetric:
        """Measure OpenAI embedding API performance."""
        self.get_clients()
        
        test_text = "Health monitoring test for embedding performance measurement."
        
        try:
            start_time = time.time()
            await get_embedding(test_text, self.openai_client)
            response_time = time.time() - start_time
            
            # Determine status
            if response_time < self.thresholds["embedding_response_time"]["warning"]:
                status = "healthy"
            elif response_time < self.thresholds["embedding_response_time"]["critical"]:
                status = "warning"
            else:
                status = "critical"
            
            return HealthMetric(
                timestamp=datetime.now().isoformat(),
                metric_name="embedding_response_time",
                value=response_time,
                unit="seconds",
                status=status,
                details={"model": config.embedding_model, "dimensions": config.embedding_dimensions}
            )
            
        except Exception as e:
            return HealthMetric(
                timestamp=datetime.now().isoformat(),
                metric_name="embedding_response_time",
                value=-1,
                unit="seconds",
                status="critical",
                details={"error": str(e)}
            )
    
    async def measure_database_performance(self) -> HealthMetric:
        """Measure Supabase database performance."""
        self.get_clients()
        
        try:
            start_time = time.time()
            
            # Simple query to test database responsiveness
            response = self.supabase_client.table(config.memory_table).select("id").limit(1).execute()
            
            response_time = time.time() - start_time
            
            # Determine status
            if response_time < self.thresholds["database_response_time"]["warning"]:
                status = "healthy"
            elif response_time < self.thresholds["database_response_time"]["critical"]:
                status = "warning"
            else:
                status = "critical"
            
            return HealthMetric(
                timestamp=datetime.now().isoformat(),
                metric_name="database_response_time",
                value=response_time,
                unit="seconds",
                status=status,
                details={"table": config.memory_table}
            )
            
        except Exception as e:
            return HealthMetric(
                timestamp=datetime.now().isoformat(),
                metric_name="database_response_time",
                value=-1,
                unit="seconds",
                status="critical",
                details={"error": str(e)}
            )
    
    def measure_memory_usage(self) -> HealthMetric:
        """Measure system memory usage."""
        try:
            import psutil
            
            memory = psutil.virtual_memory()
            usage_percent = memory.percent
            
            # Determine status
            if usage_percent < self.thresholds["memory_usage"]["warning"]:
                status = "healthy"
            elif usage_percent < self.thresholds["memory_usage"]["critical"]:
                status = "warning"
            else:
                status = "critical"
            
            return HealthMetric(
                timestamp=datetime.now().isoformat(),
                metric_name="memory_usage",
                value=usage_percent,
                unit="percent",
                status=status,
                details={
                    "total_gb": round(memory.total / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "used_gb": round(memory.used / (1024**3), 2)
                }
            )
            
        except ImportError:
            return HealthMetric(
                timestamp=datetime.now().isoformat(),
                metric_name="memory_usage",
                value=-1,
                unit="percent",
                status="warning",
                details={"error": "psutil not available for memory monitoring"}
            )
        except Exception as e:
            return HealthMetric(
                timestamp=datetime.now().isoformat(),
                metric_name="memory_usage",
                value=-1,
                unit="percent",
                status="critical",
                details={"error": str(e)}
            )
    
    def calculate_error_rate(self, time_window_hours: int = 24) -> HealthMetric:
        """Calculate error rate from recent metrics."""
        try:
            if not self.metrics_file.exists():
                return HealthMetric(
                    timestamp=datetime.now().isoformat(),
                    metric_name="error_rate",
                    value=0.0,
                    unit="ratio",
                    status="healthy",
                    details={"note": "No historical data available"}
                )
            
            # Load recent metrics
            with open(self.metrics_file, 'r') as f:
                historical_data = json.load(f)
            
            # Filter metrics from the last time window
            cutoff_time = datetime.now() - timedelta(hours=time_window_hours)
            recent_metrics = []
            
            for entry in historical_data:
                if 'metrics' in entry:
                    for metric in entry['metrics']:
                        metric_time = datetime.fromisoformat(metric['timestamp'])
                        if metric_time > cutoff_time:
                            recent_metrics.append(metric)
            
            if not recent_metrics:
                error_rate = 0.0
            else:
                error_count = sum(1 for m in recent_metrics if m['status'] == 'critical')
                error_rate = error_count / len(recent_metrics)
            
            # Determine status
            if error_rate < self.thresholds["error_rate"]["warning"]:
                status = "healthy"
            elif error_rate < self.thresholds["error_rate"]["critical"]:
                status = "warning"
            else:
                status = "critical"
            
            return HealthMetric(
                timestamp=datetime.now().isoformat(),
                metric_name="error_rate",
                value=error_rate,
                unit="ratio",
                status=status,
                details={
                    "time_window_hours": time_window_hours,
                    "total_metrics": len(recent_metrics),
                    "error_count": sum(1 for m in recent_metrics if m['status'] == 'critical')
                }
            )
            
        except Exception as e:
            return HealthMetric(
                timestamp=datetime.now().isoformat(),
                metric_name="error_rate",
                value=-1,
                unit="ratio",
                status="warning",
                details={"error": str(e)}
            )
    
    async def collect_all_metrics(self) -> List[HealthMetric]:
        """Collect all health metrics."""
        print("📊 Collecting health metrics...")
        
        metrics = []
        
        # Async metrics
        async_metrics = await asyncio.gather(
            self.measure_embedding_performance(),
            self.measure_database_performance(),
            return_exceptions=True
        )
        
        for metric in async_metrics:
            if isinstance(metric, HealthMetric):
                metrics.append(metric)
            else:
                print(f"⚠️  Error collecting async metric: {metric}")
        
        # Sync metrics
        metrics.append(self.measure_memory_usage())
        metrics.append(self.calculate_error_rate())
        
        return metrics
    
    def determine_overall_status(self, metrics: List[HealthMetric]) -> str:
        """Determine overall system health status."""
        statuses = [m.status for m in metrics if m.value >= 0]  # Exclude error metrics
        
        if "critical" in statuses:
            return "critical"
        elif "warning" in statuses:
            return "warning"
        else:
            return "healthy"
    
    def generate_summary(self, metrics: List[HealthMetric]) -> Dict[str, Any]:
        """Generate health summary statistics."""
        summary = {
            "total_metrics": len(metrics),
            "healthy_count": sum(1 for m in metrics if m.status == "healthy"),
            "warning_count": sum(1 for m in metrics if m.status == "warning"),
            "critical_count": sum(1 for m in metrics if m.status == "critical"),
            "metrics_by_type": {}
        }
        
        # Group metrics by type
        for metric in metrics:
            if metric.value >= 0:  # Valid metrics only
                summary["metrics_by_type"][metric.metric_name] = {
                    "value": metric.value,
                    "unit": metric.unit,
                    "status": metric.status
                }
        
        return summary
    
    def save_health_data(self, health: SystemHealth):
        """Save health data to file."""
        try:
            # Load existing data
            historical_data = []
            if self.metrics_file.exists():
                with open(self.metrics_file, 'r') as f:
                    historical_data = json.load(f)
            
            # Add new data
            historical_data.append(asdict(health))
            
            # Keep only last 1000 entries to prevent file from growing too large
            if len(historical_data) > 1000:
                historical_data = historical_data[-1000:]
            
            # Save updated data
            with open(self.metrics_file, 'w') as f:
                json.dump(historical_data, f, indent=2)
            
            print(f"💾 Health data saved to {self.metrics_file}")
            
        except Exception as e:
            print(f"❌ Error saving health data: {e}")
    
    def display_health_report(self, health: SystemHealth):
        """Display formatted health report."""
        print("\n" + "=" * 50)
        print("🏥 SYSTEM HEALTH REPORT")
        print("=" * 50)
        print(f"Timestamp: {health.timestamp}")
        print(f"Overall Status: {self.format_status(health.overall_status)}")
        print()
        
        print("📊 Metrics:")
        for metric in health.metrics:
            status_icon = self.get_status_icon(metric.status)
            if metric.value >= 0:
                print(f"  {status_icon} {metric.metric_name}: {metric.value:.3f} {metric.unit}")
            else:
                print(f"  {status_icon} {metric.metric_name}: ERROR")
            
            if metric.details:
                for key, value in metric.details.items():
                    if key != "error":
                        print(f"      {key}: {value}")
        
        print(f"\n📈 Summary:")
        print(f"  Total Metrics: {health.summary['total_metrics']}")
        print(f"  Healthy: {health.summary['healthy_count']}")
        print(f"  Warnings: {health.summary['warning_count']}")
        print(f"  Critical: {health.summary['critical_count']}")
    
    def format_status(self, status: str) -> str:
        """Format status with appropriate emoji."""
        status_map = {
            "healthy": "🟢 HEALTHY",
            "warning": "🟡 WARNING", 
            "critical": "🔴 CRITICAL"
        }
        return status_map.get(status, f"❓ {status.upper()}")
    
    def get_status_icon(self, status: str) -> str:
        """Get status icon."""
        icons = {
            "healthy": "✅",
            "warning": "⚠️",
            "critical": "❌"
        }
        return icons.get(status, "❓")
    
    async def run_health_check(self) -> SystemHealth:
        """Run complete health check."""
        print("🏥 Starting system health check...")
        
        # Collect metrics
        metrics = await self.collect_all_metrics()
        
        # Determine overall status
        overall_status = self.determine_overall_status(metrics)
        
        # Generate summary
        summary = self.generate_summary(metrics)
        
        # Create health object
        health = SystemHealth(
            timestamp=datetime.now().isoformat(),
            overall_status=overall_status,
            metrics=metrics,
            summary=summary
        )
        
        return health


async def main():
    """Main monitoring function."""
    monitor = HealthMonitor()
    
    try:
        # Run health check
        health = await monitor.run_health_check()
        
        # Display report
        monitor.display_health_report(health)
        
        # Save data
        monitor.save_health_data(health)
        
        # Return appropriate exit code
        if health.overall_status == "critical":
            return 2
        elif health.overall_status == "warning":
            return 1
        else:
            return 0
            
    except KeyboardInterrupt:
        print("\n⏹️  Health check interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Health check failed: {e}")
        return 1


if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
