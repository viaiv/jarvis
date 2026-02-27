import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import { useAuth } from './auth/AuthContext'
import { useChat } from './useChat'

function App() {
  const { user, logout } = useAuth()
  const { messages, status, isStreaming, sendMessage, reconnect } = useChat()
  const [input, setInput] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const text = input.trim()
    if (!text) return
    sendMessage(text)
    setInput('')
  }

  const isConnected = status === 'connected'

  return (
    <div className="flex flex-col h-screen bg-deep font-body text-text-primary">
      {/* Header */}
      <header className="flex items-center justify-between px-6 h-14 border-b border-border shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded-md bg-accent/10 border border-accent/25 flex items-center justify-center shadow-[0_0_12px_rgba(0,212,255,0.08)]">
            <span className="font-display font-bold text-accent text-xs leading-none">J</span>
          </div>
          <span className="font-display font-bold text-[13px] tracking-[0.2em] uppercase text-text-primary/90">
            Jarvis
          </span>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span
              className={`h-1.5 w-1.5 rounded-full transition-colors duration-300 ${
                isConnected
                  ? 'bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.5)]'
                  : status === 'connecting'
                    ? 'bg-amber-400 animate-pulse'
                    : 'bg-text-muted'
              }`}
            />
            <span className="text-[11px] text-text-secondary font-mono tracking-wide">
              {isConnected ? 'online' : status === 'connecting' ? 'connecting' : 'offline'}
            </span>
          </div>
          {user && (
            <div className="flex items-center gap-3">
              {user.role === 'admin' && (
                <Link
                  to="/admin"
                  className="text-[11px] text-text-muted font-mono tracking-wide hover:text-accent transition-colors duration-200"
                >
                  admin
                </Link>
              )}
              <span className="text-[11px] text-text-secondary font-mono tracking-wide">
                {user.username}
              </span>
              <button
                onClick={() => { logout(); reconnect() }}
                className="text-[11px] text-text-muted font-mono tracking-wide hover:text-accent transition-colors duration-200 cursor-pointer"
              >
                sair
              </button>
            </div>
          )}
        </div>
      </header>

      {/* Messages */}
      <main className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-3xl px-6 py-8">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center min-h-[60vh] animate-fade-in select-none">
              <div className="relative mb-8">
                <div className="absolute inset-0 rounded-2xl bg-accent/5 blur-2xl scale-150" />
                <div className="relative w-14 h-14 rounded-2xl bg-accent/8 border border-accent/20 flex items-center justify-center shadow-[0_0_40px_rgba(0,212,255,0.08)]">
                  <span className="font-display font-extrabold text-accent text-xl leading-none">J</span>
                </div>
              </div>
              <h2 className="font-display font-bold text-[22px] tracking-[0.35em] uppercase text-text-primary/80 mb-5">
                Jarvis
              </h2>
              <div className="w-24 h-px bg-gradient-to-r from-transparent via-accent/30 to-transparent mb-5" />
              <p className="text-[13px] text-text-muted tracking-wide">
                Assistente de estudo
              </p>
            </div>
          ) : (
            <div className="space-y-6">
              {messages.map((msg) => (
                <div key={msg.id} className="animate-slide-up">
                  {msg.role === 'user' ? (
                    <div className="flex justify-end">
                      <div className="max-w-[75%] bg-accent/6 border border-accent/12 rounded-2xl rounded-br-md px-4 py-2.5">
                        <p className="text-[14px] leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {/* Tool calls */}
                      {msg.toolCalls && msg.toolCalls.length > 0 && (
                        <div className="space-y-2 pl-4">
                          {msg.toolCalls.map((tc) => (
                            <div
                              key={tc.callId}
                              className={`inline-flex items-center gap-2.5 px-3 py-1.5 rounded-lg border font-mono text-[11px] transition-all duration-300 ${
                                tc.output == null
                                  ? 'border-accent/25 bg-accent/4'
                                  : 'border-border bg-surface/80'
                              }`}
                            >
                              <span
                                className={`h-1.5 w-1.5 rounded-full shrink-0 transition-colors duration-300 ${
                                  tc.output == null
                                    ? 'bg-accent animate-pulse shadow-[0_0_6px_rgba(0,212,255,0.4)]'
                                    : 'bg-emerald-400'
                                }`}
                              />
                              <span className="text-text-secondary font-medium">{tc.name}</span>
                              {tc.output != null && (
                                <>
                                  <span className="text-text-muted">→</span>
                                  <span className="text-text-secondary/80">{tc.output}</span>
                                </>
                              )}
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Content */}
                      {msg.content ? (
                        <div className="border-l-2 border-accent/15 pl-4">
                          <div className="jarvis-prose prose prose-invert prose-sm max-w-none">
                            <ReactMarkdown>{msg.content}</ReactMarkdown>
                          </div>
                        </div>
                      ) : (
                        <div className="border-l-2 border-accent/15 pl-4 py-1">
                          <span className="inline-block w-1.5 h-[18px] bg-accent/50 rounded-sm animate-blink" />
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>
      </main>

      {/* Input */}
      <div className="border-t border-border px-6 py-4 shrink-0">
        <form onSubmit={handleSubmit} className="mx-auto max-w-3xl">
          <div className="flex items-center gap-3 bg-surface/60 border border-border rounded-xl px-4 py-2.5 focus-within:border-accent/30 focus-within:shadow-[0_0_24px_rgba(0,212,255,0.04)] transition-all duration-300">
            <span className="text-accent/50 font-mono text-sm shrink-0 select-none">&gt;</span>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Digite sua mensagem..."
              disabled={!isConnected}
              className="flex-1 bg-transparent text-[14px] text-text-primary placeholder:text-text-muted outline-none font-body disabled:opacity-40"
            />
            <button
              type="submit"
              disabled={!isConnected || isStreaming || !input.trim()}
              className="w-8 h-8 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center text-accent hover:bg-accent/20 hover:border-accent/30 disabled:opacity-25 disabled:hover:bg-accent/10 transition-all duration-200 shrink-0 cursor-pointer"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="5" y1="12" x2="19" y2="12" />
                <polyline points="12 5 19 12 12 19" />
              </svg>
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default App
