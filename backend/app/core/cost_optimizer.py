"""
Cost Optimizer — routes jobs to the cheapest available resource while
respecting budget constraints and spot interruption risk tolerance.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple
import logging

from app.db.models import Job, GPUInstance
from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class CostEstimate:
    instance_id: str
    provider: str
    region: str
    gpu_type: str
    instance_type: str
    price_per_hour: float
    is_spot: bool
    estimated_total_cost: float
    on_demand_equivalent_cost: float
    savings: float
    savings_percent: float
    interruption_risk: float  # 0-1 probability per hour


class CostOptimizer:
    """
    Evaluates cost options and selects the cheapest viable placement,
    accounting for spot interruption risk and SLA urgency.
    """

    def estimate_job_cost(
        self,
        instance: GPUInstance,
        duration_hours: float,
        use_spot: bool,
    ) -> CostEstimate:
        """Compute cost estimate for placing a job on an instance."""
        price_per_hour = (
            instance.spot_price_hour
            if (use_spot and instance.spot_price_hour)
            else instance.on_demand_price_hour
        )
        is_spot = use_spot and instance.spot_price_hour is not None

        total_cost = round(price_per_hour * duration_hours, 4)
        on_demand_total = round(instance.on_demand_price_hour * duration_hours, 4)
        savings = round(on_demand_total - total_cost, 4) if is_spot else 0.0
        savings_pct = round((savings / on_demand_total * 100) if on_demand_total > 0 else 0.0, 1)

        interruption_risk = settings.SPOT_INTERRUPTION_RATE if is_spot else 0.0

        return CostEstimate(
            instance_id=instance.id,
            provider=str(instance.provider.value) if hasattr(instance.provider, "value") else str(instance.provider),
            region=instance.region,
            gpu_type=str(instance.gpu_type.value) if hasattr(instance.gpu_type, "value") else str(instance.gpu_type),
            instance_type=instance.instance_type,
            price_per_hour=price_per_hour,
            is_spot=is_spot,
            estimated_total_cost=total_cost,
            on_demand_equivalent_cost=on_demand_total,
            savings=savings,
            savings_percent=savings_pct,
            interruption_risk=interruption_risk,
        )

    def select_cheapest(
        self,
        job: Job,
        candidates: List[GPUInstance],
    ) -> Optional[Tuple[GPUInstance, CostEstimate]]:
        """
        From a list of candidate instances, select the cheapest one
        that fits within budget and acceptable risk profile.

        For jobs with SLA deadlines, penalise high spot interruption risk
        to avoid costly restarts that could breach the deadline.
        """
        duration = job.estimated_duration_hours or 1.0
        has_tight_sla = job.sla_deadline is not None and job.priority >= 8

        best: Optional[Tuple[GPUInstance, CostEstimate]] = None
        best_adjusted_cost = float("inf")

        for instance in candidates:
            for use_spot in ([True, False] if job.use_spot else [False]):
                estimate = self.estimate_job_cost(instance, duration, use_spot)

                # Reject if over budget
                if job.budget and estimate.estimated_total_cost > job.budget:
                    continue

                # Risk-adjusted cost: for high-SLA jobs, add expected restart cost
                risk_adjusted = estimate.estimated_total_cost
                if estimate.is_spot and has_tight_sla:
                    # Expected cost = P(interrupt) * restart_overhead
                    restart_overhead = duration * instance.on_demand_price_hour * 0.25
                    risk_adjusted += estimate.interruption_risk * restart_overhead

                if risk_adjusted < best_adjusted_cost:
                    best_adjusted_cost = risk_adjusted
                    best = (instance, estimate)

        return best

    def compute_savings_summary(
        self,
        total_cost: float,
        total_on_demand_equivalent: float,
    ) -> dict:
        """Summarise overall cost savings."""
        savings = total_on_demand_equivalent - total_cost
        savings_pct = (savings / total_on_demand_equivalent * 100) if total_on_demand_equivalent > 0 else 0.0
        return {
            "total_cost": round(total_cost, 4),
            "total_on_demand_equivalent": round(total_on_demand_equivalent, 4),
            "total_savings": round(savings, 4),
            "savings_percent": round(savings_pct, 1),
        }


cost_optimizer = CostOptimizer()
