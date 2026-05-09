import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import type {
  AccountDetail,
  AccountRow,
  CurrentUser,
  ServiceRow,
  SummaryResponse,
  SyncRunRow,
  TrendPoint,
} from '../api/types'

export function useMe() {
  return useQuery<CurrentUser>({
    queryKey: ['me'],
    queryFn: () => api('/auth/me'),
    retry: false,
  })
}

export function useAccounts() {
  return useQuery<AccountRow[]>({
    queryKey: ['accounts'],
    queryFn: () => api('/accounts'),
  })
}

export function useAccount(accountId: string | undefined) {
  return useQuery<AccountDetail>({
    queryKey: ['account', accountId],
    queryFn: () => api(`/accounts/${accountId}`),
    enabled: Boolean(accountId),
  })
}

export function useServices(accountId: string | undefined, month: string) {
  return useQuery<ServiceRow[]>({
    queryKey: ['services', accountId, month],
    queryFn: () => api(`/accounts/${accountId}/services?month=${month}`),
    enabled: Boolean(accountId),
  })
}

export function useSummary(month?: string) {
  const q = month ? `?month=${month}` : ''
  return useQuery<SummaryResponse>({
    queryKey: ['summary', month ?? 'current'],
    queryFn: () => api(`/summary${q}`),
  })
}

export function useTrends(months = 12) {
  return useQuery<TrendPoint[]>({
    queryKey: ['trends', months],
    queryFn: () => api(`/trends?months=${months}`),
  })
}

export function useSyncStatus() {
  return useQuery<SyncRunRow | null>({
    queryKey: ['sync-status'],
    queryFn: () => api('/sync/status'),
  })
}

export function useSyncRuns() {
  return useQuery<SyncRunRow[]>({
    queryKey: ['sync-runs'],
    queryFn: () => api('/sync/runs'),
  })
}

export function useTriggerSync() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api<SyncRunRow>('/sync/run', { method: 'POST' }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['sync-status'] })
      qc.invalidateQueries({ queryKey: ['sync-runs'] })
    },
  })
}
