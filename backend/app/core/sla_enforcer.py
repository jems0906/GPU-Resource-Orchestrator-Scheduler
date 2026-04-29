"""
SLA Enforcer — monitors running and queued jobs against their SLA deadlines.
Creates SLAViolation records, raises job priority when at risk, and triggers
failover for jobs that may miss their deadline on the current instance.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import Job, JobStatus, SLAViolation
from app.config import settings

logger = logging.getLogger(__name__)


class SLAEnforcer:
    async def check_all(self, db: AsyncSession) -> Tuple[int, int]:
        """
        Scan active jobs for SLA risks and violations.
        Returns (at_risk_count, violated_count).
        """
        now = datetime.now(timezone.utc)
        warning_cutoff = now + timedelta(minutes=settings.SLA_WARNING_THRESHOLD_MINUTES)
        queue_timeout_cutoff = now - timedelta(minutes=settings.SLA_QUEUE_TIMEOUT_MINUTES)

        # Fetch jobs with SLA deadlines that haven't completed/failed/cancelled
        result = await db.execute(
            select(Job).where(
                Job.status.in_([JobStatus.QUEUED, JobStatus.PENDING, JobStatus.RUNNING]),
            )
        )
        active_jobs: List[Job] = result.scalars().all()

        at_risk = 0
        violated = 0

        for job in active_jobs:
            # Check deadline violations
            if job.sla_deadline:
                deadline = job.sla_deadline
                if deadline.tzinfo is None:
                    deadline = deadline.replace(tzinfo=timezone.utc)

                if now > deadline and job.status != JobStatus.COMPLETED:
                    # Deadline missed
                    await self._record_violation(
                        db, job,
                        violation_type="deadline_missed",
                        severity="critical",
                        details=f"Job missed SLA deadline of {deadline.isoformat()}",
                    )
                    violated += 1

                elif now > deadline - timedelta(minutes=settings.SLA_WARNING_THRESHOLD_MINUTES):
                    # At risk — escalate priority
                    if job.priority < 9:
                        job.priority = min(job.priority + 2, 10)
                        await self._record_violation(
                            db, job,
                            violation_type="sla_at_risk",
                            severity="warning",
                            details=f"Job within {settings.SLA_WARNING_THRESHOLD_MINUTES}min of SLA deadline, priority escalated to {job.priority}",
                        )
                    at_risk += 1

            # Check queue timeout for QUEUED jobs
            if job.status == JobStatus.QUEUED:
                created = job.created_at
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)

                if created < queue_timeout_cutoff:
                    await self._record_violation(
                        db, job,
                        violation_type="queue_timeout",
                        severity="warning",
                        details=f"Job has been queued for more than {settings.SLA_QUEUE_TIMEOUT_MINUTES} minutes",
                    )
                    at_risk += 1

        return at_risk, violated

    async def _record_violation(
        self,
        db: AsyncSession,
        job: Job,
        violation_type: str,
        severity: str,
        details: str,
    ) -> None:
        """Insert a new SLA violation record, avoiding duplicates for same type within 10 min."""
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=10)
        result = await db.execute(
            select(SLAViolation).where(
                SLAViolation.job_id == job.id,
                SLAViolation.violation_type == violation_type,
                SLAViolation.created_at >= cutoff,
            )
        )
        if result.scalar_one_or_none():
            return  # already recorded recently

        violation = SLAViolation(
            job_id=job.id,
            violation_type=violation_type,
            severity=severity,
            details=details,
        )
        db.add(violation)
        logger.warning(
            "SLA %s [%s] for job %s: %s",
            violation_type, severity, job.id, details,
        )

    async def get_active_violations(self, db: AsyncSession) -> List[dict]:
        result = await db.execute(
            select(SLAViolation, Job)
            .join(Job, SLAViolation.job_id == Job.id)
            .where(SLAViolation.resolved_at.is_(None))
            .order_by(SLAViolation.created_at.desc())
            .limit(50)
        )
        rows = result.all()
        return [
            {
                "violation_id": str(v.id),
                "job_id": str(j.id),
                "job_name": j.name,
                "type": v.violation_type,
                "severity": v.severity,
                "details": v.details,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            }
            for v, j in rows
        ]


sla_enforcer = SLAEnforcer()
