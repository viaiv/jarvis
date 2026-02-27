const TOKEN_KEY = 'jarvis_tokens'

export interface StoredTokens {
  access_token: string
  refresh_token: string
}

export function getTokens(): StoredTokens | null {
  const raw = localStorage.getItem(TOKEN_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw) as StoredTokens
  } catch {
    return null
  }
}

export function setTokens(tokens: StoredTokens): void {
  localStorage.setItem(TOKEN_KEY, JSON.stringify(tokens))
}

export function clearTokens(): void {
  localStorage.removeItem(TOKEN_KEY)
}

export function getAccessToken(): string | null {
  return getTokens()?.access_token ?? null
}

async function tryRefresh(): Promise<string | null> {
  const tokens = getTokens()
  if (!tokens?.refresh_token) return null

  try {
    const resp = await fetch('/auth/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: tokens.refresh_token }),
    })

    if (!resp.ok) {
      clearTokens()
      return null
    }

    const data = await resp.json()
    setTokens(data)
    return data.access_token
  } catch {
    clearTokens()
    return null
  }
}

export async function authFetch(
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<Response> {
  const token = getAccessToken()
  const headers = new Headers(init?.headers)
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  let resp = await fetch(input, { ...init, headers })

  if (resp.status === 401 && token) {
    const newToken = await tryRefresh()
    if (newToken) {
      headers.set('Authorization', `Bearer ${newToken}`)
      resp = await fetch(input, { ...init, headers })
    }
  }

  return resp
}
