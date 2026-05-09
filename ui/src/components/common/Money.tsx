export function fmtMoney(usd: number, opts: { sign?: boolean } = {}): string {
  const sign = opts.sign && usd > 0 ? '+' : ''
  if (usd < 0) return `-$${Math.abs(usd).toFixed(2)}`
  return `${sign}$${usd.toFixed(2)}`
}

export function Money({ value, className = '' }: { value: number; className?: string }) {
  return <span className={`tabular ${className}`}>{fmtMoney(value)}</span>
}
