export type CurrentUser = {
  email: string
  name: string
  is_admin: boolean
}

export type AccountRow = {
  account_id: string
  slug: string
  name: string
  billing: 'org' | 'separate'
  monthly_budget_usd: number | null
  current_month_usd: number
  prev_month_usd: number
}

export type MonthlyPoint = {
  month: string
  gross_usd: number
  net_usd: number
}

export type AccountDetail = {
  account_id: string
  slug: string
  name: string
  billing: 'org' | 'separate'
  monthly_budget_usd: number | null
  monthly: MonthlyPoint[]
}

export type ServiceRow = {
  service: string
  cost_usd: number
  pct: number
  usage_qty?: number | null
  usage_unit?: string | null
}

export type SummaryAccount = {
  account_id: string
  slug: string
  name: string
  billing: 'org' | 'separate'
  monthly_budget_usd: number | null
  cost_usd: number
}

export type SummaryResponse = {
  month: string
  total_gross_usd: number
  total_net_usd: number
  accounts: SummaryAccount[]
}

export type TrendPoint = {
  month: string
  total_gross_usd: number
  by_account: Record<string, number>
}

export type SyncRunRow = {
  id: number
  started_at: string
  finished_at: string | null
  status: 'running' | 'ok' | 'error'
  error: string | null
}
