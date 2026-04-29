"""
Inventory Manager — tracks and syncs GPU instances across all cloud providers.
Maintains a local in-memory cache and syncs with the PostgreSQL database.
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db.models import GPUInstance, InstanceStatus, CloudProvider, GPUType
from app.providers.registry import provider_registry
from app.providers.base import GPUInstanceInfo

logger = logging.getLogger(__name__)


class InventoryManager:
    """Tracks GPU instances across all providers and keeps DB in sync."""

    def __init__(self):
        self._cache: Dict[str, GPUInstanceInfo] = {}
        self._last_sync: Optional[datetime] = None

    async def sync(self, db: AsyncSession) -> int:
        """Fetch all instances from providers and upsert into DB. Returns synced count."""
        all_instances: List[GPUInstanceInfo] = []

        for provider in provider_registry.all():
            try:
                instances = await provider.list_available_instances()
                all_instances.extend(instances)
            except Exception as exc:
                logger.warning("Failed to sync provider %s: %s", provider.provider, exc)

        if not all_instances:
            return 0

        # Update in-memory cache
        self._cache = {inst.id: inst for inst in all_instances}

        # Upsert into PostgreSQL
        for inst in all_instances:
            stmt = (
                pg_insert(GPUInstance)
                .values(
                    id=inst.id,
                    provider=inst.provider,
                    region=inst.region,
                    zone=inst.zone,
                    instance_type=inst.instance_type,
                    gpu_type=inst.gpu_type,
                    gpu_count=inst.gpu_count,
                    gpu_memory_gb=inst.gpu_memory_gb,
                    cpu_count=inst.cpu_count,
                    memory_gb=inst.memory_gb,
                    status=inst.status,
                    is_spot=inst.is_spot,
                    on_demand_price_hour=inst.on_demand_price_hour,
                    spot_price_hour=inst.spot_price_hour,
                    last_seen=datetime.utcnow(),
                )
                .on_conflict_do_update(
                    index_elements=["id"],
                    set_={
                        "status": inst.status,
                        "is_spot": inst.is_spot,
                        "spot_price_hour": inst.spot_price_hour,
                        "last_seen": datetime.utcnow(),
                    },
                )
            )
            await db.execute(stmt)

        self._last_sync = datetime.utcnow()
        return len(all_instances)

    async def get_available_instances(
        self,
        db: AsyncSession,
        gpu_type: Optional[str] = None,
        min_gpu_count: int = 1,
        min_gpu_memory_gb: Optional[int] = None,
        provider: Optional[str] = None,
        regions: Optional[List[str]] = None,
        excluded_regions: Optional[List[str]] = None,
    ) -> List[GPUInstance]:
        """Query available GPU instances matching the given constraints."""
        query = select(GPUInstance).where(GPUInstance.status == InstanceStatus.AVAILABLE)

        if gpu_type and gpu_type != "any":
            query = query.where(GPUInstance.gpu_type == gpu_type)
        if min_gpu_count > 1:
            query = query.where(GPUInstance.gpu_count >= min_gpu_count)
        if min_gpu_memory_gb:
            query = query.where(GPUInstance.gpu_memory_gb >= min_gpu_memory_gb)
        if provider:
            query = query.where(GPUInstance.provider == provider)
        if regions:
            query = query.where(GPUInstance.region.in_(regions))
        if excluded_regions:
            query = query.where(GPUInstance.region.notin_(excluded_regions))

        result = await db.execute(query)
        return result.scalars().all()

    async def mark_allocated(self, db: AsyncSession, instance_id: str) -> bool:
        """Mark an instance as allocated."""
        result = await db.execute(
            update(GPUInstance)
            .where(GPUInstance.id == instance_id)
            .values(status=InstanceStatus.ALLOCATED)
            .returning(GPUInstance.id)
        )
        return result.scalar_one_or_none() is not None

    async def mark_available(self, db: AsyncSession, instance_id: str) -> bool:
        """Release an instance back to available."""
        result = await db.execute(
            update(GPUInstance)
            .where(GPUInstance.id == instance_id)
            .values(status=InstanceStatus.AVAILABLE)
            .returning(GPUInstance.id)
        )
        return result.scalar_one_or_none() is not None

    def get_provider_summary(self) -> Dict[str, Any]:
        """Summarise inventory from cache without hitting DB."""
        by_provider: Dict[str, Dict] = {}
        for inst in self._cache.values():
            p = inst.provider
            if p not in by_provider:
                by_provider[p] = {
                    "total": 0,
                    "available": 0,
                    "total_gpus": 0,
                    "available_gpus": 0,
                    "regions": set(),
                    "gpu_types": {},
                }
            d = by_provider[p]
            d["total"] += 1
            d["regions"].add(inst.region)
            if inst.gpu_type not in d["gpu_types"]:
                d["gpu_types"][inst.gpu_type] = 0
            if inst.status == "available":
                d["available"] += 1
                d["available_gpus"] += inst.gpu_count
                d["gpu_types"][inst.gpu_type] += inst.gpu_count
            d["total_gpus"] += inst.gpu_count

        return by_provider

    @property
    def last_sync(self) -> Optional[datetime]:
        return self._last_sync

    @property
    def cached_count(self) -> int:
        return len(self._cache)


inventory_manager = InventoryManager()
