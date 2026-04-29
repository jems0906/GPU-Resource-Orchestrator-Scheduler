import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from 'recharts'
import type { CostDataPoint, CostSummary } from '@/types'

const PROVIDER_COLORS: Record<string, string> = {
  aws: '#f59e0b',
  gcp: '#3b82f6',
  azure: '#8b5cf6',
}

interface CostChartProps {
  history: CostDataPoint[]
  summary: CostSummary
}

export function CostChart({ history, summary }: CostChartProps) {
  // Aggregate daily cost by date
  const dailyMap: Record<string, { date: string; [key: string]: number | string }> = {}
  for (const point of history) {
    if (!dailyMap[point.date]) {
      dailyMap[point.date] = { date: point.date }
    }
    dailyMap[point.date][point.provider] = (Number(dailyMap[point.date][point.provider]) || 0) + point.cost
  }
  const dailyData = Object.values(dailyMap).slice(-14) // last 14 days

  // Provider pie chart data
  const pieData = Object.entries(summary?.cost_by_provider ?? {}).map(([provider, cost]) => ({
    name: provider.toUpperCase(),
    value: cost,
  }))

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div>
        <p className="text-slate-400 text-xs mb-3 uppercase tracking-wide">Daily Spend by Provider (Last 14 days)</p>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={dailyData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="date" tick={{ fill: '#94a3b8', fontSize: 10 }} interval={1} />
            <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} tickFormatter={(v) => `$${v}`} />
            <Tooltip
              contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
              formatter={(v: number) => [`$${v.toFixed(2)}`, '']}
            />
            <Bar dataKey="aws" name="AWS" stackId="a" fill="#f59e0b" radius={[0, 0, 0, 0]} />
            <Bar dataKey="gcp" name="GCP" stackId="a" fill="#3b82f6" />
            <Bar dataKey="azure" name="Azure" stackId="a" fill="#8b5cf6" radius={[2, 2, 0, 0]} />
            <Legend wrapperStyle={{ fontSize: 11, color: '#94a3b8' }} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div>
        <p className="text-slate-400 text-xs mb-3 uppercase tracking-wide">Cost Distribution by Provider</p>
        {pieData.length > 0 ? (
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={90}
                paddingAngle={3}
                dataKey="value"
              >
                {pieData.map((entry, index) => (
                  <Cell
                    key={entry.name}
                    fill={
                      PROVIDER_COLORS[entry.name.toLowerCase()] ||
                      ['#34d399', '#f97316', '#06b6d4'][index % 3]
                    }
                  />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
                formatter={(v: number) => [`$${v.toFixed(2)}`, '']}
              />
              <Legend wrapperStyle={{ fontSize: 11, color: '#94a3b8' }} />
            </PieChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-[220px] flex items-center justify-center text-slate-500 text-sm">
            No billing data yet
          </div>
        )}
      </div>
    </div>
  )
}
