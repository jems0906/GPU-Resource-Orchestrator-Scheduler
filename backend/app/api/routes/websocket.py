"""WebSocket endpoint for real-time job status and metrics streaming."""

import asyncio
import json
import logging
from typing import Dict, Set
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.db.models import Job
from app.queue.redis_queue import redis_queue

router = APIRouter(tags=["websocket"])
logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections per job ID and global listeners."""

    def __init__(self):
        self.job_connections: Dict[str, Set[WebSocket]] = {}
        self.global_connections: Set[WebSocket] = set()

    async def connect_job(self, job_id: str, ws: WebSocket) -> None:
        await ws.accept()
        if job_id not in self.job_connections:
            self.job_connections[job_id] = set()
        self.job_connections[job_id].add(ws)

    async def connect_global(self, ws: WebSocket) -> None:
        await ws.accept()
        self.global_connections.add(ws)

    def disconnect_job(self, job_id: str, ws: WebSocket) -> None:
        if job_id in self.job_connections:
            self.job_connections[job_id].discard(ws)

    def disconnect_global(self, ws: WebSocket) -> None:
        self.global_connections.discard(ws)

    async def broadcast_job(self, job_id: str, data: dict) -> None:
        if job_id not in self.job_connections:
            return
        dead: Set[WebSocket] = set()
        for ws in self.job_connections[job_id]:
            try:
                await ws.send_json(data)
            except Exception:
                dead.add(ws)
        self.job_connections[job_id] -= dead

    async def broadcast_global(self, data: dict) -> None:
        dead: Set[WebSocket] = set()
        for ws in self.global_connections:
            try:
                await ws.send_json(data)
            except Exception:
                dead.add(ws)
        self.global_connections -= dead


ws_manager = ConnectionManager()


@router.websocket("/ws/jobs/{job_id}")
async def job_websocket(job_id: str, websocket: WebSocket):
    """
    Stream real-time status and metrics for a specific job.
    Sends an update every 2 seconds.
    """
    await ws_manager.connect_job(job_id, websocket)
    try:
        while True:
            # Send latest metrics from Redis
            status = await redis_queue.get_job_status(job_id)
            metrics = await redis_queue.get_metrics(job_id)

            payload = {
                "job_id": job_id,
                "status": status,
                "metrics": metrics,
            }
            await websocket.send_json(payload)
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        ws_manager.disconnect_job(job_id, websocket)
    except Exception as exc:
        logger.warning("WebSocket error for job %s: %s", job_id, exc)
        ws_manager.disconnect_job(job_id, websocket)


@router.websocket("/ws/dashboard")
async def dashboard_websocket(websocket: WebSocket):
    """
    Stream global dashboard events (job submissions, completions, SLA alerts).
    Sends a heartbeat every 3 seconds.
    """
    await ws_manager.connect_global(websocket)
    try:
        while True:
            depth = await redis_queue.queue_depth()
            payload = {
                "type": "heartbeat",
                "queue_depth": depth,
            }
            await websocket.send_json(payload)
            await asyncio.sleep(3)
    except WebSocketDisconnect:
        ws_manager.disconnect_global(websocket)
    except Exception as exc:
        logger.warning("Dashboard WebSocket error: %s", exc)
        ws_manager.disconnect_global(websocket)
