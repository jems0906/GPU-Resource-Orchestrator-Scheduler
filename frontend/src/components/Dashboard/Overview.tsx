import { MetricCard } from '@/components/common/MetricCard'
import { useDashboardMetrics, useQueueDepth } from '@/hooks/useMetrics'
import { Cpu, DollarSign, AlertTriangle, Activity } from 'lucide-react'

export function Overview() {
  const { data: metrics } = useDashboardMetrics()
  useQueueDepth()

  const running = metrics?.queue?.total_running ?? 0
  const queued = metrics?.queue?.total_queued ?? 0
  const utilization = metrics?.total_gpus_available
    ? ((metrics.total_gpus_in_use / metrics.total_gpus_available) * 100)
    : 0
  const todayCost = metrics?.cost?.total_cost_today ?? 0
  const violations = metrics?.sla?.active_violations?.length ?? 0

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <MetricCard
        title="Running Jobs"
        value={running}
        subtitle={`${queued} queued`}
        icon={<Cpu className="w-5 h-5" />}
        accent="blue"
      />
      <MetricCard
        title="GPU Utilization"
        value={`${utilization.toFixed(1)}%`}
        subtitle="across all providers"
        icon={<Activity className="w-5 h-5" />}
        accent="green"
      />
      <MetricCard
        title="Today's Cost"
        value={`$${todayCost.toFixed(2)}`}
        subtitle={`Spot savings: $${(metrics?.cost?.total_savings_from_spot ?? 0).toFixed(2)}`}
        icon={<DollarSign className="w-5 h-5" />}
        accent="yellow"
      />
      <MetricCard
        title="SLA Violations"
        value={violations}
        subtitle="active alerts"
        icon={<AlertTriangle className="w-5 h-5" />}
        accent={violations > 0 ? 'red' : 'blue'}
      />
    </div>
  )
}
