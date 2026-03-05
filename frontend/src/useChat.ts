import { useCallback, useEffect, useRef, useState } from 'react'
import type { ChatMessage, ConnectionStatus, ToolCall } from './types'
import { getAccessToken } from './auth/authFetch'
import { getThreadMessages } from './api/chatApi'
import type { ThreadMessageItem } from './api/chatApi'

function buildWsUrl(token: string): string {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  return `${proto}://${location.host}/ws?token=${encodeURIComponent(token)}`
}

function convertServerMessages(messages: ThreadMessageItem[]): ChatMessage[] {
  const result: ChatMessage[] = []
  for (const msg of messages) {
    if (msg.role === 'user') {
      result.push({ id: crypto.randomUUID(), role: 'user', content: msg.content })
    } else if (msg.role === 'assistant') {
      const toolCalls: ToolCall[] = (msg.tool_calls || []).map((tc) => ({
        name: tc.name,
        callId: tc.id,
        output: '...',
      }))
      result.push({
        id: crypto.randomUUID(),
        role: 'assistant',
        content: msg.content,
        toolCalls: toolCalls.length > 0 ? toolCalls : undefined,
      })
    }
    // Skip tool messages — they're already embedded in assistant tool_calls
  }
  return result
}

function setupMessageHandler(
  ws: WebSocket,
  wsRef: React.RefObject<WebSocket | null>,
  assistantIdRef: React.RefObject<string | null>,
  setMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>,
  setStatus: React.Dispatch<React.SetStateAction<ConnectionStatus>>,
  setIsStreaming: React.Dispatch<React.SetStateAction<boolean>>,
) {
  ws.addEventListener('open', () => {
    if (wsRef.current === ws) setStatus('connected')
  })

  ws.addEventListener('close', () => {
    if (wsRef.current === ws) {
      setStatus('disconnected')
      wsRef.current = null
    }
  })

  ws.addEventListener('message', (event) => {
    const data = JSON.parse(event.data)

    if (data.type === 'token') {
      const id = assistantIdRef.current
      if (!id) return
      setMessages((prev) =>
        prev.map((m) =>
          m.id === id ? { ...m, content: m.content + data.content } : m,
        ),
      )
    } else if (data.type === 'tool_start') {
      const id = assistantIdRef.current
      if (!id) return
      const tool: ToolCall = { name: data.name, callId: data.call_id }
      setMessages((prev) =>
        prev.map((m) =>
          m.id === id
            ? { ...m, toolCalls: [...(m.toolCalls || []), tool] }
            : m,
        ),
      )
    } else if (data.type === 'tool_end') {
      const id = assistantIdRef.current
      if (!id) return
      setMessages((prev) =>
        prev.map((m) =>
          m.id === id
            ? {
                ...m,
                toolCalls: (m.toolCalls || []).map((tc) =>
                  tc.callId === data.call_id
                    ? { ...tc, output: data.output }
                    : tc,
                ),
              }
            : m,
        ),
      )
    } else if (data.type === 'end') {
      setIsStreaming(false)
      assistantIdRef.current = null
    } else if (data.type === 'error') {
      setIsStreaming(false)
      const id = assistantIdRef.current
      if (id) {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === id ? { ...m, content: `Erro: ${data.content}` } : m,
          ),
        )
      }
      assistantIdRef.current = null
    }
  })
}

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [status, setStatus] = useState<ConnectionStatus>('disconnected')
  const [isStreaming, setIsStreaming] = useState(false)
  const [threadId, setThreadId] = useState<string>(() => crypto.randomUUID())

  const wsRef = useRef<WebSocket | null>(null)
  const threadIdRef = useRef(threadId)
  const assistantIdRef = useRef<string | null>(null)

  // Keep ref in sync with state
  useEffect(() => {
    threadIdRef.current = threadId
  }, [threadId])

  useEffect(() => {
    function connect() {
      const token = getAccessToken()
      if (!token) {
        setStatus('disconnected')
        return
      }

      setStatus('connecting')
      const ws = new WebSocket(buildWsUrl(token))
      setupMessageHandler(ws, wsRef, assistantIdRef, setMessages, setStatus, setIsStreaming)
      wsRef.current = ws
    }

    connect()

    return () => {
      const ws = wsRef.current
      wsRef.current = null
      ws?.close()
    }
  }, [])

  const reconnect = useCallback(() => {
    const ws = wsRef.current
    wsRef.current = null
    ws?.close()

    const token = getAccessToken()
    if (!token) {
      setStatus('disconnected')
      return
    }

    setStatus('connecting')
    const newWs = new WebSocket(buildWsUrl(token))
    setupMessageHandler(newWs, wsRef, assistantIdRef, setMessages, setStatus, setIsStreaming)
    wsRef.current = newWs
  }, [])

  const sendMessage = useCallback(
    (text: string) => {
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return
      if (isStreaming) return

      const userMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'user',
        content: text,
      }

      const assistantMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: '',
      }

      assistantIdRef.current = assistantMsg.id
      setMessages((prev) => [...prev, userMsg, assistantMsg])
      setIsStreaming(true)

      wsRef.current.send(
        JSON.stringify({
          message: text,
          thread_id: threadIdRef.current,
        }),
      )
    },
    [isStreaming],
  )

  const loadThread = useCallback(async (id: string) => {
    if (isStreaming) return
    setThreadId(id)
    try {
      const serverMessages = await getThreadMessages(id)
      const converted = convertServerMessages(serverMessages)
      setMessages(converted)
    } catch {
      setMessages([])
    }
  }, [isStreaming])

  const newThread = useCallback(() => {
    if (isStreaming) return
    const id = crypto.randomUUID()
    setThreadId(id)
    setMessages([])
  }, [isStreaming])

  return { messages, status, isStreaming, threadId, sendMessage, reconnect, loadThread, newThread }
}
