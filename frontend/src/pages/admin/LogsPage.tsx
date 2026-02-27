import { useCallback, useEffect, useState } from 'react'
import type { ThreadMessage, ThreadSummary } from '../../types'
import * as api from '../../api/adminApi'

const PAGE_SIZE = 20

export default function LogsPage() {
  const [threads, setThreads] = useState<ThreadSummary[]>([])
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)
  const [loading, setLoading] = useState(true)
  const [filterUser, setFilterUser] = useState('')
  const [selectedThread, setSelectedThread] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      setLoading(true)
      const params: { limit: number; offset: number; user_id?: number } = {
        limit: PAGE_SIZE,
        offset,
      }
      const uid = parseInt(filterUser)
      if (!isNaN(uid)) params.user_id = uid
      const data = await api.listThreads(params)
      setThreads(data.threads)
      setTotal(data.total)
    } catch {
      // silently fail
    } finally {
      setLoading(false)
    }
  }, [offset, filterUser])

  useEffect(() => { load() }, [load])

  const totalPages = Math.ceil(total / PAGE_SIZE)
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1

  return (
    <div className="p-8 max-w-5xl">
      <h1 className="font-display font-bold text-[18px] tracking-[0.15em] uppercase text-text-primary/90 mb-6">
        Logs de conversa
      </h1>

      {/* Filter */}
      <div className="flex items-center gap-3 mb-5">
        <label className="text-[11px] font-mono text-text-muted tracking-wide uppercase">Filtrar por user ID:</label>
        <input
          value={filterUser}
          onChange={(e) => { setFilterUser(e.target.value); setOffset(0) }}
          placeholder="ex: 1"
          className="w-24 bg-surface border border-border rounded-lg px-3 py-1.5 text-[13px] text-text-primary outline-none focus:border-accent/30 font-mono placeholder:text-text-muted"
        />
        <span className="text-[11px] text-text-muted font-mono">
          {total} thread{total !== 1 ? 's' : ''}
        </span>
      </div>

      {selectedThread ? (
        <ThreadDetail
          threadId={selectedThread}
          onBack={() => setSelectedThread(null)}
        />
      ) : (
        <>
          {loading ? (
            <div className="flex items-center gap-2 text-text-muted text-[13px] font-mono">
              <div className="h-1.5 w-1.5 rounded-full bg-accent animate-pulse" />
              Carregando...
            </div>
          ) : threads.length === 0 ? (
            <p className="text-text-muted text-[13px] font-mono">Nenhum thread encontrado.</p>
          ) : (
            <div className="border border-border rounded-xl overflow-hidden">
              <table className="w-full text-[13px]">
                <thead>
                  <tr className="bg-surface/60 text-text-secondary font-mono text-[11px] tracking-wide uppercase">
                    <th className="text-left px-4 py-3">Thread ID</th>
                    <th className="text-left px-4 py-3">Usuario</th>
                    <th className="text-right px-4 py-3">Acoes</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {threads.map((t) => (
                    <tr key={t.thread_id} className="hover:bg-elevated/20 transition-colors">
                      <td className="px-4 py-3 font-mono text-text-primary text-[12px]">
                        {t.thread_id}
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-text-secondary text-[12px] font-mono">
                          {t.username ?? `#${t.user_id ?? '?'}`}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={() => setSelectedThread(t.thread_id)}
                          className="px-3 py-1 rounded-md text-[11px] font-mono tracking-wide border border-border text-text-secondary hover:text-accent hover:border-accent/20 transition-colors cursor-pointer"
                        >
                          ver mensagens
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between mt-4">
              <button
                onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                disabled={offset === 0}
                className="px-3 py-1.5 rounded-lg border border-border text-[11px] font-mono text-text-secondary hover:text-text-primary disabled:opacity-30 transition-colors cursor-pointer disabled:cursor-not-allowed"
              >
                &larr; Anterior
              </button>
              <span className="text-[11px] font-mono text-text-muted">
                Pagina {currentPage} de {totalPages}
              </span>
              <button
                onClick={() => setOffset(offset + PAGE_SIZE)}
                disabled={offset + PAGE_SIZE >= total}
                className="px-3 py-1.5 rounded-lg border border-border text-[11px] font-mono text-text-secondary hover:text-text-primary disabled:opacity-30 transition-colors cursor-pointer disabled:cursor-not-allowed"
              >
                Proxima &rarr;
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}

function ThreadDetail({ threadId, onBack }: { threadId: string; onBack: () => void }) {
  const [messages, setMessages] = useState<ThreadMessage[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getThreadMessages(threadId)
      .then(setMessages)
      .finally(() => setLoading(false))
  }, [threadId])

  return (
    <div>
      <button
        onClick={onBack}
        className="mb-4 text-[12px] font-mono text-text-secondary hover:text-accent transition-colors cursor-pointer"
      >
        &larr; Voltar
      </button>

      <div className="mb-4 px-4 py-2.5 rounded-lg border border-border bg-surface/40">
        <span className="text-[11px] font-mono text-text-muted tracking-wide uppercase">Thread: </span>
        <span className="text-[12px] font-mono text-text-primary">{threadId}</span>
      </div>

      {loading ? (
        <div className="flex items-center gap-2 text-text-muted text-[13px] font-mono">
          <div className="h-1.5 w-1.5 rounded-full bg-accent animate-pulse" />
          Carregando...
        </div>
      ) : messages.length === 0 ? (
        <p className="text-text-muted text-[13px] font-mono">Nenhuma mensagem.</p>
      ) : (
        <div className="space-y-3">
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`px-4 py-3 rounded-xl border ${
                msg.role === 'user'
                  ? 'border-accent/12 bg-accent/4'
                  : 'border-border bg-surface/40'
              }`}
            >
              <div className="flex items-center gap-2 mb-1.5">
                <span className={`text-[10px] font-mono tracking-wide uppercase font-bold ${
                  msg.role === 'user' ? 'text-accent' : 'text-text-secondary'
                }`}>
                  {msg.role === 'user' ? 'usuario' : 'assistente'}
                </span>
              </div>
              <p className="text-[13px] text-text-primary whitespace-pre-wrap leading-relaxed">
                {msg.content}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
