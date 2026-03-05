import { authFetch } from '../auth/authFetch'

export interface ThreadItem {
  thread_id: string
  preview: string
  message_count: number
}

export interface ThreadListResponse {
  threads: ThreadItem[]
  total: number
}

export interface ThreadMessageItem {
  role: string
  content: string
  tool_calls?: { name: string; id: string }[]
  tool_call_id?: string
  name?: string
}

async function json<T>(resp: Response): Promise<T> {
  if (!resp.ok) {
    const body = await resp.json().catch(() => null)
    throw new Error(body?.detail ?? `Erro ${resp.status}`)
  }
  return resp.json()
}

export async function listThreads(): Promise<ThreadListResponse> {
  const resp = await authFetch('/chat/threads')
  return json<ThreadListResponse>(resp)
}

export async function getThreadMessages(threadId: string): Promise<ThreadMessageItem[]> {
  const resp = await authFetch(`/chat/threads/${encodeURIComponent(threadId)}`)
  const data = await json<{ thread_id: string; messages: ThreadMessageItem[] }>(resp)
  return data.messages
}
