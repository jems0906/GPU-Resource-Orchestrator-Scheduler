import type { ReactNode } from 'react'
import clsx from 'clsx'

interface MetricCardProps {
  title: string
  value: string | number
  subtitle?: string
  icon?: ReactNode
  trend?: 'up' | 'down' | 'neutral'
  trendLabel?: string
  className?: string
  accent?: 'blue' | 'green' | 'yellow' | 'red' | 'purple'
}

const accentBorder: Record<string, string> = {
  blue: 'border-primary-500',
  green: 'border-emerald-500',
  yellow: 'border-amber-500',
  red: 'border-rose-500',
  purple: 'border-purple-500',
}

const accentText: Record<string, string> = {
  blue: 'text-primary-400',
  green: 'text-emerald-400',
  yellow: 'text-amber-400',
  red: 'text-rose-400',
  purple: 'text-purple-400',
}

export function MetricCard({
  title,
  value,
  subtitle,
  icon,
  trend,
  trendLabel,
  className,
  accent = 'blue',
}: MetricCardProps) {
  return (
    <div
      className={clsx(
        'bg-surface-800 rounded-xl p-5 border-l-4',
        accentBorder[accent],
        className,
      )}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-slate-400 text-xs font-medium uppercase tracking-wide">{title}</p>
          <p className={clsx('text-2xl font-bold mt-1', accentText[accent])}>{value}</p>
          {subtitle && <p className="text-slate-500 text-xs mt-1">{subtitle}</p>}
        </div>
        {icon && (
          <div className="w-10 h-10 rounded-lg bg-surface-700 flex items-center justify-center shrink-0">
            <span className={accentText[accent]}>{icon}</span>
          </div>
        )}
      </div>
      {trendLabel && (
        <div className="mt-3 flex items-center gap-1 text-xs">
          <span
            className={clsx(
              trend === 'up' && 'text-emerald-400',
              trend === 'down' && 'text-rose-400',
              trend === 'neutral' && 'text-slate-400',
            )}
          >
            {trendLabel}
          </span>
        </div>
      )}
    </div>
  )
}
