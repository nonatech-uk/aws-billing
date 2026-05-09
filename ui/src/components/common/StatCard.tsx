import type { ReactNode } from 'react'

export default function StatCard({
  label,
  value,
  hint,
}: {
  label: string
  value: ReactNode
  hint?: ReactNode
}) {
  return (
    <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-4 py-3">
      <div className="text-xs uppercase tracking-wide text-[var(--color-text-muted)]">{label}</div>
      <div className="text-2xl font-semibold tabular mt-1">{value}</div>
      {hint && <div className="text-xs text-[var(--color-text-muted)] mt-0.5">{hint}</div>}
    </div>
  )
}
