"""
GPU Scheduler — main orchestration loop.

Every SCHEDULER_INTERVAL_SECONDS the scheduler:
  1. Syncs GPU inventory from cloud providers.
  2. Pops pending jobs from the Redis priority queue.
  3. Uses BinPackingScheduler + CostOptimizer to find the best instance.
  4. Allocates the instance, creates billing records, and updates job status.
  5. Simulates job completion for demo purposes (real impl would poll cloud APIs).
  6. Runs SLA checks and handles failover for spot-interrupted jobs.
"""

import asyncio
import logging
import random
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import AsyncSessionLocal
from app.db.models import Job, JobStatus, GPUInstance, InstanceStatus, BillingRecord, JobMetric
from app.core.bin_packing import BinPackingScheduler
from app.core.cost_optimizer import cost_optimizer
from app.core.sla_enforcer import sla_enforcer
from app.inventory.manager import inventory_manager
from app.queue.redis_queue import redis_queue
from app.providers.registry import provider_registry

logger = logging.getLogger(__name__)

bin_packer = BinPackingScheduler()


class GPUScheduler:
    def __init__(self):
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._cycle_count = 0

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("GPU Scheduler started (interval=%.1fs)", settings.SCHEDULER_INTERVAL_SECONDS)

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("GPU Scheduler stopped after %d cycles", self._cycle_count)

    async def _loop(self) -> None:
        while self._running:
            try:
                await self._tick()
            except Exception as exc:
                logger.exception("Scheduler tick error: %s", exc)
            await asyncio.sleep(settings.SCHEDULER_INTERVAL_SECONDS)
            self._cycle_count += 1

    async def _tick(self) -> None:
        async with AsyncSessionLocal() as db:
            # 1. Sync inventory every 10 cycles (~20 seconds)
            if self._cycle_count % 10 == 0:
                try:
                    synced = await inventory_manager.sync(db)
                    logger.debug("Inventory sync: %d instances", synced)
                except Exception as exc:
                    logger.warning("Inventory sync failed: %s", exc)

            # 2. Process queued jobs
            await self._process_queue(db)

            # 3. Simulate progress & complete running jobs
            await self._update_running_jobs(db)

            # 4. SLA checks every 5 cycles
            if self._cycle_count % 5 == 0:
                at_risk, violated = await sla_enforcer.check_all(db)
                if at_risk or violated:
                    logger.info("SLA check: %d at-risk, %d violated", at_risk, violated)

            # 5. Handle spot interruptions
            await self._handle_spot_interruptions(db)

            await db.commit()

    async def _process_queue(self, db: AsyncSession) -> None:
        """Dequeue high-priority jobs and attempt allocation."""
        job_ids = await redis_queue.dequeue(count=20)
        if not job_ids:
            # Also check DB for any queued jobs not yet in Redis
            result = await db.execute(
                select(Job)
                .where(Job.status == JobStatus.QUEUED)
                .order_by(Job.priority.desc(), Job.created_at.asc())
                .limit(20)
            )
            db_jobs: List[Job] = result.scalars().all()
        else:
            result = await db.execute(
                select(Job)
                .where(Job.id.in_([UUID(jid) for jid in job_ids]))
                .where(Job.status == JobStatus.QUEUED)
            )
            db_jobs = result.scalars().all()

        if not db_jobs:
            return

        sorted_jobs = bin_packer.sort_jobs_by_priority(db_jobs)

        for job in sorted_jobs:
            await self._allocate_job(db, job)

    async def _allocate_job(self, db: AsyncSession, job: Job) -> bool:
        """Find the best instance and allocate the job to it."""
        available = await inventory_manager.get_available_instances(
            db,
            gpu_type=str(job.gpu_type.value) if job.gpu_type else None,
            min_gpu_count=job.gpu_count,
            min_gpu_memory_gb=job.gpu_memory_gb,
            regions=job.preferred_regions,
            excluded_regions=job.excluded_regions,
        )

        if not available:
            logger.debug("No available instances for job %s", job.id)
            return False

        candidate = bin_packer.find_best_instance(job, available)
        if not candidate:
            logger.debug("No suitable instance for job %s", job.id)
            return False

        instance = candidate.instance
        provider = provider_registry.get(str(instance.provider.value) if hasattr(instance.provider, "value") else str(instance.provider))

        if provider:
            result = await provider.provision_instance(
                instance_type=instance.instance_type,
                region=instance.region,
                is_spot=candidate.is_spot,
            )
            if not result.success:
                logger.warning("Provision failed for job %s: %s", job.id, result.error)
                return False

        # Update instance status in DB
        await inventory_manager.mark_allocated(db, instance.id)

        # Update job
        now = datetime.now(timezone.utc)
        job.status = JobStatus.RUNNING
        job.instance_id = instance.id
        job.allocated_at = now
        job.started_at = now
        job.estimated_cost = candidate.estimated_cost

        # Publish event
        await redis_queue.set_job_status(str(job.id), {
            "job_id": str(job.id),
            "status": "running",
            "instance_id": instance.id,
            "provider": str(instance.provider.value) if hasattr(instance.provider, "value") else str(instance.provider),
            "region": instance.region,
            "gpu_type": str(instance.gpu_type.value) if hasattr(instance.gpu_type, "value") else str(instance.gpu_type),
            "is_spot": candidate.is_spot,
            "estimated_cost": candidate.estimated_cost,
            "started_at": now.isoformat(),
        })

        logger.info(
            "Allocated job %s → instance %s (%s/%s) cost=%.4f spot=%s",
            job.id, instance.id, instance.provider, instance.region,
            candidate.estimated_cost, candidate.is_spot,
        )
        return True

    async def _update_running_jobs(self, db: AsyncSession) -> None:
        """Simulate job progress; complete jobs after simulated duration."""
        result = await db.execute(
            select(Job)
            .where(Job.status == JobStatus.RUNNING)
            .where(Job.instance_id.isnot(None))
        )
        running_jobs: List[Job] = result.scalars().all()

        for job in running_jobs:
            if not job.started_at:
                continue

            started = job.started_at
            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)

            elapsed_hours = (datetime.now(timezone.utc) - started).total_seconds() / 3600
            duration = job.estimated_duration_hours or random.uniform(0.1, 2.0)

            # Record metrics snapshot
            instance_result = await db.execute(
                select(GPUInstance).where(GPUInstance.id == job.instance_id)
            )
            instance = instance_result.scalar_one_or_none()
            if instance:
                price = (
                    instance.spot_price_hour
                    if (job.use_spot and instance.spot_price_hour)
                    else instance.on_demand_price_hour
                )
                cost_so_far = round(price * elapsed_hours, 4)

                metric = JobMetric(
                    job_id=job.id,
                    gpu_utilization=random.uniform(65, 99),
                    gpu_memory_used_gb=instance.gpu_memory_gb * random.uniform(0.5, 0.92),
                    gpu_memory_total_gb=float(instance.gpu_memory_gb),
                    cpu_utilization=random.uniform(20, 85),
                    memory_used_gb=instance.memory_gb * random.uniform(0.3, 0.75),
                    throughput=random.uniform(200, 2000),
                    cost_so_far=cost_so_far,
                )
                db.add(metric)

                # Push to Redis for real-time dashboard
                await redis_queue.push_metrics(str(job.id), {
                    "gpu_utilization": metric.gpu_utilization,
                    "gpu_memory_used_gb": metric.gpu_memory_used_gb,
                    "cost_so_far": cost_so_far,
                    "elapsed_hours": elapsed_hours,
                })

                # Complete job after simulated duration
                if elapsed_hours >= duration:
                    await self._complete_job(db, job, instance, elapsed_hours, price)

    async def _complete_job(
        self,
        db: AsyncSession,
        job: Job,
        instance: GPUInstance,
        duration_hours: float,
        price_per_hour: float,
    ) -> None:
        now = datetime.now(timezone.utc)
        total_cost = round(price_per_hour * duration_hours, 4)
        is_spot = job.use_spot and instance.spot_price_hour is not None
        on_demand_cost = round(instance.on_demand_price_hour * duration_hours, 4)

        job.status = JobStatus.COMPLETED
        job.completed_at = now
        job.actual_cost = total_cost

        # Free up instance
        await inventory_manager.mark_available(db, instance.id)
        if hasattr(instance, 'provider'):
            provider = provider_registry.get(
                str(instance.provider.value) if hasattr(instance.provider, "value") else str(instance.provider)
            )
            if provider:
                await provider.terminate_instance(instance.id, instance.region)

        # Billing record
        billing = BillingRecord(
            job_id=job.id,
            user_id=job.user_id,
            instance_id=instance.id,
            provider=instance.provider,
            region=instance.region,
            gpu_type=instance.gpu_type,
            duration_seconds=int(duration_hours * 3600),
            price_per_hour=price_per_hour,
            total_cost=total_cost,
            is_spot=is_spot,
            on_demand_equivalent_cost=on_demand_cost,
            savings=round(on_demand_cost - total_cost, 4) if is_spot else 0.0,
            billing_period_start=job.started_at,
            billing_period_end=now,
        )
        db.add(billing)

        await redis_queue.set_job_status(str(job.id), {
            "job_id": str(job.id),
            "status": "completed",
            "actual_cost": total_cost,
            "completed_at": now.isoformat(),
        })
        logger.info("Completed job %s, cost=%.4f", job.id, total_cost)

    async def _handle_spot_interruptions(self, db: AsyncSession) -> None:
        """Simulate spot interruption and trigger failover for affected jobs."""
        result = await db.execute(
            select(Job, GPUInstance)
            .join(GPUInstance, Job.instance_id == GPUInstance.id)
            .where(Job.status == JobStatus.RUNNING)
            .where(GPUInstance.is_spot.is_(True))
        )
        rows = result.all()

        for job, instance in rows:
            # Low probability of interruption per scheduler tick
            if random.random() < (settings.SPOT_INTERRUPTION_RATE / 100):
                logger.warning(
                    "Spot interruption for job %s on instance %s — initiating failover",
                    job.id, instance.id,
                )
                job.status = JobStatus.FAILOVER
                job.instance_id = None
                job.retry_count += 1

                # Re-queue with higher priority for fast failover
                job.priority = min(job.priority + 1, 10)
                await inventory_manager.mark_available(db, instance.id)

                await redis_queue.enqueue(
                    str(job.id),
                    job.priority,
                    {"job_id": str(job.id), "status": "failover", "retry_count": job.retry_count},
                )

                # Re-set status to QUEUED so the main loop picks it up
                job.status = JobStatus.QUEUED


scheduler = GPUScheduler()
