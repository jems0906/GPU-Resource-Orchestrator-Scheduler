import { Overview } from '@/components/Dashboard/Overview'
import { CostChart } from '@/components/Dashboard/CostChart'
import { JobTable } from '@/components/Jobs/JobTable'
import { useDashboardMetrics, useCostHistory } from '@/hooks/useMetrics'
import { Link } from 'react-router-dom'
import { PlusCircle } from 'lucide-react'

export default function DashboardPage() {
  const { data: metrics } = useDashboardMetrics()
  const { data: costHistory } = useCostHistory(14)

  return (
    <div className="space-y-6">
      {/* Metric overview row */}
      <Overview />

      {/* Cost chart */}
      {metrics && costHistory && (
        <div className="bg-surface-800 rounded-xl p-6">
          <h2 className="text-white font-semibold mb-4">Cost Trends</h2>
          <CostChart history={costHistory} summary={metrics.cost} />
        </div>
      )}

      {/* Recent jobs */}
      <div className="bg-surface-800 rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-white font-semibold">Recent Jobs</h2>
          <Link
            to="/jobs/new"
            className="flex items-center gap-1.5 px-3 py-1.5 bg-primary-600 hover:bg-primary-700 text-white text-xs font-medium rounded-lg transition-colors"
          >
            <PlusCircle className="w-3.5 h-3.5" />
            Submit Job
          </Link>
        </div>
        <JobTable compact />
      </div>
    </div>
  )
}
