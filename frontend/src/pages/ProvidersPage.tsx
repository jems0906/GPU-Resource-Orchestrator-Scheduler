import { ProviderGrid } from '@/components/Providers/ProviderGrid'
import { useInventory, useProviderHealth } from '@/hooks/useProviders'
import { PageLoader } from '@/components/common/LoadingSpinner'
import { useEffect, useState } from 'react'

const INVENTORY_REFRESH_INTERVAL_SECONDS = 15

function formatLastSync(value?: string) {
  if (!value) return 'unknown'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'unknown'

  const now = Date.now()
  const diffMs = now - date.getTime()
  const diffSeconds = Math.floor(Math.abs(diffMs) / 1000)

  if (diffSeconds < 10) return 'just now'
  if (diffSeconds < 60) return `${diffSeconds}s ago`

  const diffMinutes = Math.floor(diffSeconds / 60)
  if (diffMinutes < 60) return `${diffMinutes}m ago`

  const diffHours = Math.floor(diffMinutes / 60)
  if (diffHours < 24) return `${diffHours}h ago`

  const diffDays = Math.floor(diffHours / 24)
  return `${diffDays}d ago`
}

function OverallHealthBadge({ total, healthy, unknown }: { total: number; healthy: number; unknown: number }) {
  const unhealthy = Math.max(total - healthy - unknown, 0)

  if (total === 0 || unknown > 0) {
    return (
      <span className="inline-flex items-center rounded-full border border-amber-500/50 bg-amber-500/10 px-2 py-0.5 text-[11px] font-medium text-amber-300">
        Unknown
      </span>
    )
  }

  if (unhealthy === 0) {
    return (
      <span className="inline-flex items-center rounded-full border border-emerald-500/50 bg-emerald-500/10 px-2 py-0.5 text-[11px] font-medium text-emerald-300">
        Healthy
      </span>
    )
  }

  return (
    <span className="inline-flex items-center rounded-full border border-rose-500/50 bg-rose-500/10 px-2 py-0.5 text-[11px] font-medium text-rose-300">
      Degraded
    </span>
  )
}

export default function ProvidersPage() {
  const { data: inventory, isLoading: inventoryLoading, dataUpdatedAt, isFetching } = useInventory()
  const { data: health } = useProviderHealth()
  const [refreshCountdown, setRefreshCountdown] = useState(INVENTORY_REFRESH_INTERVAL_SECONDS)

  useEffect(() => {
    if (isFetching) {
      return
    }

    const tick = () => {
      if (!dataUpdatedAt) {
        setRefreshCountdown(INVENTORY_REFRESH_INTERVAL_SECONDS)
        return
      }

      const elapsedMs = Date.now() - dataUpdatedAt
      const remainingMs = Math.max(INVENTORY_REFRESH_INTERVAL_SECONDS * 1000 - elapsedMs, 0)
      setRefreshCountdown(Math.ceil(remainingMs / 1000))
    }

    tick()
    const intervalId = window.setInterval(tick, 1000)
    return () => window.clearInterval(intervalId)
  }, [dataUpdatedAt, isFetching])

  if (inventoryLoading || !inventory) {
    return (
      <div className="space-y-4">
        <h2 className="text-white font-bold text-lg">Cloud Providers</h2>
        <PageLoader />
      </div>
    )
  }

  const totalProviders = inventory.providers?.length ?? 0
  const knownHealth = health?.providers ?? {}
  const healthyProviders = Object.values(knownHealth).filter(Boolean).length
  const unknownProviders = Math.max(totalProviders - Object.keys(knownHealth).length, 0)
  const totalInstances = inventory.total_instances ?? 0
  const totalAvailableGpus = inventory.total_available_gpus ?? 0

  return (
    <div className="space-y-4">
      <h2 className="text-white font-bold text-lg">Cloud Providers</h2>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-3">
        <div className="rounded-xl border border-surface-600 bg-surface-800 px-4 py-3">
          <p className="text-xs uppercase tracking-wide text-slate-500">Providers</p>
          <p className="text-white text-xl font-semibold mt-1">{totalProviders}</p>
        </div>
        <div className="rounded-xl border border-surface-600 bg-surface-800 px-4 py-3">
          <p className="text-xs uppercase tracking-wide text-slate-500">Healthy</p>
          <div className="mt-1 flex items-center gap-2">
            <p className="text-white text-xl font-semibold">{healthyProviders}/{totalProviders}</p>
            <OverallHealthBadge total={totalProviders} healthy={healthyProviders} unknown={unknownProviders} />
          </div>
        </div>
        <div className="rounded-xl border border-surface-600 bg-surface-800 px-4 py-3">
          <p className="text-xs uppercase tracking-wide text-slate-500">Total Instances</p>
          <p className="text-white text-xl font-semibold mt-1">{totalInstances}</p>
        </div>
        <div className="rounded-xl border border-surface-600 bg-surface-800 px-4 py-3">
          <p className="text-xs uppercase tracking-wide text-slate-500">Available GPUs</p>
          <p className="text-white text-xl font-semibold mt-1">{totalAvailableGpus}</p>
        </div>
        <div className="rounded-xl border border-surface-600 bg-surface-800 px-4 py-3 sm:col-span-2 xl:col-span-1">
          <p className="text-xs uppercase tracking-wide text-slate-500">Last Sync</p>
          <p className="text-slate-200 text-sm font-medium mt-1">{formatLastSync(inventory.last_updated)}</p>
          <p className="text-slate-500 text-xs mt-1">
            {isFetching ? 'Refreshing now...' : `Auto-refresh in ${refreshCountdown}s`}
          </p>
        </div>
      </div>

      <ProviderGrid inventory={inventory} health={health} isLoading={inventoryLoading} />
    </div>
  )
}
