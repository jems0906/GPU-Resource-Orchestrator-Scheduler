import { Link } from 'react-router-dom'
import { useJobs, useCancelJob } from '@/hooks/useJobs'
import { StatusBadge } from '@/components/common/StatusBadge'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { XCircle, ExternalLink, ChevronLeft, ChevronRight } from 'lucide-react'
import { format } from 'date-fns'
import type { JobStatus } from '@/types'
import { useState } from 'react'

interface JobTableProps {
  statusFilter?: string
  compact?: boolean
}

export function JobTable({ statusFilter, compact = false }: JobTableProps) {
  const [page, setPage] = useState(1)
  const { data, isLoading } = useJobs({ status: statusFilter, page, page_size: compact ? 5 : 20 })
  const cancelJob = useCancelJob()

  if (isLoading) return <LoadingSpinner />

  const jobs = data?.jobs ?? []

  return (
    <div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-surface-700">
              {!compact && <th className="text-left py-3 px-4 text-slate-400 font-medium">Name</th>}
              <th className="text-left py-3 px-4 text-slate-400 font-medium">Status</th>
              <th className="text-left py-3 px-4 text-slate-400 font-medium">GPU</th>
              {!compact && <th className="text-left py-3 px-4 text-slate-400 font-medium">Provider</th>}
              {!compact && <th className="text-left py-3 px-4 text-slate-400 font-medium">Cost</th>}
              <th className="text-left py-3 px-4 text-slate-400 font-medium">Priority</th>
              <th className="text-left py-3 px-4 text-slate-400 font-medium">Submitted</th>
              <th className="py-3 px-4" />
            </tr>
          </thead>
          <tbody>
            {jobs.length === 0 ? (
              <tr>
                <td
                  colSpan={compact ? 5 : 8}
                  className="py-10 text-center text-slate-500 text-sm"
                >
                  No jobs found
                </td>
              </tr>
            ) : (
              jobs.map((job) => (
                <tr
                  key={job.id}
                  className="border-b border-surface-700/50 hover:bg-surface-700/30 transition-colors"
                >
                  {!compact && (
                    <td className="py-3 px-4">
                      <Link
                        to={`/jobs/${job.id}`}
                        className="text-primary-400 hover:text-primary-300 font-medium"
                      >
                        {job.name}
                      </Link>
                      {job.model && (
                        <p className="text-xs text-slate-500 mt-0.5">{job.model}</p>
                      )}
                    </td>
                  )}
                  <td className="py-3 px-4">
                    <StatusBadge status={job.status as JobStatus} />
                  </td>
                  <td className="py-3 px-4 text-slate-300">
                    {job.gpu_count}× {job.gpu_type ?? 'Any'}
                  </td>
                  {!compact && (
                    <td className="py-3 px-4 text-slate-400 text-xs">
                      {job.instance ? (
                        <>
                          <span className="uppercase font-medium text-slate-300">
                            {job.instance.provider}
                          </span>{' '}
                          · {job.instance.region}
                        </>
                      ) : (
                        '—'
                      )}
                    </td>
                  )}
                  {!compact && (
                    <td className="py-3 px-4 text-slate-300 text-xs">
                      {job.actual_cost != null
                        ? `$${job.actual_cost.toFixed(4)}`
                        : job.estimated_cost != null
                        ? `~$${job.estimated_cost.toFixed(4)}`
                        : '—'}
                    </td>
                  )}
                  <td className="py-3 px-4">
                    <span
                      className={`text-xs font-bold ${
                        job.priority >= 8
                          ? 'text-rose-400'
                          : job.priority >= 5
                          ? 'text-amber-400'
                          : 'text-slate-400'
                      }`}
                    >
                      P{job.priority}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-slate-500 text-xs">
                    {format(new Date(job.created_at), 'MM/dd HH:mm')}
                  </td>
                  <td className="py-3 px-4">
                    <div className="flex items-center gap-1">
                      <Link
                        to={`/jobs/${job.id}`}
                        aria-label="View job details"
                        className="p-1 text-slate-500 hover:text-primary-400 transition-colors"
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                      </Link>
                      {!['completed', 'cancelled', 'failed'].includes(job.status) && (
                        <button
                          aria-label="Cancel job"
                          onClick={() => cancelJob.mutate(job.id)}
                          className="p-1 text-slate-500 hover:text-rose-400 transition-colors"
                          disabled={cancelJob.isPending}
                        >
                          <XCircle className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {!compact && data && data.total_pages > 1 && (
        <div className="flex items-center justify-between mt-4 text-sm text-slate-400">
          <span>
            {data.total} total · page {data.page} of {data.total_pages}
          </span>
          <div className="flex gap-2">
            <button
              aria-label="Previous page"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="p-1 rounded hover:bg-surface-700 disabled:opacity-40"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              aria-label="Next page"
              onClick={() => setPage((p) => Math.min(data.total_pages, p + 1))}
              disabled={page === data.total_pages}
              className="p-1 rounded hover:bg-surface-700 disabled:opacity-40"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
