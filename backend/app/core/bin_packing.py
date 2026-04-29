"""
Bin-Packing Scheduler — assigns jobs to optimal GPU instances.

Algorithm: Best-Fit Decreasing (BFD) adapted for GPU workloads.
Scoring considers GPU type match, capacity headroom, cost per GPU-hour,
region preference, and spot availability.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import logging

from app.db.models import Job, GPUInstance

logger = logging.getLogger(__name__)

# Weights for the placement score (higher = more important)
WEIGHT_GPU_TYPE_MATCH = 100.0
WEIGHT_COST = 60.0
WEIGHT_REGION_PREFERENCE = 30.0
WEIGHT_CAPACITY_FIT = 20.0
WEIGHT_SPOT = 15.0


@dataclass
class PlacementCandidate:
    instance: GPUInstance
    score: float
    estimated_cost: float
    is_spot: bool


class BinPackingScheduler:
    """
    Assigns jobs to GPU instances using a scored Best-Fit strategy.

    For each job the algorithm:
      1. Filters instances that satisfy hard constraints (GPU type, memory, count, budget).
      2. Scores each candidate on GPU match, cost, region preference, and spot savings.
      3. Returns the highest-scoring candidate.

    This runs in O(n) per job where n = candidate instance count, giving sub-second
    placement decisions even with thousands of instances.
    """

    def find_best_instance(
        self,
        job: Job,
        available_instances: List[GPUInstance],
    ) -> Optional[PlacementCandidate]:
        """
        Find the best GPU instance for a job.
        Returns None if no suitable instance exists.
        """
        candidates: List[PlacementCandidate] = []

        for instance in available_instances:
            if not self._satisfies_hard_constraints(job, instance):
                continue

            score, estimated_cost, use_spot = self._score_instance(job, instance)
            candidates.append(
                PlacementCandidate(
                    instance=instance,
                    score=score,
                    estimated_cost=estimated_cost,
                    is_spot=use_spot,
                )
            )

        if not candidates:
            return None

        # Return highest score; break ties by lowest estimated cost
        return max(candidates, key=lambda c: (c.score, -c.estimated_cost))

    def _satisfies_hard_constraints(self, job: Job, instance: GPUInstance) -> bool:
        """Hard constraints that must all be satisfied."""
        # GPU count
        if instance.gpu_count < job.gpu_count:
            return False

        # GPU type (if specified and not "any")
        if job.gpu_type and job.gpu_type != "any":
            if instance.gpu_type != job.gpu_type:
                return False

        # GPU memory
        if job.gpu_memory_gb and instance.gpu_memory_gb < job.gpu_memory_gb:
            return False

        # Region exclusions
        if job.excluded_regions and instance.region in job.excluded_regions:
            return False

        # Budget check (rough estimate based on 1 hour minimum)
        if job.budget is not None:
            price = instance.spot_price_hour if (job.use_spot and instance.spot_price_hour) else instance.on_demand_price_hour
            min_cost = price  # at least 1 billing increment
            if min_cost > job.budget:
                return False

        return True

    def _score_instance(
        self,
        job: Job,
        instance: GPUInstance,
    ) -> Tuple[float, float, bool]:
        """
        Compute a placement score for this instance/job pair.
        Returns (score, estimated_cost_usd, use_spot).
        """
        score = 0.0

        # --- GPU type match ---
        if job.gpu_type and job.gpu_type != "any" and instance.gpu_type == job.gpu_type:
            score += WEIGHT_GPU_TYPE_MATCH
        elif not job.gpu_type or job.gpu_type == "any":
            score += WEIGHT_GPU_TYPE_MATCH * 0.5  # any type is partial match

        # --- Spot vs on-demand ---
        use_spot = job.use_spot and instance.spot_price_hour is not None
        price_per_hour = (
            instance.spot_price_hour if use_spot else instance.on_demand_price_hour
        )
        if use_spot:
            score += WEIGHT_SPOT

        # --- Cost score (penalise expensive instances) ---
        max_reasonable_price = 35.0  # $35/hr is top of range
        cost_ratio = min(price_per_hour / max_reasonable_price, 1.0)
        score += WEIGHT_COST * (1.0 - cost_ratio)

        # --- Region preference ---
        if job.preferred_regions and instance.region in job.preferred_regions:
            score += WEIGHT_REGION_PREFERENCE

        # --- Capacity fit (prefer tightest fit to reduce fragmentation) ---
        excess_gpus = instance.gpu_count - job.gpu_count
        if excess_gpus == 0:
            score += WEIGHT_CAPACITY_FIT  # perfect fit
        elif excess_gpus <= 2:
            score += WEIGHT_CAPACITY_FIT * 0.7
        else:
            score += WEIGHT_CAPACITY_FIT * (1.0 / (1.0 + excess_gpus * 0.3))

        # Estimate cost for a full job run
        duration = job.estimated_duration_hours or 1.0
        estimated_cost = round(price_per_hour * duration, 4)

        return score, estimated_cost, use_spot

    def sort_jobs_by_priority(self, jobs: List[Job]) -> List[Job]:
        """
        Sort jobs for processing: higher priority first,
        then earlier SLA deadline, then earlier submission.
        """
        def sort_key(j: Job):
            deadline_ts = j.sla_deadline.timestamp() if j.sla_deadline else float("inf")
            return (-j.priority, deadline_ts, j.created_at.timestamp())

        return sorted(jobs, key=sort_key)
