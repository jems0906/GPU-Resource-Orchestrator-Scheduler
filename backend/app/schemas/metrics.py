from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime


class GPUUtilizationPoint(BaseModel):
    timestamp: datetime
    provider: str
    region: str
    gpu_type: str
    utilization_percent: float
    memory_used_gb: float
    memory_total_gb: float


class CostDataPoint(BaseModel):
    date: str
    provider: str
    cost: float
    spot_cost: float
    on_demand_cost: float
    savings: float


class QueueMetrics(BaseModel):
    total_queued: int
    total_running: int
    total_completed_today: int
    total_failed_today: int
    average_wait_time_minutes: float
    average_run_time_minutes: float
    jobs_by_status: Dict[str, int]
    jobs_by_priority: Dict[str, int]


class SLAMetrics(BaseModel):
    total_jobs_with_sla: int
    sla_compliant: int
    sla_violated: int
    sla_at_risk: int
    compliance_percent: float
    active_violations: List[Dict]


class CostSummary(BaseModel):
    total_cost_today: float
    total_cost_this_month: float
    total_cost_all_time: float
    total_savings_from_spot: float
    savings_percent: float
    cost_by_provider: Dict[str, float]
    cost_by_gpu_type: Dict[str, float]
    average_cost_per_job: float


class DashboardMetrics(BaseModel):
    queue: QueueMetrics
    sla: SLAMetrics
    cost: CostSummary
    gpu_utilization: List[GPUUtilizationPoint]
    active_jobs_count: int
    total_gpus_available: int
    total_gpus_in_use: int
    timestamp: datetime
