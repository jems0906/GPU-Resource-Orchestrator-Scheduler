import axios from 'axios'
import type {
  Job,
  JobCreate,
  JobListResponse,
  JobMetric,
  InventoryResponse,
  PricingInfo,
  DashboardMetrics,
  CostDataPoint,
} from '@/types'

function normalizeApiBaseUrl(raw: string | undefined): string {
  if (!raw) return '/api/v1'
  const trimmed = raw.replace(/\/$/, '')
  return trimmed.endsWith('/api/v1') ? trimmed : `${trimmed}/api/v1`
}

const BASE_URL = normalizeApiBaseUrl(import.meta.env.VITE_API_BASE_URL)
const API_KEY = import.meta.env.VITE_API_KEY || 'dev-api-key-change-in-production'

export const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': API_KEY,
  },
})

// ─── Jobs ─────────────────────────────────────────────────────────────────────

export const jobsApi = {
  submit: (data: JobCreate): Promise<Job> =>
    apiClient.post<Job>('/jobs/', data).then((r) => r.data),

  list: (params?: {
    status?: string
    job_type?: string
    priority_min?: number
    page?: number
    page_size?: number
  }): Promise<JobListResponse> =>
    apiClient.get<JobListResponse>('/jobs/', { params }).then((r) => r.data),

  get: (id: string): Promise<Job> =>
    apiClient.get<Job>(`/jobs/${id}`).then((r) => r.data),

  cancel: (id: string): Promise<{ job_id: string; status: string; message: string }> =>
    apiClient.delete(`/jobs/${id}`).then((r) => r.data),

  update: (
    id: string,
    data: { priority?: number; budget?: number; sla_deadline?: string },
  ): Promise<Job> => apiClient.patch<Job>(`/jobs/${id}`, data).then((r) => r.data),

  scale: (id: string, gpu_count: number, reason?: string): Promise<Job> =>
    apiClient.post<Job>(`/jobs/${id}/scale`, { gpu_count, reason }).then((r) => r.data),

  metrics: (id: string, limit = 60): Promise<JobMetric[]> =>
    apiClient.get<JobMetric[]>(`/jobs/${id}/metrics`, { params: { limit } }).then((r) => r.data),
}

// ─── Providers & Inventory ────────────────────────────────────────────────────

export const providersApi = {
  inventory: (params?: {
    provider?: string
    region?: string
    gpu_type?: string
    available_only?: boolean
  }): Promise<InventoryResponse> =>
    apiClient.get<InventoryResponse>('/providers/inventory', { params }).then((r) => r.data),

  health: (): Promise<{ providers: Record<string, boolean>; all_healthy: boolean }> =>
    apiClient.get('/providers/health').then((r) => r.data),

  pricing: (params?: { provider?: string; gpu_type?: string }): Promise<PricingInfo[]> =>
    apiClient.get<PricingInfo[]>('/providers/pricing', { params }).then((r) => r.data),
}

// ─── Metrics ──────────────────────────────────────────────────────────────────

export const metricsApi = {
  dashboard: (): Promise<DashboardMetrics> =>
    apiClient.get<DashboardMetrics>('/metrics/dashboard').then((r) => r.data),

  costHistory: (days = 30): Promise<CostDataPoint[]> =>
    apiClient
      .get<CostDataPoint[]>('/metrics/cost-history', { params: { days } })
      .then((r) => r.data),

  queueDepth: (): Promise<{ queue_depth: number; top_job_ids: string[] }> =>
    apiClient.get('/metrics/queue-depth').then((r) => r.data),
}
