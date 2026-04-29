import { useQuery } from '@tanstack/react-query'
import { providersApi } from '@/services/api'

export function useInventory(params?: {
  provider?: string
  region?: string
  gpu_type?: string
  available_only?: boolean
}) {
  return useQuery({
    queryKey: ['inventory', params],
    queryFn: () => providersApi.inventory(params),
    refetchInterval: 15_000,
  })
}

export function useProviderHealth() {
  return useQuery({
    queryKey: ['provider-health'],
    queryFn: () => providersApi.health(),
    refetchInterval: 30_000,
  })
}

export function usePricing(params?: { provider?: string; gpu_type?: string }) {
  return useQuery({
    queryKey: ['pricing', params],
    queryFn: () => providersApi.pricing(params),
    staleTime: 5 * 60 * 1000,
  })
}
