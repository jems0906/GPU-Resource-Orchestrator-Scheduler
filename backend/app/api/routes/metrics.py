"""Metrics API — GPU utilization, cost summaries, queue depth, SLA compliance."""

from datetime import datetime, timezone, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, Integer

from app.api.deps import require_auth
from app.db.session import get_db
from app.db.models import Job, JobStatus, JobMetric, BillingRecord, SLAViolation, GPUInstance, User
from app.schemas.metrics import (
    DashboardMetrics, QueueMetrics, SLAMetrics, CostSummary, GPUUtilizationPoint, CostDataPoint,
)
from app.core.sla_enforcer import sla_enforcer
from app.queue.redis_queue import redis_queue
from app.inventory.manager import inventory_manager

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/dashboard", response_model=DashboardMetrics)
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(require_auth),
):
    """Aggregate dashboard metrics: queue, SLA, cost, GPU utilisation."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # --- Queue metrics ---
    queue_depth = await redis_queue.queue_depth()

    status_counts = {}
    for s in JobStatus:
        cnt = await db.execute(select(func.count(Job.id)).where(Job.status == s))
        status_counts[s.value] = cnt.scalar_one()

    completed_today = await db.execute(
        select(func.count(Job.id))
        .where(Job.status == JobStatus.COMPLETED, Job.completed_at >= today_start)
    )
    failed_today = await db.execute(
        select(func.count(Job.id))
        .where(Job.status == JobStatus.FAILED, Job.updated_at >= today_start)
    )

    # Average wait time (queued → running)
    wait_result = await db.execute(
        select(func.avg(
            func.extract("epoch", Job.started_at - Job.created_at) / 60
        ))
        .where(Job.started_at.isnot(None))
    )
    avg_wait = wait_result.scalar_one() or 0.0

    run_result = await db.execute(
        select(func.avg(
            func.extract("epoch", Job.completed_at - Job.started_at) / 60
        ))
        .where(Job.completed_at.isnot(None), Job.started_at.isnot(None))
    )
    avg_run = run_result.scalar_one() or 0.0

    priority_counts: dict = {}
    for p in range(1, 11):
        cnt = await db.execute(
            select(func.count(Job.id)).where(Job.priority == p, Job.status == JobStatus.QUEUED)
        )
        priority_counts[str(p)] = cnt.scalar_one()

    queue_metrics = QueueMetrics(
        total_queued=queue_depth,
        total_running=status_counts.get("running", 0),
        total_completed_today=completed_today.scalar_one(),
        total_failed_today=failed_today.scalar_one(),
        average_wait_time_minutes=round(float(avg_wait), 1),
        average_run_time_minutes=round(float(avg_run), 1),
        jobs_by_status=status_counts,
        jobs_by_priority=priority_counts,
    )

    # --- SLA metrics ---
    active_violations = await sla_enforcer.get_active_violations(db)

    sla_total = await db.execute(
        select(func.count(Job.id)).where(Job.sla_deadline.isnot(None))
    )
    sla_violated_count = await db.execute(
        select(func.count(SLAViolation.id))
        .where(SLAViolation.violation_type == "deadline_missed", SLAViolation.resolved_at.is_(None))
    )
    sla_at_risk_count = await db.execute(
        select(func.count(SLAViolation.id))
        .where(SLAViolation.violation_type == "sla_at_risk", SLAViolation.resolved_at.is_(None))
    )
    total_sla = sla_total.scalar_one()
    violated = sla_violated_count.scalar_one()
    at_risk = sla_at_risk_count.scalar_one()
    compliant = max(total_sla - violated, 0)
    compliance_pct = round((compliant / total_sla * 100) if total_sla > 0 else 100.0, 1)

    sla_metrics = SLAMetrics(
        total_jobs_with_sla=total_sla,
        sla_compliant=compliant,
        sla_violated=violated,
        sla_at_risk=at_risk,
        compliance_percent=compliance_pct,
        active_violations=active_violations[:10],
    )

    # --- Cost metrics ---
    cost_today = await db.execute(
        select(func.sum(BillingRecord.total_cost)).where(BillingRecord.created_at >= today_start)
    )
    cost_month = await db.execute(
        select(func.sum(BillingRecord.total_cost)).where(BillingRecord.created_at >= month_start)
    )
    cost_all = await db.execute(select(func.sum(BillingRecord.total_cost)))
    savings_all = await db.execute(select(func.sum(BillingRecord.savings)))
    total_od = await db.execute(select(func.sum(BillingRecord.on_demand_equivalent_cost)))
    avg_job_cost = await db.execute(
        select(func.avg(BillingRecord.total_cost))
    )

    total_cost = float(cost_all.scalar_one() or 0.0)
    total_savings = float(savings_all.scalar_one() or 0.0)
    total_od_val = float(total_od.scalar_one() or total_cost)
    savings_pct = round((total_savings / total_od_val * 100) if total_od_val > 0 else 0.0, 1)

    # Cost by provider
    provider_costs = await db.execute(
        select(BillingRecord.provider, func.sum(BillingRecord.total_cost))
        .group_by(BillingRecord.provider)
    )
    cost_by_provider = {str(p.value if hasattr(p, "value") else p): round(float(c or 0), 2) for p, c in provider_costs.all()}

    gpu_costs = await db.execute(
        select(BillingRecord.gpu_type, func.sum(BillingRecord.total_cost))
        .group_by(BillingRecord.gpu_type)
    )
    cost_by_gpu = {str(g.value if hasattr(g, "value") else g): round(float(c or 0), 2) for g, c in gpu_costs.all()}

    cost_summary = CostSummary(
        total_cost_today=round(float(cost_today.scalar_one() or 0.0), 4),
        total_cost_this_month=round(float(cost_month.scalar_one() or 0.0), 4),
        total_cost_all_time=round(total_cost, 4),
        total_savings_from_spot=round(total_savings, 4),
        savings_percent=savings_pct,
        cost_by_provider=cost_by_provider,
        cost_by_gpu_type=cost_by_gpu,
        average_cost_per_job=round(float(avg_job_cost.scalar_one() or 0.0), 4),
    )

    # --- GPU utilisation (latest metric per running job) ---
    running_result = await db.execute(
        select(Job)
        .where(Job.status == JobStatus.RUNNING)
        .limit(20)
    )
    running_jobs = running_result.scalars().all()

    gpu_utilization: List[GPUUtilizationPoint] = []
    for job in running_jobs:
        if not job.instance_id:
            continue
        inst_result = await db.execute(
            select(GPUInstance).where(GPUInstance.id == job.instance_id)
        )
        inst = inst_result.scalar_one_or_none()
        if not inst:
            continue
        latest_metric = await db.execute(
            select(JobMetric)
            .where(JobMetric.job_id == job.id)
            .order_by(JobMetric.timestamp.desc())
            .limit(1)
        )
        m = latest_metric.scalar_one_or_none()
        if m:
            gpu_utilization.append(GPUUtilizationPoint(
                timestamp=m.timestamp or now,
                provider=str(inst.provider.value) if hasattr(inst.provider, "value") else str(inst.provider),
                region=inst.region,
                gpu_type=str(inst.gpu_type.value) if hasattr(inst.gpu_type, "value") else str(inst.gpu_type),
                utilization_percent=round(m.gpu_utilization or 0.0, 1),
                memory_used_gb=round(m.gpu_memory_used_gb or 0.0, 2),
                memory_total_gb=round(m.gpu_memory_total_gb or float(inst.gpu_memory_gb), 2),
            ))

    # GPU inventory counts
    inv_summary = inventory_manager.get_provider_summary()
    total_available_gpus = sum(v.get("available_gpus", 0) for v in inv_summary.values())
    total_in_use_gpus = sum(v.get("total_gpus", 0) - v.get("available_gpus", 0) for v in inv_summary.values())

    return DashboardMetrics(
        queue=queue_metrics,
        sla=sla_metrics,
        cost=cost_summary,
        gpu_utilization=gpu_utilization,
        active_jobs_count=status_counts.get("running", 0),
        total_gpus_available=total_available_gpus,
        total_gpus_in_use=total_in_use_gpus,
        timestamp=now,
    )


@router.get("/cost-history", response_model=List[CostDataPoint])
async def get_cost_history(
    days: int = Query(default=30, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(require_auth),
):
    """Daily cost breakdown for the last N days."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(
            func.date(BillingRecord.created_at).label("date"),
            BillingRecord.provider,
            func.sum(BillingRecord.total_cost).label("cost"),
            func.sum(
                func.coalesce(BillingRecord.total_cost * BillingRecord.is_spot.cast(Integer), 0)
            ).label("spot_cost"),
            func.sum(BillingRecord.on_demand_equivalent_cost).label("od_cost"),
            func.sum(func.coalesce(BillingRecord.savings, 0)).label("savings"),
        )
        .where(BillingRecord.created_at >= since)
        .group_by(func.date(BillingRecord.created_at), BillingRecord.provider)
        .order_by(func.date(BillingRecord.created_at))
    )
    rows = result.all()
    return [
        CostDataPoint(
            date=str(row.date),
            provider=str(row.provider.value if hasattr(row.provider, "value") else row.provider),
            cost=round(float(row.cost or 0), 4),
            spot_cost=round(float(row.spot_cost or 0), 4),
            on_demand_cost=round(float(row.od_cost or 0), 4),
            savings=round(float(row.savings or 0), 4),
        )
        for row in rows
    ]


@router.get("/queue-depth")
async def get_queue_depth():
    """Real-time queue depth from Redis."""
    depth = await redis_queue.queue_depth()
    queued_ids = await redis_queue.peek(count=5)
    return {
        "queue_depth": depth,
        "top_job_ids": queued_ids,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
