import { useParams, Navigate } from 'react-router-dom'
import { JobDetail } from '@/components/Jobs/JobDetail'

export default function JobDetailPage() {
  const { id } = useParams<{ id: string }>()
  if (!id) return <Navigate to="/jobs" replace />
  return <JobDetail jobId={id} />
}
