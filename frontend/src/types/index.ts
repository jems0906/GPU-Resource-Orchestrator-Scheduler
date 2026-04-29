// ─── Enums ────────────────────────────────────────────────────────────────────

export type JobStatus =
  | 'queued'
  | 'pending'
  | 'running'
  | 'completed'
  | 'failed'
  | 'cancelled'
  | 'failover'

export type JobType = 'training' | 'inference' | 'batch' | 'fine_tuning'

export type GPUType =
  | 'A100-40GB'
  | 'A100-80GB'
  | 'V100-16GB'
  | 'V100-32GB'
  | 'T4-16GB'
  | 'A10G-24GB'
  | 'any'

export type CloudProvider = 'aws' | 'gcp' | 'azure'

// ─── Jobs ─────────────────────────────────────────────────────────────────────

export interface GPUInstanceBrief {
  id: string
  provider: CloudProvider
  region: string
  instance_type: string
  gpu_type: GPUType
  gpu_count: number
  gpu_memory_gb: number
  is_spot: boolean
  price_per_hour: number
}

export interface Job {
  id: string
  name: string
  model?: string
  job_type: JobType
  status: JobStatus
  priority: number
  gpu_type?: GPUType
  gpu_count: number
  gpu_memory_gb?: number
  preferred_regions?: string[]
  budget?: number
  sla_deadline?: string
  use_spot: boolean
  instance?: GPUInstanceBrief
  estimated_cost?: number
  actual_cost?: number
  progress?: number
  estimated_duration_hours?: number
  retry_count: number
  error_message?: string
  job_metadata?: Record<string, unknown>
  allocated_at?: string
  started_at?: string
  completed_at?: string
  created_at: string
  updated_at?: string
}

export interface JobCreate {
  name: string
  model?: string
  job_type: JobType
  priority: number
  gpu_type?: GPUType
  gpu_count: number
  gpu_memory_gb?: number
  preferred_regions?: string[]
  excluded_regions?: string[]
  budget?: number
  sla_deadline?: string
  use_spot: boolean
  estimated_duration_hours?: number
  job_metadata?: Record<string, unknown>
}

export interface JobListResponse {
  jobs: Job[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface JobMetric {
  timestamp: string
  gpu_utilization?: number
  gpu_memory_used_gb?: number
  gpu_memory_total_gb?: number
  cpu_utilization?: number
  throughput?: number
  cost_so_far?: number
}

// ─── Providers & Inventory ────────────────────────────────────────────────────

export interface GPUInstanceSchema {
  id: string
  provider: CloudProvider
  region: string
  zone?: string
  instance_type: string
  gpu_type: GPUType
  gpu_count: number
  gpu_memory_gb: number
  cpu_count: number
  memory_gb: number
  status: string
  is_spot: boolean
  on_demand_price_hour: number
  spot_price_hour?: number
  allocated_gpu_count: number
  last_seen?: string
}

export interface ProviderSummary {
  provider: CloudProvider
  total_instances: number
  available_instances: number
  allocated_instances: number
  total_gpus: number
  available_gpus: number
  regions: string[]
  gpu_types: Record<string, number>
  estimated_hourly_cost_if_full: number
}

export interface InventoryResponse {
  providers: ProviderSummary[]
  total_instances: number
  total_available_gpus: number
  instances: GPUInstanceSchema[]
  last_updated: string
}

export interface PricingInfo {
  provider: CloudProvider
  region: string
  instance_type: string
  gpu_type: GPUType
  gpu_count: number
  on_demand_price_hour: number
  spot_price_hour?: number
  spot_savings_percent?: number
}

// ─── Metrics ──────────────────────────────────────────────────────────────────

export interface QueueMetrics {
  total_queued: number
  total_running: number
  total_completed_today: number
  total_failed_today: number
  average_wait_time_minutes: number
  average_run_time_minutes: number
  jobs_by_status: Record<string, number>
  jobs_by_priority: Record<string, number>
}

export interface SLAMetrics {
  total_jobs_with_sla: number
  sla_compliant: number
  sla_violated: number
  sla_at_risk: number
  compliance_percent: number
  active_violations: Array<Record<string, unknown>>
}

export interface CostSummary {
  total_cost_today: number
  total_cost_this_month: number
  total_cost_all_time: number
  total_savings_from_spot: number
  savings_percent: number
  cost_by_provider: Record<string, number>
  cost_by_gpu_type: Record<string, number>
  average_cost_per_job: number
}

export interface GPUUtilizationPoint {
  timestamp: string
  provider: CloudProvider
  region: string
  gpu_type: GPUType
  utilization_percent: number
  memory_used_gb: number
  memory_total_gb: number
}

export interface DashboardMetrics {
  queue: QueueMetrics
  sla: SLAMetrics
  cost: CostSummary
  gpu_utilization: GPUUtilizationPoint[]
  active_jobs_count: number
  total_gpus_available: number
  total_gpus_in_use: number
  timestamp: string
}

export interface CostDataPoint {
  date: string
  provider: CloudProvider
  cost: number
  spot_cost: number
  on_demand_cost: number
  savings: number
}
