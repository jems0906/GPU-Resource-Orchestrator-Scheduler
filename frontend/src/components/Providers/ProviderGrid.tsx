import { useInventory, useProviderHealth } from '@/hooks/useProviders'
import { PageLoader } from '@/components/common/LoadingSpinner'
import { CheckCircle, XCircle, AlertCircle, Cpu, MemoryStick } from 'lucide-react'
import type { InventoryResponse, ProviderSummary } from '@/types'

const PROVIDER_GRADIENT: Record<string, string> = {
  aws: 'from-amber-900/30 to-surface-800',
  gcp: 'from-blue-900/30 to-surface-800',
  azure: 'from-purple-900/30 to-surface-800',
}

function HealthIcon({ healthy }: { healthy: boolean | null }) {
  if (healthy === null) return <AlertCircle className="w-4 h-4 text-slate-500" />
  return healthy ? (
    <CheckCircle className="w-4 h-4 text-emerald-400" />
  ) : (
    <XCircle className="w-4 h-4 text-rose-400" />
  )
}

function HealthBadge({ healthy }: { healthy: boolean | null }) {
  if (healthy === null) {
    return (
      <span className="inline-flex items-center rounded-full border border-amber-500/50 bg-amber-500/10 px-2 py-0.5 text-[11px] font-medium text-amber-300">
        Unknown
      </span>
    )
  }

  if (healthy) {
    return (
      <span className="inline-flex items-center rounded-full border border-emerald-500/50 bg-emerald-500/10 px-2 py-0.5 text-[11px] font-medium text-emerald-300">
        Healthy
      </span>
    )
  }

  return (
    <span className="inline-flex items-center rounded-full border border-rose-500/50 bg-rose-500/10 px-2 py-0.5 text-[11px] font-medium text-rose-300">
      Unhealthy
    </span>
  )
}

function ProviderCard({ summary, healthy }: { summary: ProviderSummary; healthy: boolean | null }) {
  const totalInstances = summary.total_instances ?? 0
  const allocatedInstances = summary.allocated_instances ?? 0
  const regions = summary.regions ?? []
  const gpuTypes = summary.gpu_types ?? {}
  const utilPct = totalInstances > 0 ? (allocatedInstances / totalInstances) * 100 : 0

  return (
    <div
      className={`bg-gradient-to-b ${PROVIDER_GRADIENT[summary.provider] ?? 'from-surface-700 to-surface-800'} border border-surface-600 rounded-xl p-5`}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-white font-bold text-lg uppercase tracking-wider">{summary.provider}</h3>
            <HealthBadge healthy={healthy} />
          </div>
          <p className="text-slate-400 text-xs">{regions.length > 0 ? regions.join(' · ') : 'No regions synced'}</p>
        </div>
        <HealthIcon healthy={healthy} />
      </div>

      {/* Utilization bar */}
      <div className="mb-4">
        <div className="flex justify-between text-xs text-slate-400 mb-1">
          <span>Instance Utilization</span>
          <span>
            {allocatedInstances}/{totalInstances}
          </span>
        </div>
        <progress
          max={100}
          value={utilPct}
          className="provider-util w-full h-2"
        />
        <p className="text-xs text-slate-500 mt-1">{utilPct.toFixed(1)}% allocated</p>
      </div>

      {/* GPU type breakdown */}
      <div>
        <p className="text-xs text-slate-500 uppercase tracking-wide mb-2">GPU Types Available</p>
        <div className="flex flex-wrap gap-1.5">
          {Object.keys(gpuTypes).length > 0 ? (
            Object.entries(gpuTypes).map(([g, count]) => (
              <span
                key={g}
                className="px-2 py-0.5 bg-surface-700 text-slate-300 rounded text-xs"
              >
                {g} <span className="text-slate-500">×{count}</span>
              </span>
            ))
          ) : (
            <span className="text-slate-600 text-xs">No instances</span>
          )}
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-3 mt-4 pt-4 border-t border-surface-600">
        <div className="flex items-center gap-2">
          <Cpu className="w-3.5 h-3.5 text-slate-500" />
          <div>
            <p className="text-xs text-slate-500">Total GPUs</p>
            <p className="text-white text-sm font-medium">{summary.total_gpus ?? '—'}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <MemoryStick className="w-3.5 h-3.5 text-slate-500" />
          <div>
            <p className="text-xs text-slate-500">Est. Full Cost/hr</p>
            <p className="text-white text-sm font-medium">
              {summary.estimated_hourly_cost_if_full != null
                ? `$${summary.estimated_hourly_cost_if_full.toFixed(2)}`
                : '—'}
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

interface ProviderGridProps {
  inventory?: InventoryResponse
  health?: { providers: Record<string, boolean>; all_healthy: boolean }
  isLoading?: boolean
}

export function ProviderGrid({ inventory: inventoryProp, health: healthProp, isLoading: isLoadingProp }: ProviderGridProps = {}) {
  const inventoryQuery = useInventory()
  const healthQuery = useProviderHealth()

  const inventory = inventoryProp ?? inventoryQuery.data
  const health = healthProp ?? healthQuery.data
  const isLoading = isLoadingProp ?? inventoryQuery.isLoading

  if (isLoading || !inventory) return <PageLoader />

  const providers = inventory.providers ?? []

  if (providers.length === 0) {
    return (
      <div className="rounded-xl border border-surface-600 bg-surface-800 p-6 text-center text-slate-400">
        No provider inventory data available yet
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
      {providers.map((summary) => (
        <ProviderCard
          key={summary.provider}
          summary={summary}
          healthy={health?.providers[summary.provider] ?? null}
        />
      ))}
    </div>
  )
}
