import { useCallback, useEffect, useRef, useState } from 'react'
import type { ChatMessage, ConnectionStatus, ToolCall } from './types'
import { getAccessToken } from './auth/authFetch'

function buildWsUrl(token: string): string {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  return `${proto}://${location.host}/ws?token=${encodeURIComponent(token)}`
}

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [status, setStatus] = useState<ConnectionStatus>('disconnected')
  const [isStreaming, setIsStreaming] = useState(false)

  const wsRef = useRef<WebSocket | null>(null)
  const threadIdRef = useRef(crypto.randomUUID())
  const assistantIdRef = useRef<string | null>(null)

  useEffect(() => {
    function connect() {
      const token = getAccessToken()
      if (!token) {
        setStatus('disconnected')
        return
      }

      setStatus('connecting')
      const ws = new WebSocket(buildWsUrl(token))

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

    newWs.addEventListener('open', () => {
      if (wsRef.current === newWs) setStatus('connected')
    })

    newWs.addEventListener('close', () => {
      if (wsRef.current === newWs) {
        setStatus('disconnected')
        wsRef.current = null
      }
    })

    newWs.addEventListener('message', (event) => {
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

  return { messages, status, isStreaming, sendMessage, reconnect }
}
