import uuid
import enum
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text,
    ForeignKey, Enum as SAEnum, Index, JSON,
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    FAILOVER = "failover"


class JobType(str, enum.Enum):
    TRAINING = "training"
    INFERENCE = "inference"
    BATCH = "batch"
    FINE_TUNING = "fine_tuning"


class GPUType(str, enum.Enum):
    A100_40GB = "A100-40GB"
    A100_80GB = "A100-80GB"
    V100_16GB = "V100-16GB"
    V100_32GB = "V100-32GB"
    T4_16GB = "T4-16GB"
    A10G_24GB = "A10G-24GB"
    ANY = "any"


class InstanceStatus(str, enum.Enum):
    AVAILABLE = "available"
    ALLOCATED = "allocated"
    MAINTENANCE = "maintenance"
    TERMINATED = "terminated"


class CloudProvider(str, enum.Enum):
    AWS = "aws"
    GCP = "gcp"
    AZURE = "azure"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    api_key = Column(String(64), unique=True, nullable=False, index=True)
    budget_limit = Column(Float, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    jobs = relationship("Job", back_populates="user")
    billing_records = relationship("BillingRecord", back_populates="user")


class GPUInstance(Base):
    __tablename__ = "gpu_instances"

    id = Column(String(128), primary_key=True)
    provider = Column(SAEnum(CloudProvider), nullable=False, index=True)
    region = Column(String(64), nullable=False, index=True)
    zone = Column(String(64), nullable=True)
    instance_type = Column(String(64), nullable=False)
    gpu_type = Column(SAEnum(GPUType), nullable=False, index=True)
    gpu_count = Column(Integer, nullable=False)
    gpu_memory_gb = Column(Integer, nullable=False)
    cpu_count = Column(Integer, nullable=False)
    memory_gb = Column(Integer, nullable=False)
    status = Column(SAEnum(InstanceStatus), default=InstanceStatus.AVAILABLE, index=True)
    is_spot = Column(Boolean, default=False)
    on_demand_price_hour = Column(Float, nullable=False)
    spot_price_hour = Column(Float, nullable=True)
    allocated_gpu_count = Column(Integer, default=0)
    last_seen = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    allocations = relationship("Job", back_populates="instance")

    __table_args__ = (
        Index("idx_gpu_instances_provider_region_status", "provider", "region", "status"),
        Index("idx_gpu_instances_gpu_type_status", "gpu_type", "status"),
    )


class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    model = Column(String(255), nullable=True)
    job_type = Column(SAEnum(JobType), nullable=False, default=JobType.TRAINING)
    status = Column(SAEnum(JobStatus), nullable=False, default=JobStatus.QUEUED, index=True)
    priority = Column(Integer, default=5, nullable=False)
    gpu_type = Column(SAEnum(GPUType), nullable=True)
    gpu_count = Column(Integer, nullable=False, default=1)
    gpu_memory_gb = Column(Integer, nullable=True)
    preferred_regions = Column(ARRAY(String), nullable=True)
    excluded_regions = Column(ARRAY(String), nullable=True)
    budget = Column(Float, nullable=True)
    sla_deadline = Column(DateTime(timezone=True), nullable=True)
    use_spot = Column(Boolean, default=True)
    instance_id = Column(String(128), ForeignKey("gpu_instances.id"), nullable=True, index=True)
    estimated_duration_hours = Column(Float, nullable=True)
    allocated_at = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    actual_cost = Column(Float, nullable=True)
    estimated_cost = Column(Float, nullable=True)
    retry_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    job_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="jobs")
    instance = relationship("GPUInstance", back_populates="allocations")
    metrics = relationship("JobMetric", back_populates="job", cascade="all, delete-orphan")
    billing_records = relationship("BillingRecord", back_populates="job")
    sla_violations = relationship("SLAViolation", back_populates="job")

    __table_args__ = (
        Index("idx_jobs_status_priority", "status", "priority"),
        Index("idx_jobs_created_at", "created_at"),
    )


class JobMetric(Base):
    __tablename__ = "job_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    gpu_utilization = Column(Float, nullable=True)
    gpu_memory_used_gb = Column(Float, nullable=True)
    gpu_memory_total_gb = Column(Float, nullable=True)
    cpu_utilization = Column(Float, nullable=True)
    memory_used_gb = Column(Float, nullable=True)
    throughput = Column(Float, nullable=True)
    cost_so_far = Column(Float, nullable=True)

    job = relationship("Job", back_populates="metrics")


class BillingRecord(Base):
    __tablename__ = "billing_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    instance_id = Column(String(128), nullable=True)
    provider = Column(SAEnum(CloudProvider), nullable=False)
    region = Column(String(64), nullable=False)
    gpu_type = Column(SAEnum(GPUType), nullable=False)
    duration_seconds = Column(Integer, nullable=False)
    price_per_hour = Column(Float, nullable=False)
    total_cost = Column(Float, nullable=False)
    is_spot = Column(Boolean, default=False)
    on_demand_equivalent_cost = Column(Float, nullable=True)
    savings = Column(Float, nullable=True)
    billing_period_start = Column(DateTime(timezone=True), nullable=True)
    billing_period_end = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    job = relationship("Job", back_populates="billing_records")
    user = relationship("User", back_populates="billing_records")


class SLAViolation(Base):
    __tablename__ = "sla_violations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False, index=True)
    violation_type = Column(String(64), nullable=False)
    severity = Column(String(16), nullable=False, default="warning")
    details = Column(Text, nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    job = relationship("Job", back_populates="sla_violations")
