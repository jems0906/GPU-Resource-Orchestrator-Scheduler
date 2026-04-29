import { useQuery } from '@tanstack/react-query'
import { metricsApi } from '@/services/api'

export function useDashboardMetrics() {
  return useQuery({
    queryKey: ['dashboard'],
    queryFn: () => metricsApi.dashboard(),
    refetchInterval: 5000,
  })
}

export function useCostHistory(days = 30) {
  return useQuery({
    queryKey: ['cost-history', days],
    queryFn: () => metricsApi.costHistory(days),
    refetchInterval: 60_000,
  })
}

export function useQueueDepth() {
  return useQuery({
    queryKey: ['queue-depth'],
    queryFn: () => metricsApi.queueDepth(),
    refetchInterval: 2000,
  })
}
