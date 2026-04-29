from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime


class GPUInstanceSchema(BaseModel):
    id: str
    provider: str
    region: str
    zone: Optional[str] = None
    instance_type: str
    gpu_type: str
    gpu_count: int
    gpu_memory_gb: int
    cpu_count: int
    memory_gb: int
    status: str
    is_spot: bool
    on_demand_price_hour: float
    spot_price_hour: Optional[float] = None
    allocated_gpu_count: int = 0
    last_seen: Optional[datetime] = None

    model_config = {"from_attributes": True}

    @property
    def available_gpu_count(self) -> int:
        return self.gpu_count - self.allocated_gpu_count

    @property
    def current_price_hour(self) -> float:
        if self.is_spot and self.spot_price_hour:
            return self.spot_price_hour
        return self.on_demand_price_hour


class ProviderSummary(BaseModel):
    provider: str
    total_instances: int
    available_instances: int
    allocated_instances: int
    total_gpus: int
    available_gpus: int
    regions: List[str]
    gpu_types: Dict[str, int]
    estimated_hourly_cost_if_full: float


class InventoryResponse(BaseModel):
    providers: List[ProviderSummary]
    total_instances: int
    total_available_gpus: int
    instances: List[GPUInstanceSchema]
    last_updated: datetime


class PricingInfo(BaseModel):
    provider: str
    region: str
    instance_type: str
    gpu_type: str
    gpu_count: int
    on_demand_price_hour: float
    spot_price_hour: Optional[float] = None
    spot_savings_percent: Optional[float] = None
