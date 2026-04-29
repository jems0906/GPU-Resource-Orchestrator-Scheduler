"""Jobs API — submit, query, cancel, and scale GPU workloads."""

import math
import uuid
from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, inspect
from sqlalchemy.orm import joinedload

from app.api.deps import require_auth
from app.db.session import get_db
from app.db.models import Job, JobStatus, JobType, GPUType, GPUInstance, JobMetric, User
from app.schemas.job import (
    JobCreate, JobUpdate, JobScaleRequest, JobResponse,
    JobListResponse, JobMetricResponse, JobCancelResponse,
)
from app.queue.redis_queue import redis_queue

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _job_to_response(job: Job) -> JobResponse:
    instance_brief = None
    state = inspect(job)
    instance_is_loaded = "instance" not in state.unloaded

    if instance_is_loaded and job.instance:
        inst = job.instance
        price = (
            inst.spot_price_hour
            if (job.use_spot and inst.spot_price_hour)
            else inst.on_demand_price_hour
        )
        from app.schemas.job import GPUInstanceBrief
        instance_brief = GPUInstanceBrief(
            id=inst.id,
            provider=str(inst.provider.value) if hasattr(inst.provider, "value") else str(inst.provider),
            region=inst.region,
            instance_type=inst.instance_type,
            gpu_type=str(inst.gpu_type.value) if hasattr(inst.gpu_type, "value") else str(inst.gpu_type),
            gpu_count=inst.gpu_count,
            gpu_memory_gb=inst.gpu_memory_gb,
            is_spot=inst.is_spot,
            price_per_hour=price,
        )

    return JobResponse(
        id=job.id,
        name=job.name,
        model=job.model,
        job_type=str(job.job_type.value) if hasattr(job.job_type, "value") else str(job.job_type),
        status=str(job.status.value) if hasattr(job.status, "value") else str(job.status),
        priority=job.priority,
        gpu_type=str(job.gpu_type.value) if (job.gpu_type and hasattr(job.gpu_type, "value")) else str(job.gpu_type) if job.gpu_type else None,
        gpu_count=job.gpu_count,
        gpu_memory_gb=job.gpu_memory_gb,
        preferred_regions=job.preferred_regions,
        budget=job.budget,
        sla_deadline=job.sla_deadline,
        use_spot=job.use_spot,
        instance=instance_brief,
        estimated_cost=job.estimated_cost,
        actual_cost=job.actual_cost,
        estimated_duration_hours=job.estimated_duration_hours,
        retry_count=job.retry_count,
        error_message=job.error_message,
        job_metadata=job.job_metadata,
        allocated_at=job.allocated_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.post("/", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def submit_job(
    payload: JobCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(require_auth),
):
    """Submit a new GPU job to the scheduler queue."""
    # Validate gpu_type
    gpu_type_val = None
    if payload.gpu_type:
        try:
            gpu_type_val = GPUType(payload.gpu_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid gpu_type '{payload.gpu_type}'. Valid values: {[e.value for e in GPUType]}",
            )

    # Validate job_type
    try:
        job_type_val = JobType(payload.job_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid job_type '{payload.job_type}'",
        )

    job = Job(
        user_id=current_user.id if current_user else None,
        name=payload.name,
        model=payload.model,
        job_type=job_type_val,
        status=JobStatus.QUEUED,
        priority=payload.priority,
        gpu_type=gpu_type_val,
        gpu_count=payload.gpu_count,
        gpu_memory_gb=payload.gpu_memory_gb,
        preferred_regions=payload.preferred_regions,
        excluded_regions=payload.excluded_regions,
        budget=payload.budget,
        sla_deadline=payload.sla_deadline,
        use_spot=payload.use_spot,
        estimated_duration_hours=payload.estimated_duration_hours,
        job_metadata=payload.job_metadata,
    )
    db.add(job)
    await db.flush()  # get job.id

    # Add to Redis priority queue
    await redis_queue.enqueue(
        str(job.id),
        job.priority,
        {
            "job_id": str(job.id),
            "status": "queued",
            "name": job.name,
            "gpu_type": str(gpu_type_val.value) if gpu_type_val else None,
            "gpu_count": job.gpu_count,
            "priority": job.priority,
            "submitted_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    await db.commit()
    await db.refresh(job)
    return _job_to_response(job)


@router.get("/", response_model=JobListResponse)
async def list_jobs(
    status: Optional[str] = Query(default=None),
    job_type: Optional[str] = Query(default=None),
    priority_min: Optional[int] = Query(default=None, ge=1, le=10),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(require_auth),
):
    """List jobs with optional filtering and pagination."""
    query = select(Job).options(joinedload(Job.instance))

    if status:
        try:
            status_val = JobStatus(status)
            query = query.where(Job.status == status_val)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid status '{status}'")
    if job_type:
        try:
            query = query.where(Job.job_type == JobType(job_type))
        except ValueError:
            pass
    if priority_min:
        query = query.where(Job.priority >= priority_min)
    if current_user:
        query = query.where(Job.user_id == current_user.id)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = (
        query
        .order_by(Job.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    jobs = result.scalars().all()

    return JobListResponse(
        jobs=[_job_to_response(j) for j in jobs],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size),
    )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(require_auth),
):
    """Get a job by ID, including its allocated instance info."""
    result = await db.execute(
        select(Job)
        .options(joinedload(Job.instance))
        .where(Job.id == job_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_to_response(job)


@router.patch("/{job_id}", response_model=JobResponse)
async def update_job(
    job_id: UUID,
    payload: JobUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(require_auth),
):
    """Update mutable job fields (priority, budget, SLA deadline)."""
    result = await db.execute(
        select(Job)
        .options(joinedload(Job.instance))
        .where(Job.id == job_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
        raise HTTPException(status_code=400, detail=f"Cannot modify job in '{job.status}' state")

    if payload.priority is not None:
        job.priority = payload.priority
    if payload.budget is not None:
        job.budget = payload.budget
    if payload.sla_deadline is not None:
        job.sla_deadline = payload.sla_deadline

    await db.commit()
    await db.refresh(job)
    return _job_to_response(job)


@router.delete("/{job_id}", response_model=JobCancelResponse)
async def cancel_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(require_auth),
):
    """Cancel a job. Releases its allocated GPU instance if running."""
    result = await db.execute(
        select(Job)
        .options(joinedload(Job.instance))
        .where(Job.id == job_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status in (JobStatus.COMPLETED, JobStatus.CANCELLED):
        raise HTTPException(
            status_code=400,
            detail=f"Job is already in '{job.status}' state",
        )

    if job.instance_id:
        from app.inventory.manager import inventory_manager
        await inventory_manager.mark_available(db, job.instance_id)

    job.status = JobStatus.CANCELLED
    job.completed_at = datetime.now(timezone.utc)
    await redis_queue.remove(str(job_id))
    await redis_queue.set_job_status(str(job_id), {"job_id": str(job_id), "status": "cancelled"})

    await db.commit()
    return JobCancelResponse(
        job_id=str(job_id),
        status="cancelled",
        message="Job cancelled successfully",
    )


@router.post("/{job_id}/scale", response_model=JobResponse)
async def scale_job(
    job_id: UUID,
    payload: JobScaleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(require_auth),
):
    """
    Scale the GPU count for a running or queued job.
    For queued jobs, updates the requirement.
    For running jobs, triggers re-allocation on a larger instance.
    """
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status not in (JobStatus.QUEUED, JobStatus.RUNNING):
        raise HTTPException(
            status_code=400,
            detail=f"Can only scale jobs in 'queued' or 'running' state, not '{job.status}'",
        )

    old_count = job.gpu_count
    job.gpu_count = payload.gpu_count

    if job.status == JobStatus.RUNNING and job.instance_id:
        # Free current instance and re-queue for reallocation
        from app.inventory.manager import inventory_manager
        await inventory_manager.mark_available(db, job.instance_id)
        job.instance_id = None
        job.status = JobStatus.QUEUED
        await redis_queue.enqueue(str(job.id), job.priority, {"job_id": str(job.id), "status": "queued"})

    await db.commit()
    await db.refresh(job)
    return _job_to_response(job)


@router.get("/{job_id}/metrics", response_model=List[JobMetricResponse])
async def get_job_metrics(
    job_id: UUID,
    limit: int = Query(default=60, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(require_auth),
):
    """Fetch the most recent metrics data points for a job."""
    result = await db.execute(select(Job.id).where(Job.id == job_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Job not found")

    metrics_result = await db.execute(
        select(JobMetric)
        .where(JobMetric.job_id == job_id)
        .order_by(JobMetric.timestamp.desc())
        .limit(limit)
    )
    metrics = metrics_result.scalars().all()
    return [JobMetricResponse.model_validate(m) for m in reversed(metrics)]
