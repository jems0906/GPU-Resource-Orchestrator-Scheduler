from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


class JobCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    model: Optional[str] = None
    job_type: str = Field(default="training")
    priority: int = Field(default=5, ge=1, le=10)
    gpu_type: Optional[str] = None
    gpu_count: int = Field(default=1, ge=1, le=64)
    gpu_memory_gb: Optional[int] = Field(default=None, ge=1)
    preferred_regions: Optional[List[str]] = None
    excluded_regions: Optional[List[str]] = None
    budget: Optional[float] = Field(default=None, ge=0)
    sla_deadline: Optional[datetime] = None
    use_spot: bool = True
    estimated_duration_hours: Optional[float] = Field(default=None, ge=0)
    job_metadata: Optional[Dict[str, Any]] = None


class JobUpdate(BaseModel):
    priority: Optional[int] = Field(default=None, ge=1, le=10)
    budget: Optional[float] = Field(default=None, ge=0)
    sla_deadline: Optional[datetime] = None


class JobScaleRequest(BaseModel):
    gpu_count: int = Field(..., ge=1, le=64)
    reason: Optional[str] = None


class GPUInstanceBrief(BaseModel):
    id: str
    provider: str
    region: str
    instance_type: str
    gpu_type: str
    gpu_count: int
    gpu_memory_gb: int
    is_spot: bool
    price_per_hour: float

    model_config = {"from_attributes": True}


class JobMetricResponse(BaseModel):
    timestamp: datetime
    gpu_utilization: Optional[float] = None
    gpu_memory_used_gb: Optional[float] = None
    gpu_memory_total_gb: Optional[float] = None
    cpu_utilization: Optional[float] = None
    throughput: Optional[float] = None
    cost_so_far: Optional[float] = None

    model_config = {"from_attributes": True}


class JobResponse(BaseModel):
    id: UUID
    name: str
    model: Optional[str] = None
    job_type: str
    status: str
    priority: int
    gpu_type: Optional[str] = None
    gpu_count: int
    gpu_memory_gb: Optional[int] = None
    preferred_regions: Optional[List[str]] = None
    budget: Optional[float] = None
    sla_deadline: Optional[datetime] = None
    use_spot: bool
    instance: Optional[GPUInstanceBrief] = None
    estimated_cost: Optional[float] = None
    actual_cost: Optional[float] = None
    estimated_duration_hours: Optional[float] = None
    retry_count: int
    error_message: Optional[str] = None
    job_metadata: Optional[Dict[str, Any]] = None
    allocated_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class JobListResponse(BaseModel):
    jobs: List[JobResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class JobCancelResponse(BaseModel):
    job_id: str
    status: str
    message: str
