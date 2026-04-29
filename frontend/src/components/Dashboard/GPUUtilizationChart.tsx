import {
  LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend,
} from 'recharts'
import type { JobMetric } from '@/types'
import { format } from 'date-fns'

interface Props {
  metrics: JobMetric[]
}

export function GPUUtilizationChart({ metrics }: Props) {
  const data = metrics.map((m) => ({
    time: format(new Date(m.timestamp), 'HH:mm:ss'),
    gpu: m.gpu_utilization ? +m.gpu_utilization.toFixed(1) : 0,
    mem: m.gpu_memory_used_gb
      ? +(
          (m.gpu_memory_used_gb / (m.gpu_memory_total_gb || m.gpu_memory_used_gb || 1)) *
          100
        ).toFixed(1)
      : 0,
    cost: m.cost_so_far ? +m.cost_so_far.toFixed(4) : 0,
  }))

  return (
    <div className="space-y-4">
      <div>
        <p className="text-slate-400 text-xs mb-2 uppercase tracking-wide">GPU &amp; Memory Utilization (%)</p>
        <ResponsiveContainer width="100%" height={200}>
          <AreaChart data={data} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="gpuGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="memGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#a855f7" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#a855f7" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="time" tick={{ fill: '#94a3b8', fontSize: 10 }} interval="preserveStartEnd" />
            <YAxis domain={[0, 100]} tick={{ fill: '#94a3b8', fontSize: 10 }} />
            <Tooltip
              contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
              labelStyle={{ color: '#cbd5e1' }}
            />
            <Legend wrapperStyle={{ fontSize: 11, color: '#94a3b8' }} />
            <Area type="monotone" dataKey="gpu" name="GPU %" stroke="#3b82f6" fill="url(#gpuGrad)" strokeWidth={2} dot={false} />
            <Area type="monotone" dataKey="mem" name="Mem %" stroke="#a855f7" fill="url(#memGrad)" strokeWidth={2} dot={false} />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div>
        <p className="text-slate-400 text-xs mb-2 uppercase tracking-wide">Cumulative Cost (USD)</p>
        <ResponsiveContainer width="100%" height={120}>
          <LineChart data={data} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="time" tick={{ fill: '#94a3b8', fontSize: 10 }} interval="preserveStartEnd" />
            <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} />
            <Tooltip
              contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
              labelStyle={{ color: '#cbd5e1' }}
              formatter={(v: number) => [`$${v.toFixed(4)}`, 'Cost']}
            />
            <Line type="monotone" dataKey="cost" name="Cost $" stroke="#34d399" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
