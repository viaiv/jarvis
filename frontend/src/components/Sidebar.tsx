import { useCallback, useEffect, useState } from 'react'
import { listThreads } from '../api/chatApi'
import type { ThreadItem } from '../api/chatApi'

interface SidebarProps {
  isOpen: boolean
  onClose: () => void
  currentThreadId: string
  onSelectThread: (threadId: string) => void
  onNewThread: () => void
}

export default function Sidebar({ isOpen, onClose, currentThreadId, onSelectThread, onNewThread }: SidebarProps) {
  const [threads, setThreads] = useState<ThreadItem[]>([])
  const [loading, setLoading] = useState(false)

  const fetchThreads = useCallback(async () => {
    setLoading(true)
    try {
      const data = await listThreads()
      setThreads(data.threads)
    } catch {
      // silently fail
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (isOpen) {
      fetchThreads()
    }
  }, [isOpen, fetchThreads])

  return (
    <>
      {/* Overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/40 z-40 lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed top-0 left-0 h-full w-72 bg-surface border-r border-border z-50 flex flex-col transition-transform duration-300 ease-in-out ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 h-14 border-b border-border shrink-0">
          <span className="font-display font-bold text-[11px] tracking-[0.2em] uppercase text-text-secondary">
            Historico
          </span>
          <button
            onClick={onClose}
            className="w-7 h-7 rounded-lg flex items-center justify-center text-text-muted hover:text-text-secondary hover:bg-elevated transition-colors duration-200 cursor-pointer"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        {/* New chat button */}
        <div className="px-3 py-3 border-b border-border">
          <button
            onClick={() => { onNewThread(); onClose() }}
            className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg border border-border hover:border-accent/30 hover:bg-accent/4 text-text-secondary hover:text-accent transition-all duration-200 cursor-pointer"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            <span className="font-mono text-[11px] tracking-wide">Nova conversa</span>
          </button>
        </div>

        {/* Thread list */}
        <div className="flex-1 overflow-y-auto py-2">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <span className="text-[11px] text-text-muted font-mono">carregando...</span>
            </div>
          ) : threads.length === 0 ? (
            <div className="flex items-center justify-center py-8">
              <span className="text-[11px] text-text-muted font-mono">Nenhuma conversa</span>
            </div>
          ) : (
            <div className="space-y-0.5 px-2">
              {threads.map((thread) => {
                const isActive = thread.thread_id === currentThreadId
                return (
                  <button
                    key={thread.thread_id}
                    onClick={() => { onSelectThread(thread.thread_id); onClose() }}
                    className={`w-full text-left px-3 py-2.5 rounded-lg transition-all duration-200 group cursor-pointer ${
                      isActive
                        ? 'bg-accent/8 border border-accent/20'
                        : 'border border-transparent hover:bg-elevated hover:border-border'
                    }`}
                  >
                    <p className={`text-[12px] leading-relaxed truncate ${
                      isActive ? 'text-accent' : 'text-text-primary group-hover:text-text-primary'
                    }`}>
                      {thread.preview || 'Conversa sem titulo'}
                    </p>
                    <p className="text-[10px] text-text-muted font-mono mt-0.5">
                      {thread.message_count} mensagens
                    </p>
                  </button>
                )
              })}
            </div>
          )}
        </div>
      </aside>
    </>
  )
}
