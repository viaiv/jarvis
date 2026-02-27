import { useCallback, useEffect, useRef, useState } from 'react'
import type { ChatMessage, ConnectionStatus, ToolCall } from './types'

const WS_URL = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [status, setStatus] = useState<ConnectionStatus>('disconnected')
  const [isStreaming, setIsStreaming] = useState(false)

  const wsRef = useRef<WebSocket | null>(null)
  const threadIdRef = useRef(crypto.randomUUID())
  const assistantIdRef = useRef<string | null>(null)

  useEffect(() => {
    function connect() {
      setStatus('connecting')
      const ws = new WebSocket(WS_URL)

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

  return { messages, status, isStreaming, sendMessage }
}
