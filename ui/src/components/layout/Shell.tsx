import type { ReactNode } from 'react'
import { Link, NavLink } from 'react-router-dom'
import { useMe } from '../../hooks/queries'

const navLink = ({ isActive }: { isActive: boolean }) =>
  `px-3 py-1.5 rounded-md text-sm font-medium transition ${
    isActive
      ? 'bg-[var(--color-accent)] text-white'
      : 'text-[var(--color-text-muted)] hover:text-[var(--color-text)] hover:bg-[var(--color-bg)]'
  }`

export default function Shell({ children }: { children: ReactNode }) {
  const me = useMe()
  return (
    <div className="min-h-full flex flex-col">
      <header className="bg-[var(--color-surface)] border-b border-[var(--color-border)] sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 py-3 flex items-center gap-4">
          <Link to="/" className="font-semibold text-base">
            AWS Billing
          </Link>
          <nav className="flex items-center gap-1 ml-2">
            <NavLink to="/" end className={navLink}>Summary</NavLink>
            <NavLink to="/settings" className={navLink}>Settings</NavLink>
          </nav>
          <div className="ml-auto text-xs text-[var(--color-text-muted)]">
            {me.data ? (
              <span>
                {me.data.name || me.data.email}
                {me.data.is_admin && <span className="ml-2 px-1.5 py-0.5 rounded bg-[var(--color-bg)] border border-[var(--color-border)] text-[10px]">admin</span>}
              </span>
            ) : null}
          </div>
        </div>
      </header>
      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-6">{children}</main>
    </div>
  )
}
