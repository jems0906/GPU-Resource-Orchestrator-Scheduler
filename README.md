# GPU Resource Orchestrator & Scheduler

Multi-cloud GPU job scheduling platform with cost/performance optimization.

## Stack

- Backend: FastAPI, SQLAlchemy async, PostgreSQL, Redis
- Frontend: React + TypeScript + Vite + Tailwind
- Providers: AWS, GCP, Azure (mock provider implementations behind pluggable interfaces)
- Orchestration: Docker Compose

## Project Layout

- `backend/` FastAPI service and scheduler engine
- `frontend/` React dashboard and job workflow UI
- `docker-compose.yml` local full-stack runtime
- `.env.example` configurable environment values

## Quick Start (Docker)

1. Create environment file:

```powershell
Set-Location "d:\project\GPU Resource Orchestrator & Scheduler"
Copy-Item .env.example .env
```

2. Build and run:

```powershell
docker compose up --build -d
```

3. Open apps:

- Frontend: http://localhost
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

4. Stop stack:

```powershell
docker compose down
```

## Local Dev (Without Docker)

### One-Command Startup (Windows)

The workspace path on this machine can block direct Python and Node execution. Use the repo launcher instead:

```powershell
Set-Location "d:\project\GPU Resource Orchestrator & Scheduler"
.\start-local-dev.ps1
```

This launcher:

- starts the local PostgreSQL and Redis containers if they already exist
- boots the backend with `C:\temp\gpu_orchestrator_py311`
- syncs frontend source into `C:\temp\gpu_orchestrator_frontend`
- builds the frontend and serves it on `http://localhost:5174`
- targets the backend on `http://localhost:8011`

Logs are written to `%TEMP%\gpu-orchestrator-backend.log` and `%TEMP%\gpu-orchestrator-frontend.log`.

### Backend

```powershell
Set-Location "d:\project\GPU Resource Orchestrator & Scheduler\backend"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```powershell
Set-Location "d:\project\GPU Resource Orchestrator & Scheduler\frontend"
npm install
npm run dev
```

## API Authentication

Use header `X-API-Key` and match `DEFAULT_API_KEY` in environment.
Default development value is in `.env.example`.

## Docker Desktop Proxy Fix (If Image Pull Fails)

If you see errors such as:

- `lookup http.docker.internal ... i/o timeout`
- `failed to resolve source metadata for docker.io/library/...`

then Docker daemon proxy is configured to an unreachable host.

### Fix in Docker Desktop UI

1. Open Docker Desktop.
2. Go to Settings -> Resources -> Proxies.
3. Disable manual proxy, or set valid reachable proxy endpoints.
4. Apply & Restart Docker Desktop.

### Verify

```powershell
docker info
```

Check `HTTP Proxy` / `HTTPS Proxy` fields. They should be empty or valid.

Then retry:

```powershell
Set-Location "d:\project\GPU Resource Orchestrator & Scheduler"
docker compose up --build -d
```

## Notes

- Provider modules currently use deterministic mock data and can be replaced with cloud SDK integrations.
- Scheduler loop interval and spot behavior are configurable in environment.
