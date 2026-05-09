import { Link } from 'react-router-dom'
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import StatCard from '../components/common/StatCard'
import { fmtMoney, Money } from '../components/common/Money'
import { useAccounts, useTrends } from '../hooks/queries'

export default function Summary() {
  const accounts = useAccounts()
  const trends = useTrends(12)

  const totalCurrent = accounts.data?.reduce((s, a) => s + a.current_month_usd, 0) ?? 0
  const totalPrev = accounts.data?.reduce((s, a) => s + a.prev_month_usd, 0) ?? 0
  const totalBudget = accounts.data?.reduce((s, a) => s + (a.monthly_budget_usd ?? 0), 0) ?? 0

  const trendData = (trends.data ?? []).map((p) => ({
    month: p.month.slice(0, 7),
    ...p.by_account,
  }))
  const slugSet = new Set<string>()
  trends.data?.forEach((p) => Object.keys(p.by_account).forEach((s) => slugSet.add(s)))
  const slugs = Array.from(slugSet)
  const palette = [
    '#2563eb', '#16a34a', '#dc2626', '#ca8a04', '#7c3aed',
    '#0891b2', '#db2777', '#65a30d', '#9333ea', '#0d9488',
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Summary</h1>
        <p className="text-sm text-[var(--color-text-muted)]">
          AWS spend across the Nonatech organisation, plus separately-invoiced accounts.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <StatCard
          label="This month so far"
          value={<Money value={totalCurrent} />}
          hint={
            totalBudget > 0
              ? `${((totalCurrent / totalBudget) * 100).toFixed(0)}% of $${totalBudget.toFixed(0)} combined budget`
              : '—'
          }
        />
        <StatCard label="Last month" value={<Money value={totalPrev} />} />
        <StatCard
          label="MoM change"
          value={
            <span className={totalCurrent > totalPrev ? 'text-[var(--color-bad)]' : 'text-[var(--color-good)]'}>
              {fmtMoney(totalCurrent - totalPrev, { sign: true })}
            </span>
          }
          hint={totalPrev > 0 ? `${(((totalCurrent - totalPrev) / totalPrev) * 100).toFixed(1)}%` : '—'}
        />
      </div>

      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg p-4">
        <h2 className="text-sm font-semibold mb-2">Last 12 months by account</h2>
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={trendData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
              <XAxis dataKey="month" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip
                formatter={(v: number) => `$${v.toFixed(2)}`}
                contentStyle={{ borderRadius: 6, border: '1px solid var(--color-border)' }}
              />
              {slugs.map((slug, i) => (
                <Area
                  key={slug}
                  type="monotone"
                  dataKey={slug}
                  stackId="a"
                  stroke={palette[i % palette.length]}
                  fill={palette[i % palette.length]}
                  fillOpacity={0.6}
                  isAnimationActive={false}
                />
              ))}
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-[var(--color-bg)] text-[var(--color-text-muted)] text-xs uppercase tracking-wide">
            <tr>
              <th className="text-left px-4 py-2">Account</th>
              <th className="text-left px-4 py-2 hidden md:table-cell">Billing</th>
              <th className="text-right px-4 py-2">This month</th>
              <th className="text-right px-4 py-2 hidden sm:table-cell">Last month</th>
              <th className="text-right px-4 py-2 hidden md:table-cell">Budget</th>
              <th className="text-right px-4 py-2">Status</th>
            </tr>
          </thead>
          <tbody>
            {accounts.data?.map((a) => {
              const budget = a.monthly_budget_usd ?? 0
              const overBudget = budget > 0 && a.current_month_usd > budget
              return (
                <tr key={a.account_id} className="border-t border-[var(--color-border)] hover:bg-[var(--color-bg)]">
                  <td className="px-4 py-2">
                    <Link className="text-[var(--color-accent)] hover:underline" to={`/account/${a.account_id}`}>
                      {a.name}
                    </Link>
                    <div className="text-xs text-[var(--color-text-muted)]">{a.account_id}</div>
                  </td>
                  <td className="px-4 py-2 hidden md:table-cell text-xs">
                    {a.billing === 'org' ? 'consolidated' : 'separate'}
                  </td>
                  <td className="px-4 py-2 text-right tabular">{fmtMoney(a.current_month_usd)}</td>
                  <td className="px-4 py-2 text-right tabular hidden sm:table-cell text-[var(--color-text-muted)]">
                    {fmtMoney(a.prev_month_usd)}
                  </td>
                  <td className="px-4 py-2 text-right tabular hidden md:table-cell text-[var(--color-text-muted)]">
                    {budget > 0 ? `$${budget.toFixed(0)}` : '—'}
                  </td>
                  <td className="px-4 py-2 text-right text-xs">
                    {budget > 0 ? (
                      <span className={overBudget ? 'text-[var(--color-bad)] font-semibold' : 'text-[var(--color-good)]'}>
                        {overBudget ? 'Over' : 'Under'}
                      </span>
                    ) : (
                      <span className="text-[var(--color-text-muted)]">—</span>
                    )}
                  </td>
                </tr>
              )
            })}
            {accounts.data && accounts.data.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-[var(--color-text-muted)]">
                  No accounts yet — run the backfill.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
