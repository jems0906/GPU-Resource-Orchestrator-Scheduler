"""Providers API — GPU inventory, instance details, and pricing information."""

from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import require_auth
from app.db.session import get_db
from app.db.models import GPUInstance, InstanceStatus, User
from app.schemas.provider import (
    GPUInstanceSchema, ProviderSummary, InventoryResponse, PricingInfo,
)
from app.inventory.manager import inventory_manager
from app.providers.registry import provider_registry

router = APIRouter(prefix="/providers", tags=["providers"])


def _build_provider_summaries_from_instances(instances: List[GPUInstance]) -> List[ProviderSummary]:
    grouped = {}

    for instance in instances:
        provider_name = str(instance.provider.value) if hasattr(instance.provider, "value") else str(instance.provider)
        gpu_type = str(instance.gpu_type.value) if hasattr(instance.gpu_type, "value") else str(instance.gpu_type)
        status = str(instance.status.value) if hasattr(instance.status, "value") else str(instance.status)

        if provider_name not in grouped:
            grouped[provider_name] = {
                "total_instances": 0,
                "available_instances": 0,
                "allocated_instances": 0,
                "total_gpus": 0,
                "available_gpus": 0,
                "regions": set(),
                "gpu_types": {},
            }

        summary = grouped[provider_name]
        summary["total_instances"] += 1
        summary["total_gpus"] += instance.gpu_count
        summary["regions"].add(instance.region)

        if status == InstanceStatus.AVAILABLE.value:
            summary["available_instances"] += 1
            summary["available_gpus"] += instance.gpu_count
            summary["gpu_types"][gpu_type] = summary["gpu_types"].get(gpu_type, 0) + instance.gpu_count
        else:
            summary["allocated_instances"] += 1

    return [
        ProviderSummary(
            provider=provider_name,
            total_instances=summary["total_instances"],
            available_instances=summary["available_instances"],
            allocated_instances=summary["allocated_instances"],
            total_gpus=summary["total_gpus"],
            available_gpus=summary["available_gpus"],
            regions=sorted(summary["regions"]),
            gpu_types=summary["gpu_types"],
            estimated_hourly_cost_if_full=0.0,
        )
        for provider_name, summary in grouped.items()
    ]


@router.get("/inventory", response_model=InventoryResponse)
async def get_inventory(
    provider: Optional[str] = Query(default=None),
    region: Optional[str] = Query(default=None),
    gpu_type: Optional[str] = Query(default=None),
    available_only: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(require_auth),
):
    """Return the full GPU inventory across all cloud providers."""
    query = select(GPUInstance)

    if provider:
        query = query.where(GPUInstance.provider == provider)
    if region:
        query = query.where(GPUInstance.region == region)
    if gpu_type:
        query = query.where(GPUInstance.gpu_type == gpu_type)
    if available_only:
        query = query.where(GPUInstance.status == InstanceStatus.AVAILABLE)

    result = await db.execute(query)
    instances = result.scalars().all()

    # Build provider summaries from cache
    inv_cache = inventory_manager.get_provider_summary()
    provider_summaries: List[ProviderSummary] = []
    for pname, pdata in inv_cache.items():
        provider_summaries.append(ProviderSummary(
            provider=pname,
            total_instances=pdata["total"],
            available_instances=pdata["available"],
            allocated_instances=pdata["total"] - pdata["available"],
            total_gpus=pdata["total_gpus"],
            available_gpus=pdata["available_gpus"],
            regions=sorted(pdata["regions"]),
            gpu_types={k: v for k, v in pdata["gpu_types"].items()},
            estimated_hourly_cost_if_full=0.0,
        ))

    if not provider_summaries and instances:
        provider_summaries = _build_provider_summaries_from_instances(instances)

    total_available = sum(p.available_gpus for p in provider_summaries)

    return InventoryResponse(
        providers=provider_summaries,
        total_instances=len(instances),
        total_available_gpus=total_available,
        instances=[
            GPUInstanceSchema(
                id=i.id,
                provider=str(i.provider.value) if hasattr(i.provider, "value") else str(i.provider),
                region=i.region,
                zone=i.zone,
                instance_type=i.instance_type,
                gpu_type=str(i.gpu_type.value) if hasattr(i.gpu_type, "value") else str(i.gpu_type),
                gpu_count=i.gpu_count,
                gpu_memory_gb=i.gpu_memory_gb,
                cpu_count=i.cpu_count,
                memory_gb=i.memory_gb,
                status=str(i.status.value) if hasattr(i.status, "value") else str(i.status),
                is_spot=i.is_spot,
                on_demand_price_hour=i.on_demand_price_hour,
                spot_price_hour=i.spot_price_hour,
                allocated_gpu_count=i.allocated_gpu_count or 0,
                last_seen=i.last_seen,
            )
            for i in instances
        ],
        last_updated=inventory_manager.last_sync or datetime.now(timezone.utc),
    )


@router.get("/health")
async def provider_health():
    """Check connectivity to each cloud provider."""
    results = await provider_registry.health_check()
    return {
        "providers": results,
        "all_healthy": all(results.values()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/pricing", response_model=List[PricingInfo])
async def get_pricing(
    provider: Optional[str] = Query(default=None),
    gpu_type: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(require_auth),
):
    """Return GPU pricing across providers and instance types."""
    query = select(GPUInstance).group_by(
        GPUInstance.provider,
        GPUInstance.instance_type,
        GPUInstance.region,
        GPUInstance.gpu_type,
        GPUInstance.gpu_count,
        GPUInstance.on_demand_price_hour,
        GPUInstance.spot_price_hour,
        GPUInstance.id,
    )
    if provider:
        query = query.where(GPUInstance.provider == provider)
    if gpu_type:
        query = query.where(GPUInstance.gpu_type == gpu_type)

    result = await db.execute(query.limit(200))
    instances = result.scalars().all()

    seen = set()
    pricing: List[PricingInfo] = []
    for i in instances:
        key = (str(i.provider), i.instance_type, i.region)
        if key in seen:
            continue
        seen.add(key)
        spot_savings = None
        if i.spot_price_hour:
            spot_savings = round((1 - i.spot_price_hour / i.on_demand_price_hour) * 100, 1)
        pricing.append(PricingInfo(
            provider=str(i.provider.value) if hasattr(i.provider, "value") else str(i.provider),
            region=i.region,
            instance_type=i.instance_type,
            gpu_type=str(i.gpu_type.value) if hasattr(i.gpu_type, "value") else str(i.gpu_type),
            gpu_count=i.gpu_count,
            on_demand_price_hour=i.on_demand_price_hour,
            spot_price_hour=i.spot_price_hour,
            spot_savings_percent=spot_savings,
        ))

    return sorted(pricing, key=lambda p: (p.provider, p.gpu_type, p.on_demand_price_hour))
