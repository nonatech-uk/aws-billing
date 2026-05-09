import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import MonthPicker from '../components/common/MonthPicker'
import { fmtMoney } from '../components/common/Money'
import StatCard from '../components/common/StatCard'
import { useAccount, useServices } from '../hooks/queries'

function ymToday() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

export default function AccountDetail() {
  const { accountId } = useParams<{ accountId: string }>()
  const [month, setMonth] = useState<string>(ymToday())
  const account = useAccount(accountId)
  const services = useServices(accountId, month)

  const a = account.data
  const monthly = a?.monthly ?? []
  const currentMonth = monthly[monthly.length - 1]
  const prevMonth = monthly[monthly.length - 2]
  const budget = a?.monthly_budget_usd ?? 0

  return (
    <div className="space-y-6">
      <div>
        <Link to="/" className="text-xs text-[var(--color-accent)] hover:underline">← Back to summary</Link>
        <div className="flex items-center gap-3 mt-1">
          <h1 className="text-xl font-semibold">{a?.name ?? '...'}</h1>
          {a && (
            <span className="text-xs text-[var(--color-text-muted)]">
              {a.account_id} · {a.billing === 'org' ? 'consolidated' : 'separate invoice'}
            </span>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <StatCard
          label="Current month"
          value={fmtMoney(currentMonth?.gross_usd ?? 0)}
          hint={currentMonth ? currentMonth.month.slice(0, 7) : ''}
        />
        <StatCard
          label="Previous month"
          value={fmtMoney(prevMonth?.gross_usd ?? 0)}
          hint={prevMonth ? prevMonth.month.slice(0, 7) : ''}
        />
        <StatCard
          label="Budget"
          value={budget > 0 ? `$${budget.toFixed(0)}` : '—'}
          hint={
            budget > 0 && currentMonth
              ? `${((currentMonth.gross_usd / budget) * 100).toFixed(0)}% used`
              : ''
          }
        />
      </div>

      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg p-4">
        <h2 className="text-sm font-semibold mb-2">12-month trend</h2>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={monthly.map((p) => ({ month: p.month.slice(0, 7), cost: p.gross_usd }))}
              margin={{ top: 10, right: 10, left: -10, bottom: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
              <XAxis dataKey="month" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip
                formatter={(v: number) => `$${v.toFixed(2)}`}
                contentStyle={{ borderRadius: 6, border: '1px solid var(--color-border)' }}
              />
              <Line type="monotone" dataKey="cost" stroke="var(--color-accent)" strokeWidth={2} dot />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--color-border)]">
          <h2 className="text-sm font-semibold">Service breakdown</h2>
          <MonthPicker value={month} onChange={setMonth} />
        </div>
        <table className="w-full text-sm">
          <thead className="bg-[var(--color-bg)] text-[var(--color-text-muted)] text-xs uppercase tracking-wide">
            <tr>
              <th className="text-left px-4 py-2">Service</th>
              <th className="text-right px-4 py-2">Cost</th>
              <th className="text-right px-4 py-2">% of total</th>
            </tr>
          </thead>
          <tbody>
            {services.data?.map((s) => (
              <tr key={s.service} className="border-t border-[var(--color-border)]">
                <td className="px-4 py-2">{s.service}</td>
                <td className="px-4 py-2 text-right tabular">{fmtMoney(s.cost_usd)}</td>
                <td className="px-4 py-2 text-right tabular text-[var(--color-text-muted)]">
                  {s.pct.toFixed(1)}%
                </td>
              </tr>
            ))}
            {services.data && services.data.length === 0 && (
              <tr>
                <td colSpan={3} className="px-4 py-8 text-center text-[var(--color-text-muted)]">
                  No data for {month}.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
