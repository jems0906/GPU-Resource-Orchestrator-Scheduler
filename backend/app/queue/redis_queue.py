"""
Redis-backed job queue with priority support.
Uses a sorted set (ZSET) scored by priority + submission time for sub-second placement.
"""

import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger(__name__)


class RedisQueue:
    """Priority job queue backed by Redis sorted set."""

    def __init__(self):
        self._client: Optional[aioredis.Redis] = None

    async def connect(self) -> None:
        self._client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
        await self._client.ping()
        logger.info("Redis connected at %s", settings.REDIS_URL)

    async def disconnect(self) -> None:
        if self._client:
            await self._client.aclose()

    async def enqueue(self, job_id: str, priority: int, job_data: Dict[str, Any]) -> None:
        """Add job to the priority queue. Higher priority = processed first."""
        if not self._client:
            raise RuntimeError("Redis not connected")
        # Score = priority * 1e12 - timestamp_micros (higher priority, earlier first)
        timestamp_us = int(datetime.utcnow().timestamp() * 1_000_000)
        score = priority * 1_000_000_000_000 - timestamp_us

        pipe = self._client.pipeline()
        pipe.zadd(settings.QUEUE_KEY, {job_id: score})
        pipe.setex(
            f"{settings.JOB_STATUS_PREFIX}{job_id}",
            3600 * settings.METRICS_RETENTION_HOURS,
            json.dumps(job_data),
        )
        await pipe.execute()

    async def dequeue(self, count: int = 10) -> List[str]:
        """Pop the highest-priority job IDs from the queue."""
        if not self._client:
            return []
        # ZPOPMAX returns highest scores first
        items = await self._client.zpopmax(settings.QUEUE_KEY, count)
        return [item[0] for item in items]  # (member, score) pairs

    async def peek(self, count: int = 50) -> List[str]:
        """Inspect queue without removing items."""
        if not self._client:
            return []
        return await self._client.zrevrange(settings.QUEUE_KEY, 0, count - 1)

    async def remove(self, job_id: str) -> bool:
        """Remove a specific job from the queue (e.g., on cancellation)."""
        if not self._client:
            return False
        result = await self._client.zrem(settings.QUEUE_KEY, job_id)
        return bool(result)

    async def queue_depth(self) -> int:
        if not self._client:
            return 0
        return await self._client.zcard(settings.QUEUE_KEY)

    async def set_job_status(self, job_id: str, status_data: Dict[str, Any]) -> None:
        if not self._client:
            return
        status_data["updated_at"] = datetime.utcnow().isoformat()
        await self._client.setex(
            f"{settings.JOB_STATUS_PREFIX}{job_id}",
            3600 * settings.METRICS_RETENTION_HOURS,
            json.dumps(status_data, default=str),
        )

    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        if not self._client:
            return None
        raw = await self._client.get(f"{settings.JOB_STATUS_PREFIX}{job_id}")
        if raw:
            return json.loads(raw)
        return None

    async def publish_job_event(self, channel: str, event: Dict[str, Any]) -> None:
        """Publish a job event for real-time WebSocket subscribers."""
        if not self._client:
            return
        await self._client.publish(channel, json.dumps(event, default=str))

    async def push_metrics(self, job_id: str, metrics: Dict[str, Any]) -> None:
        """Store latest metrics snapshot for a job, with TTL."""
        if not self._client:
            return
        key = f"{settings.JOB_METRICS_PREFIX}{job_id}"
        await self._client.setex(
            key,
            3600 * 24,  # keep for 24 hours
            json.dumps(metrics, default=str),
        )

    async def get_metrics(self, job_id: str) -> Optional[Dict[str, Any]]:
        if not self._client:
            return None
        raw = await self._client.get(f"{settings.JOB_METRICS_PREFIX}{job_id}")
        if raw:
            return json.loads(raw)
        return None

    @property
    def client(self) -> Optional[aioredis.Redis]:
        return self._client


redis_queue = RedisQueue()
