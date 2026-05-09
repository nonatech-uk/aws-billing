const BASE = '/api/v1'

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    credentials: 'include',
    ...init,
  })
  if (res.status === 401) {
    // Redirect to login. Authlib middleware will redirect back to "/"
    window.location.href = `${BASE}/auth/login`
    throw new Error('Redirecting to login')
  }
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`API ${res.status}: ${text || res.statusText}`)
  }
  return res.json() as Promise<T>
}
