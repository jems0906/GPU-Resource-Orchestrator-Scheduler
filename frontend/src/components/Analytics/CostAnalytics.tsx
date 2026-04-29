import { useCostHistory } from '@/hooks/useMetrics'
import { CostChart } from '@/components/Dashboard/CostChart'
import { PageLoader } from '@/components/common/LoadingSpinner'
import { useDashboardMetrics } from '@/hooks/useMetrics'
import { MetricCard } from '@/components/common/MetricCard'
import { DollarSign, TrendingDown, Zap } from 'lucide-react'

export function CostAnalytics() {
  const { data: history, isLoading: histLoading } = useCostHistory(90)
  const { data: metrics, isLoading: metricsLoading } = useDashboardMetrics()

  if (histLoading || metricsLoading || !history || !metrics) return <PageLoader />

  const savings = metrics.cost ?? {
    total_cost_today: 0,
    total_cost_this_month: 0,
    total_cost_all_time: 0,
    total_savings_from_spot: 0,
    savings_percent: 0,
    cost_by_provider: {},
    cost_by_gpu_type: {},
    average_cost_per_job: 0,
  }
  const spotSavings = savings.total_savings_from_spot ?? 0
  const totalSpend = savings.total_cost_today ?? 0
  const estimatedMonthly = totalSpend * 30

  return (
    <div className="space-y-6">
      {/* Summary cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Today's Spend"
          value={`$${totalSpend.toFixed(2)}`}
          icon={<DollarSign className="w-5 h-5" />}
          accent="blue"
        />
        <MetricCard
          title="Est. Monthly"
          value={`$${estimatedMonthly.toFixed(0)}`}
          icon={<DollarSign className="w-5 h-5" />}
          accent="purple"
        />
        <MetricCard
          title="Spot Savings"
          value={`$${spotSavings.toFixed(2)}`}
          icon={<Zap className="w-5 h-5" />}
          accent="green"
          trendLabel={`${savings.savings_percent?.toFixed(0) ?? 0}% savings`}
          trend="neutral"
        />
        <MetricCard
          title="Avg Cost/Job"
          value={
            savings.average_cost_per_job != null
              ? `$${savings.average_cost_per_job.toFixed(4)}`
              : '—'
          }
          icon={<TrendingDown className="w-5 h-5" />}
          accent="yellow"
        />
      </div>

      {/* Cost charts */}
      <div className="bg-surface-800 rounded-xl p-6">
        <h3 className="text-white font-semibold mb-4">Cost History</h3>
        <CostChart history={history} summary={savings} />
      </div>

      {/* Provider breakdown table */}
      <div className="bg-surface-800 rounded-xl p-6">
        <h3 className="text-white font-semibold mb-4">Spend by Provider</h3>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-surface-700">
              <th className="text-left py-2 px-3 text-slate-400 font-medium">Provider</th>
              <th className="text-right py-2 px-3 text-slate-400 font-medium">Today</th>
              <th className="text-right py-2 px-3 text-slate-400 font-medium">% of Total</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(savings.cost_by_provider ?? {}).map(([provider, cost]) => {
              const pct = totalSpend > 0 ? (cost / totalSpend) * 100 : 0
              return (
                <tr key={provider} className="border-b border-surface-700/50">
                  <td className="py-2 px-3 text-white uppercase font-medium">{provider}</td>
                  <td className="py-2 px-3 text-right text-slate-300">${cost.toFixed(4)}</td>
                  <td className="py-2 px-3 text-right text-slate-500">{pct.toFixed(1)}%</td>
                </tr>
              )
            })}
            {Object.keys(savings.cost_by_provider ?? {}).length === 0 && (
              <tr>
                <td colSpan={3} className="py-4 px-3 text-center text-slate-500">
                  No provider spend data yet
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
