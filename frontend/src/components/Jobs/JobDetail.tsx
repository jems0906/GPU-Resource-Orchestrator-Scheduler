import { useJob, useJobMetrics, useCancelJob, useScaleJob } from '@/hooks/useJobs'
import { useJobWebSocket } from '@/hooks/useWebSocket'
import { StatusBadge } from '@/components/common/StatusBadge'
import { GPUUtilizationChart } from '@/components/Dashboard/GPUUtilizationChart'
import { PageLoader } from '@/components/common/LoadingSpinner'
import { format } from 'date-fns'
import { XCircle, Zap, AlertTriangle } from 'lucide-react'
import { useState } from 'react'
import type { JobStatus } from '@/types'

interface Props {
  jobId: string
}

export function JobDetail({ jobId }: Props) {
  const { data: job, isLoading } = useJob(jobId)
  const { data: metrics } = useJobMetrics(jobId)
  const cancelJob = useCancelJob()
  const scaleJob = useScaleJob()
  const wsData = useJobWebSocket(jobId) as Record<string, number> | null
  const [scaleGpu, setScaleGpu] = useState<number>(1)

  if (isLoading || !job) return <PageLoader />

  const isActive = !['completed', 'cancelled', 'failed'].includes(job.status)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-surface-800 rounded-xl p-6">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <h2 className="text-white text-xl font-bold">{job.name}</h2>
              <StatusBadge status={job.status as JobStatus} />
              {job.use_spot && (
                <span className="flex items-center gap-1 text-xs text-emerald-400">
                  <Zap className="w-3 h-3" /> Spot
                </span>
              )}
            </div>
            {job.model && <p className="text-slate-400 text-sm">{job.model}</p>}
            <p className="text-slate-500 text-xs mt-1">ID: {job.id}</p>
          </div>

          {isActive && (
            <button
              onClick={() => cancelJob.mutate(job.id)}
              disabled={cancelJob.isPending}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-rose-900/50 hover:bg-rose-900 text-rose-300 rounded-lg text-xs font-medium transition-colors"
            >
              <XCircle className="w-3.5 h-3.5" />
              Cancel
            </button>
          )}
        </div>

        {/* Info grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-5 pt-5 border-t border-surface-700">
          <Stat label="GPU Type" value={job.gpu_type ?? 'Any'} />
          <Stat label="GPU Count" value={`${job.gpu_count}×`} />
          <Stat label="Priority" value={`P${job.priority}`} />
          <Stat label="Type" value={job.job_type} />
          <Stat label="Submitted" value={format(new Date(job.created_at), 'MMM d, HH:mm')} />
          <Stat label="Started" value={job.started_at ? format(new Date(job.started_at), 'MMM d, HH:mm') : '—'} />
          <Stat label="Est. Cost" value={job.estimated_cost != null ? `$${job.estimated_cost.toFixed(4)}` : '—'} />
          <Stat label="Actual Cost" value={job.actual_cost != null ? `$${job.actual_cost.toFixed(4)}` : '—'} />
        </div>

        {/* Progress bar */}
        {job.progress != null && (
          <div className="mt-4">
            <div className="flex justify-between text-xs text-slate-400 mb-1">
              <span>Progress</span>
              <span>{job.progress.toFixed(1)}%</span>
            </div>
            <progress
              max={100}
              value={Math.min(100, job.progress)}
              className="job-progress w-full h-2"
            />
          </div>
        )}

        {/* Live metrics from WS */}
        {wsData && (
          <div className="flex gap-6 mt-4 text-sm">
            {wsData.gpu_utilization != null && (
              <span className="text-slate-400">
                GPU: <span className="text-blue-400 font-medium">{wsData.gpu_utilization.toFixed(1)}%</span>
              </span>
            )}
            {wsData.cost_so_far != null && (
              <span className="text-slate-400">
                Cost: <span className="text-emerald-400 font-medium">${wsData.cost_so_far.toFixed(4)}</span>
              </span>
            )}
          </div>
        )}
      </div>

      {/* Instance info */}
      {job.instance && (
        <div className="bg-surface-800 rounded-xl p-6">
          <h3 className="text-white font-semibold mb-3">Allocated Instance</h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <Stat label="Provider" value={job.instance.provider.toUpperCase()} />
            <Stat label="Region" value={job.instance.region} />
            <Stat label="Instance Type" value={job.instance.instance_type} />
            <Stat label="$/hr" value={`$${job.instance.price_per_hour.toFixed(3)}`} />
          </div>
        </div>
      )}

      {/* Scale controls */}
      {job.status === 'running' && (
        <div className="bg-surface-800 rounded-xl p-6">
          <h3 className="text-white font-semibold mb-3 flex items-center gap-2">
            <Zap className="w-4 h-4 text-amber-400" />
            Scale Job
          </h3>
          <div className="flex items-center gap-3">
            <input
              type="number"
              min={1}
              max={64}
              aria-label="GPU count to scale to"
              placeholder="GPU count"
              value={scaleGpu}
              onChange={(e) => setScaleGpu(Number(e.target.value))}
              className="w-24 bg-surface-700 rounded-lg px-3 py-2 text-white text-sm border border-surface-600 focus:outline-none focus:border-primary-500"
            />
            <span className="text-slate-400 text-sm">GPUs</span>
            <button
              onClick={() => scaleJob.mutate({ id: job.id, gpu_count: scaleGpu })}
              disabled={scaleJob.isPending}
              className="px-4 py-2 bg-amber-700 hover:bg-amber-600 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-60"
            >
              {scaleJob.isPending ? 'Scaling…' : 'Scale'}
            </button>
          </div>
        </div>
      )}

      {/* Metrics chart */}
      {metrics && metrics.length > 0 ? (
        <div className="bg-surface-800 rounded-xl p-6">
          <h3 className="text-white font-semibold mb-4">Live Metrics</h3>
          <GPUUtilizationChart metrics={metrics} />
        </div>
      ) : (
        <div className="bg-surface-800 rounded-xl p-6 flex items-center gap-3 text-slate-500">
          <AlertTriangle className="w-4 h-4" />
          <span className="text-sm">No metrics available yet</span>
        </div>
      )}
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-slate-500 text-xs">{label}</p>
      <p className="text-slate-200 text-sm font-medium mt-0.5">{value}</p>
    </div>
  )
}
