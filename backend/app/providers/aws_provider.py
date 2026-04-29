"""
AWS Provider — Mock implementation with realistic EC2 GPU instance data.

In production, replace mock methods with boto3 calls:
  - list_available_instances  → ec2.describe_instances(Filters=[...])
  - provision_instance        → ec2.run_instances() / request_spot_instances()
  - terminate_instance        → ec2.terminate_instances()
  - get_gpu_metrics           → cloudwatch.get_metric_data()
  - get_spot_price            → ec2.describe_spot_price_history()
"""

import uuid
import random
from typing import List, Optional, Dict
from datetime import datetime

from app.providers.base import CloudProviderBase, GPUInstanceInfo, JobExecutionResult, GPUMetrics

# Realistic AWS GPU instance catalog with 2025 pricing
AWS_GPU_CATALOG = [
    {
        "instance_type": "p4d.24xlarge",
        "gpu_type": "A100-40GB",
        "gpu_count": 8,
        "gpu_memory_gb": 40,
        "cpu_count": 96,
        "memory_gb": 1152,
        "on_demand_price_hour": 32.7726,
        "spot_discount": 0.35,
    },
    {
        "instance_type": "p3.16xlarge",
        "gpu_type": "V100-16GB",
        "gpu_count": 8,
        "gpu_memory_gb": 16,
        "cpu_count": 64,
        "memory_gb": 488,
        "on_demand_price_hour": 24.48,
        "spot_discount": 0.28,
    },
    {
        "instance_type": "p3.8xlarge",
        "gpu_type": "V100-16GB",
        "gpu_count": 4,
        "gpu_memory_gb": 16,
        "cpu_count": 32,
        "memory_gb": 244,
        "on_demand_price_hour": 12.24,
        "spot_discount": 0.28,
    },
    {
        "instance_type": "p3.2xlarge",
        "gpu_type": "V100-16GB",
        "gpu_count": 1,
        "gpu_memory_gb": 16,
        "cpu_count": 8,
        "memory_gb": 61,
        "on_demand_price_hour": 3.06,
        "spot_discount": 0.28,
    },
    {
        "instance_type": "g4dn.12xlarge",
        "gpu_type": "T4-16GB",
        "gpu_count": 4,
        "gpu_memory_gb": 16,
        "cpu_count": 48,
        "memory_gb": 192,
        "on_demand_price_hour": 3.912,
        "spot_discount": 0.40,
    },
    {
        "instance_type": "g4dn.xlarge",
        "gpu_type": "T4-16GB",
        "gpu_count": 1,
        "gpu_memory_gb": 16,
        "cpu_count": 4,
        "memory_gb": 16,
        "on_demand_price_hour": 0.526,
        "spot_discount": 0.40,
    },
    {
        "instance_type": "g5.48xlarge",
        "gpu_type": "A10G-24GB",
        "gpu_count": 8,
        "gpu_memory_gb": 24,
        "cpu_count": 192,
        "memory_gb": 768,
        "on_demand_price_hour": 16.288,
        "spot_discount": 0.45,
    },
    {
        "instance_type": "g5.4xlarge",
        "gpu_type": "A10G-24GB",
        "gpu_count": 1,
        "gpu_memory_gb": 24,
        "cpu_count": 16,
        "memory_gb": 64,
        "on_demand_price_hour": 1.624,
        "spot_discount": 0.45,
    },
]

AWS_REGIONS = ["us-east-1", "us-west-2", "eu-west-1"]


class AWSProvider(CloudProviderBase):
    def __init__(self, regions: List[str] = None):
        super().__init__("aws", regions or AWS_REGIONS)
        self._instances: Dict[str, GPUInstanceInfo] = {}
        self._initialized = False

    async def _initialize(self) -> None:
        if self._initialized:
            return
        rng = random.Random(42)  # deterministic seed for reproducibility
        for region in self.regions:
            region_factor = 3 if region == "us-east-1" else 2 if region == "us-west-2" else 1
            for item in AWS_GPU_CATALOG:
                count = rng.randint(1, region_factor + 2)
                for i in range(count):
                    instance_id = f"i-{uuid.uuid4().hex[:17]}"
                    spot_price = round(item["on_demand_price_hour"] * item["spot_discount"], 4)
                    inst = GPUInstanceInfo(
                        id=instance_id,
                        provider="aws",
                        region=region,
                        zone=f"{region}{'abc'[i % 3]}",
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
                    external_job_id=f"aws-job-{uuid.uuid4().hex[:8]}",
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
            gpu_utilization=random.uniform(55, 99),
            gpu_memory_used_gb=inst.gpu_memory_gb * random.uniform(0.5, 0.92),
            gpu_memory_total_gb=float(inst.gpu_memory_gb),
            cpu_utilization=random.uniform(20, 85),
            memory_used_gb=inst.memory_gb * random.uniform(0.3, 0.75),
            throughput=random.uniform(200, 2000),
        )

    async def check_spot_availability(self, instance_type: str, region: str) -> bool:
        return random.random() > 0.08

    async def get_spot_price(self, instance_type: str, region: str) -> Optional[float]:
        await self._initialize()
        for item in AWS_GPU_CATALOG:
            if item["instance_type"] == instance_type:
                base = item["on_demand_price_hour"] * item["spot_discount"]
                return round(base * random.uniform(0.9, 1.1), 4)
        return None
