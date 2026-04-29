import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { jobsApi } from '@/services/api'
import type { JobCreate } from '@/types'

export function useJobs(params?: {
  status?: string
  job_type?: string
  page?: number
  page_size?: number
}) {
  return useQuery({
    queryKey: ['jobs', params],
    queryFn: () => jobsApi.list(params),
    refetchInterval: 5000,
  })
}

export function useJob(id: string) {
  return useQuery({
    queryKey: ['job', id],
    queryFn: () => jobsApi.get(id),
    refetchInterval: 3000,
    enabled: Boolean(id),
  })
}

export function useJobMetrics(id: string, enabled = true) {
  return useQuery({
    queryKey: ['job-metrics', id],
    queryFn: () => jobsApi.metrics(id, 60),
    refetchInterval: 3000,
    enabled: Boolean(id) && enabled,
  })
}

export function useSubmitJob() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: JobCreate) => jobsApi.submit(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })
}

export function useCancelJob() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => jobsApi.cancel(id),
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      queryClient.invalidateQueries({ queryKey: ['job', id] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })
}

export function useScaleJob() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, gpu_count, reason }: { id: string; gpu_count: number; reason?: string }) =>
      jobsApi.scale(id, gpu_count, reason),
    onSuccess: (_data, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      queryClient.invalidateQueries({ queryKey: ['job', id] })
    },
  })
}
