import { authFetch } from '../auth/authFetch'
import type {
  AdminUser,
  ConfigData,
  ThreadListResponse,
  ThreadMessage,
  UserCreate,
  UserUpdate,
} from '../types'

const BASE = '/admin'

async function json<T>(resp: Response): Promise<T> {
  if (!resp.ok) {
    const body = await resp.json().catch(() => null)
    throw new Error(body?.detail ?? `Erro ${resp.status}`)
  }
  return resp.json()
}

// --- Users ---

export async function listUsers(): Promise<AdminUser[]> {
  const resp = await authFetch(`${BASE}/users`)
  return json<AdminUser[]>(resp)
}

export async function createUser(data: UserCreate): Promise<AdminUser> {
  const resp = await authFetch(`${BASE}/users`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  return json<AdminUser>(resp)
}

export async function getUser(id: number): Promise<AdminUser> {
  const resp = await authFetch(`${BASE}/users/${id}`)
  return json<AdminUser>(resp)
}

export async function updateUser(id: number, data: UserUpdate): Promise<AdminUser> {
  const resp = await authFetch(`${BASE}/users/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  return json<AdminUser>(resp)
}

export async function deleteUser(id: number): Promise<void> {
  const resp = await authFetch(`${BASE}/users/${id}`, { method: 'DELETE' })
  if (!resp.ok) {
    const body = await resp.json().catch(() => null)
    throw new Error(body?.detail ?? `Erro ${resp.status}`)
  }
}

export async function updatePassword(id: number, password: string): Promise<void> {
  const resp = await authFetch(`${BASE}/users/${id}/password`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ password }),
  })
  if (!resp.ok) {
    const body = await resp.json().catch(() => null)
    throw new Error(body?.detail ?? `Erro ${resp.status}`)
  }
}

// --- Config ---

export async function getGlobalConfig(): Promise<ConfigData> {
  const resp = await authFetch(`${BASE}/config`)
  return json<ConfigData>(resp)
}

export async function setGlobalConfig(data: ConfigData): Promise<ConfigData> {
  const resp = await authFetch(`${BASE}/config`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  return json<ConfigData>(resp)
}

export async function getUserConfig(userId: number): Promise<ConfigData> {
  const resp = await authFetch(`${BASE}/users/${userId}/config`)
  return json<ConfigData>(resp)
}

export async function setUserConfig(userId: number, data: ConfigData): Promise<ConfigData> {
  const resp = await authFetch(`${BASE}/users/${userId}/config`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  return json<ConfigData>(resp)
}

// --- Logs ---

export async function listThreads(
  params?: { user_id?: number; limit?: number; offset?: number },
): Promise<ThreadListResponse> {
  const qs = new URLSearchParams()
  if (params?.user_id != null) qs.set('user_id', String(params.user_id))
  if (params?.limit != null) qs.set('limit', String(params.limit))
  if (params?.offset != null) qs.set('offset', String(params.offset))
  const query = qs.toString()
  const resp = await authFetch(`${BASE}/logs${query ? `?${query}` : ''}`)
  return json<ThreadListResponse>(resp)
}

export async function getThreadMessages(threadId: string): Promise<ThreadMessage[]> {
  const resp = await authFetch(`${BASE}/logs/${encodeURIComponent(threadId)}`)
  const data = await json<{ thread_id: string; messages: ThreadMessage[] }>(resp)
  return data.messages
}
