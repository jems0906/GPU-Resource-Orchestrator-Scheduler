import { useState } from 'react'
import { JobTable } from '@/components/Jobs/JobTable'
import { Link } from 'react-router-dom'
import { PlusCircle } from 'lucide-react'

const STATUS_FILTERS = [
  { label: 'All', value: '' },
  { label: 'Queued', value: 'queued' },
  { label: 'Running', value: 'running' },
  { label: 'Completed', value: 'completed' },
  { label: 'Failed', value: 'failed' },
  { label: 'Cancelled', value: 'cancelled' },
]

export default function JobsPage() {
  const [statusFilter, setStatusFilter] = useState('')

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex items-center justify-between">
        <div className="flex gap-1.5">
          {STATUS_FILTERS.map((f) => (
            <button
              key={f.value}
              onClick={() => setStatusFilter(f.value)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                statusFilter === f.value
                  ? 'bg-primary-600 text-white'
                  : 'bg-surface-700 text-slate-400 hover:text-white'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
        <Link
          to="/jobs/new"
          className="flex items-center gap-1.5 px-3 py-1.5 bg-primary-600 hover:bg-primary-700 text-white text-xs font-medium rounded-lg transition-colors"
        >
          <PlusCircle className="w-3.5 h-3.5" />
          Submit Job
        </Link>
      </div>

      {/* Table */}
      <div className="bg-surface-800 rounded-xl p-6">
        <JobTable statusFilter={statusFilter || undefined} />
      </div>
    </div>
  )
}
