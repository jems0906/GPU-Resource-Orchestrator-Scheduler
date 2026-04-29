import clsx from 'clsx'
import type { JobStatus } from '@/types'

const statusConfig: Record<JobStatus, { label: string; className: string }> = {
  queued: { label: 'Queued', className: 'bg-slate-700 text-slate-300' },
  pending: { label: 'Pending', className: 'bg-amber-900/60 text-amber-300' },
  running: { label: 'Running', className: 'bg-blue-900/60 text-blue-300' },
  completed: { label: 'Completed', className: 'bg-emerald-900/60 text-emerald-300' },
  failed: { label: 'Failed', className: 'bg-rose-900/60 text-rose-300' },
  cancelled: { label: 'Cancelled', className: 'bg-slate-700 text-slate-400' },
  failover: { label: 'Failover', className: 'bg-orange-900/60 text-orange-300' },
}

interface StatusBadgeProps {
  status: JobStatus | string
  size?: 'sm' | 'md'
}

export function StatusBadge({ status, size = 'md' }: StatusBadgeProps) {
  const cfg = statusConfig[status as JobStatus] ?? {
    label: status,
    className: 'bg-slate-700 text-slate-300',
  }

  return (
    <span
      className={clsx(
        'inline-flex items-center rounded-full font-medium',
        size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-xs',
        cfg.className,
      )}
    >
      {status === 'running' && (
        <span className="w-1.5 h-1.5 rounded-full bg-blue-400 mr-1.5 animate-pulse" />
      )}
      {cfg.label}
    </span>
  )
}
