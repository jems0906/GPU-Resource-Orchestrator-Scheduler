from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class GPUInstanceInfo:
    """Represents a GPU instance from a cloud provider."""
    id: str
    provider: str
    region: str
    zone: Optional[str]
    instance_type: str
    gpu_type: str
    gpu_count: int
    gpu_memory_gb: int
    cpu_count: int
    memory_gb: int
    is_spot: bool
    on_demand_price_hour: float
    spot_price_hour: Optional[float] = None
    status: str = "available"
    metadata: Dict[str, Any] = field(default_factory=dict)
    last_seen: datetime = field(default_factory=datetime.utcnow)

    @property
    def current_price_hour(self) -> float:
        if self.is_spot and self.spot_price_hour is not None:
            return self.spot_price_hour
        return self.on_demand_price_hour


@dataclass
class JobExecutionResult:
    """Result of submitting a job to a cloud provider."""
    success: bool
    instance_id: Optional[str] = None
    external_job_id: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GPUMetrics:
    """Real-time GPU metrics from a running job."""
    job_id: str
    instance_id: str
    gpu_utilization: float
    gpu_memory_used_gb: float
    gpu_memory_total_gb: float
    cpu_utilization: float
    memory_used_gb: float
    throughput: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


class CloudProviderBase(ABC):
    """Abstract base class for cloud provider integrations."""

    def __init__(self, provider: str, regions: List[str]):
        self.provider = provider
        self.regions = regions

    @abstractmethod
    async def list_available_instances(self, region: Optional[str] = None) -> List[GPUInstanceInfo]:
        """List all available GPU instances. In production: query cloud provider API."""
        pass

    @abstractmethod
    async def provision_instance(
        self,
        instance_type: str,
        region: str,
        is_spot: bool = False,
        **kwargs,
    ) -> JobExecutionResult:
        """Provision a GPU instance. In production: call cloud provider launch API."""
        pass

    @abstractmethod
    async def terminate_instance(self, instance_id: str, region: str) -> bool:
        """Terminate a GPU instance. In production: call cloud provider terminate API."""
        pass

    @abstractmethod
    async def get_gpu_metrics(self, instance_id: str) -> Optional[GPUMetrics]:
        """Get current GPU metrics. In production: query monitoring APIs (CloudWatch, etc.)."""
        pass

    @abstractmethod
    async def check_spot_availability(self, instance_type: str, region: str) -> bool:
        """Check spot instance availability."""
        pass

    @abstractmethod
    async def get_spot_price(self, instance_type: str, region: str) -> Optional[float]:
        """Get current spot price for an instance type."""
        pass

    async def health_check(self) -> bool:
        """Verify provider API is reachable."""
        try:
            await self.list_available_instances()
            return True
        except Exception:
            return False
