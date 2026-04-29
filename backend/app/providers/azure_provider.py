"""
Azure Provider — Mock implementation with realistic Azure VM GPU instance data.

In production, replace mock methods with azure-mgmt-compute calls:
  - list_available_instances  → ComputeManagementClient().virtual_machines.list()
  - provision_instance        → ComputeManagementClient().virtual_machines.begin_create_or_update()
  - terminate_instance        → ComputeManagementClient().virtual_machines.begin_delete()
  - get_gpu_metrics           → MonitorManagementClient().metrics.list()
  - get_spot_price            → RetailPrices API
"""

import uuid
import random
from typing import List, Optional, Dict

from app.providers.base import CloudProviderBase, GPUInstanceInfo, JobExecutionResult, GPUMetrics

AZURE_GPU_CATALOG = [
    {
        "instance_type": "Standard_ND96asr_v4",
        "gpu_type": "A100-40GB",
        "gpu_count": 8,
        "gpu_memory_gb": 40,
        "cpu_count": 96,
        "memory_gb": 900,
        "on_demand_price_hour": 27.20,
        "spot_discount": 0.32,
    },
    {
        "instance_type": "Standard_NC24ads_A100_v4",
        "gpu_type": "A100-80GB",
        "gpu_count": 1,
        "gpu_memory_gb": 80,
        "cpu_count": 24,
        "memory_gb": 220,
        "on_demand_price_hour": 3.40,
        "spot_discount": 0.30,
    },
    {
        "instance_type": "Standard_ND40rs_v2",
        "gpu_type": "V100-32GB",
        "gpu_count": 8,
        "gpu_memory_gb": 32,
        "cpu_count": 40,
        "memory_gb": 672,
        "on_demand_price_hour": 22.03,
        "spot_discount": 0.27,
    },
    {
        "instance_type": "Standard_NC6s_v3",
        "gpu_type": "V100-16GB",
        "gpu_count": 1,
        "gpu_memory_gb": 16,
        "cpu_count": 6,
        "memory_gb": 112,
        "on_demand_price_hour": 3.06,
        "spot_discount": 0.27,
    },
    {
        "instance_type": "Standard_NC4as_T4_v3",
        "gpu_type": "T4-16GB",
        "gpu_count": 1,
        "gpu_memory_gb": 16,
        "cpu_count": 4,
        "memory_gb": 28,
        "on_demand_price_hour": 0.526,
        "spot_discount": 0.42,
    },
    {
        "instance_type": "Standard_NC64as_T4_v3",
        "gpu_type": "T4-16GB",
        "gpu_count": 4,
        "gpu_memory_gb": 16,
        "cpu_count": 64,
        "memory_gb": 440,
        "on_demand_price_hour": 4.352,
        "spot_discount": 0.42,
    },
]

AZURE_REGIONS = ["eastus", "westus2", "westeurope"]


class AzureProvider(CloudProviderBase):
    def __init__(self, regions: List[str] = None):
        super().__init__("azure", regions or AZURE_REGIONS)
        self._instances: Dict[str, GPUInstanceInfo] = {}
        self._initialized = False

    async def _initialize(self) -> None:
        if self._initialized:
            return
        rng = random.Random(77)
        for region in self.regions:
            region_factor = 3 if region == "eastus" else 2
            for item in AZURE_GPU_CATALOG:
                count = rng.randint(1, region_factor + 1)
                for i in range(count):
                    instance_id = f"azure-{region}-{uuid.uuid4().hex[:12]}"
                    spot_price = round(item["on_demand_price_hour"] * item["spot_discount"], 4)
                    inst = GPUInstanceInfo(
                        id=instance_id,
                        provider="azure",
                        region=region,
                        zone=f"{region}-{i + 1}",
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
                    external_job_id=f"azure-job-{uuid.uuid4().hex[:8]}",
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
            gpu_utilization=random.uniform(58, 96),
            gpu_memory_used_gb=inst.gpu_memory_gb * random.uniform(0.48, 0.91),
            gpu_memory_total_gb=float(inst.gpu_memory_gb),
            cpu_utilization=random.uniform(22, 78),
            memory_used_gb=inst.memory_gb * random.uniform(0.28, 0.72),
            throughput=random.uniform(180, 1900),
        )

    async def check_spot_availability(self, instance_type: str, region: str) -> bool:
        return random.random() > 0.10

    async def get_spot_price(self, instance_type: str, region: str) -> Optional[float]:
        await self._initialize()
        for item in AZURE_GPU_CATALOG:
            if item["instance_type"] == instance_type:
                base = item["on_demand_price_hour"] * item["spot_discount"]
                return round(base * random.uniform(0.85, 1.15), 4)
        return None
