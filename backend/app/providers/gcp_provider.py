"""
GCP Provider — Mock implementation with realistic Compute Engine GPU instance data.

In production, replace mock methods with google-cloud-compute calls:
  - list_available_instances  → compute_v1.InstancesClient().list()
  - provision_instance        → compute_v1.InstancesClient().insert()
  - terminate_instance        → compute_v1.InstancesClient().delete()
  - get_gpu_metrics           → monitoring_v3.MetricServiceClient()
  - get_spot_price            → cloudbilling API
"""

import uuid
import random
from typing import List, Optional, Dict
from datetime import datetime

from app.providers.base import CloudProviderBase, GPUInstanceInfo, JobExecutionResult, GPUMetrics

GCP_GPU_CATALOG = [
    {
        "instance_type": "a2-highgpu-8g",
        "gpu_type": "A100-40GB",
        "gpu_count": 8,
        "gpu_memory_gb": 40,
        "cpu_count": 96,
        "memory_gb": 680,
        "on_demand_price_hour": 29.39,
        "spot_discount": 0.33,
    },
    {
        "instance_type": "a2-highgpu-4g",
        "gpu_type": "A100-40GB",
        "gpu_count": 4,
        "gpu_memory_gb": 40,
        "cpu_count": 48,
        "memory_gb": 340,
        "on_demand_price_hour": 14.69,
        "spot_discount": 0.33,
    },
    {
        "instance_type": "a2-highgpu-1g",
        "gpu_type": "A100-40GB",
        "gpu_count": 1,
        "gpu_memory_gb": 40,
        "cpu_count": 12,
        "memory_gb": 85,
        "on_demand_price_hour": 3.67,
        "spot_discount": 0.33,
    },
    {
        "instance_type": "n1-standard-8-v100",
        "gpu_type": "V100-16GB",
        "gpu_count": 1,
        "gpu_memory_gb": 16,
        "cpu_count": 8,
        "memory_gb": 30,
        "on_demand_price_hour": 2.955,
        "spot_discount": 0.30,
    },
    {
        "instance_type": "n1-standard-4-t4",
        "gpu_type": "T4-16GB",
        "gpu_count": 1,
        "gpu_memory_gb": 16,
        "cpu_count": 4,
        "memory_gb": 15,
        "on_demand_price_hour": 0.95,
        "spot_discount": 0.38,
    },
    {
        "instance_type": "n1-standard-16-t4x4",
        "gpu_type": "T4-16GB",
        "gpu_count": 4,
        "gpu_memory_gb": 16,
        "cpu_count": 16,
        "memory_gb": 60,
        "on_demand_price_hour": 3.80,
        "spot_discount": 0.38,
    },
]

GCP_REGIONS = ["us-central1", "us-east1", "europe-west4"]


class GCPProvider(CloudProviderBase):
    def __init__(self, regions: List[str] = None):
        super().__init__("gcp", regions or GCP_REGIONS)
        self._instances: Dict[str, GPUInstanceInfo] = {}
        self._initialized = False

    async def _initialize(self) -> None:
        if self._initialized:
            return
        rng = random.Random(99)
        for region in self.regions:
            region_factor = 3 if region == "us-central1" else 2
            for item in GCP_GPU_CATALOG:
                count = rng.randint(1, region_factor + 1)
                for i in range(count):
                    instance_id = f"gcp-{region}-{uuid.uuid4().hex[:12]}"
                    spot_price = round(item["on_demand_price_hour"] * item["spot_discount"], 4)
                    zones = ["a", "b", "c", "f"]
                    inst = GPUInstanceInfo(
                        id=instance_id,
                        provider="gcp",
                        region=region,
                        zone=f"{region}-{zones[i % len(zones)]}",
                        instance_type=item["instance_type"],
                        gpu_type=item["gpu_type"],
                        gpu_count=item["gpu_count"],
                        gpu_memory_gb=item["gpu_memory_gb"],
                        cpu_count=item["cpu_count"],
                        memory_gb=item["memory_gb"],
                        is_spot=False,
                        on_demand_price_hour=item["on_demand_price_hour"],
                        spot_price_hour=spot_price,
                        status="available",
                    )
                    self._instances[instance_id] = inst
        self._initialized = True

    async def list_available_instances(self, region: Optional[str] = None) -> List[GPUInstanceInfo]:
        await self._initialize()
        instances = list(self._instances.values())
        if region:
            instances = [i for i in instances if i.region == region]
        return [i for i in instances if i.status == "available"]

    async def provision_instance(
        self,
        instance_type: str,
        region: str,
        is_spot: bool = False,
        **kwargs,
    ) -> JobExecutionResult:
        await self._initialize()
        for inst in self._instances.values():
            if (
                inst.instance_type == instance_type
                and inst.region == region
                and inst.status == "available"
            ):
                inst.status = "allocated"
                inst.is_spot = is_spot
                return JobExecutionResult(
                    success=True,
                    instance_id=inst.id,
                    external_job_id=f"gcp-job-{uuid.uuid4().hex[:8]}",
                )
        return JobExecutionResult(
            success=False,
            error=f"No available {instance_type} in {region}",
        )

    async def terminate_instance(self, instance_id: str, region: str) -> bool:
        await self._initialize()
        if instance_id in self._instances:
            self._instances[instance_id].status = "available"
            self._instances[instance_id].is_spot = False
            return True
        return False

    async def get_gpu_metrics(self, instance_id: str) -> Optional[GPUMetrics]:
        await self._initialize()
        inst = self._instances.get(instance_id)
        if not inst:
            return None
        return GPUMetrics(
            job_id="",
            instance_id=instance_id,
            gpu_utilization=random.uniform(60, 97),
            gpu_memory_used_gb=inst.gpu_memory_gb * random.uniform(0.5, 0.9),
            gpu_memory_total_gb=float(inst.gpu_memory_gb),
            cpu_utilization=random.uniform(25, 80),
            memory_used_gb=inst.memory_gb * random.uniform(0.3, 0.7),
            throughput=random.uniform(150, 1800),
        )

    async def check_spot_availability(self, instance_type: str, region: str) -> bool:
        return random.random() > 0.12

    async def get_spot_price(self, instance_type: str, region: str) -> Optional[float]:
        await self._initialize()
        for item in GCP_GPU_CATALOG:
            if item["instance_type"] == instance_type:
                base = item["on_demand_price_hour"] * item["spot_discount"]
                return round(base * random.uniform(0.88, 1.12), 4)
        return None
