type Props = {
  value: string  // YYYY-MM
  onChange: (next: string) => void
  monthsBack?: number
}

function* months(back: number): Iterable<string> {
  const today = new Date()
  for (let i = 0; i < back; i++) {
    const d = new Date(today.getFullYear(), today.getMonth() - i, 1)
    yield `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
  }
}

export default function MonthPicker({ value, onChange, monthsBack = 24 }: Props) {
  const options = Array.from(months(monthsBack))
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="border border-[var(--color-border)] rounded-md px-2 py-1 text-sm bg-[var(--color-surface)]"
    >
      {options.map((m) => (
        <option key={m} value={m}>{m}</option>
      ))}
    </select>
  )
}
