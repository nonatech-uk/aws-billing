import { useMe, useSyncRuns, useSyncStatus, useTriggerSync } from '../hooks/queries'

function fmtTs(s: string | null | undefined): string {
  if (!s) return '—'
  return new Date(s).toLocaleString()
}

export default function Settings() {
  const me = useMe()
  const status = useSyncStatus()
  const runs = useSyncRuns()
  const trigger = useTriggerSync()

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Settings</h1>
      </div>

      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg p-4 space-y-3">
        <h2 className="text-sm font-semibold">Sync</h2>
        <div className="text-sm">
          <div>Last status: <strong>{status.data?.status ?? '—'}</strong></div>
          <div>Started: {fmtTs(status.data?.started_at)}</div>
          <div>Finished: {fmtTs(status.data?.finished_at)}</div>
          {status.data?.error && (
            <div className="text-[var(--color-bad)] text-xs mt-1">Error: {status.data.error}</div>
          )}
        </div>
        {me.data?.is_admin && (
          <button
            onClick={() => trigger.mutate()}
            disabled={trigger.isPending}
            className="px-3 py-1.5 rounded-md bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] text-white text-sm font-medium disabled:opacity-50"
          >
            {trigger.isPending ? 'Triggering…' : 'Run sync now'}
          </button>
        )}
      </div>

      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg overflow-hidden">
        <h2 className="text-sm font-semibold px-4 py-3 border-b border-[var(--color-border)]">
          Recent runs
        </h2>
        <table className="w-full text-sm">
          <thead className="bg-[var(--color-bg)] text-[var(--color-text-muted)] text-xs uppercase tracking-wide">
            <tr>
              <th className="text-left px-4 py-2">Started</th>
              <th className="text-left px-4 py-2">Finished</th>
              <th className="text-left px-4 py-2">Status</th>
              <th className="text-left px-4 py-2">Error</th>
            </tr>
          </thead>
          <tbody>
            {runs.data?.map((r) => (
              <tr key={r.id} className="border-t border-[var(--color-border)]">
                <td className="px-4 py-2">{fmtTs(r.started_at)}</td>
                <td className="px-4 py-2">{fmtTs(r.finished_at)}</td>
                <td className="px-4 py-2">
                  <span
                    className={
                      r.status === 'ok'
                        ? 'text-[var(--color-good)]'
                        : r.status === 'error'
                          ? 'text-[var(--color-bad)]'
                          : 'text-[var(--color-text-muted)]'
                    }
                  >
                    {r.status}
                  </span>
                </td>
                <td className="px-4 py-2 text-xs text-[var(--color-text-muted)] truncate max-w-xs">
                  {r.error ?? '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg p-4 text-sm">
        <h2 className="text-sm font-semibold mb-2">Account</h2>
        {me.data ? (
          <div className="space-y-1 text-[var(--color-text-muted)]">
            <div><span className="text-[var(--color-text)]">{me.data.email}</span></div>
            <div>Role: {me.data.is_admin ? 'admin' : 'viewer'}</div>
            <a href="/api/v1/auth/logout" className="text-[var(--color-accent)] hover:underline">Sign out</a>
          </div>
        ) : (
          <div className="text-[var(--color-text-muted)]">Not signed in.</div>
        )}
      </div>
    </div>
  )
}
