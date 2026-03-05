import { useCallback, useEffect, useState } from 'react'
import type { AgentRun } from '../../types'
import * as api from '../../api/adminApi'

const PAGE_SIZE = 20

const STATUS_COLORS: Record<string, string> = {
  processing: 'text-yellow-400 bg-yellow-400/10 border-yellow-400/20',
  completed: 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20',
  failed: 'text-red-400 bg-red-400/10 border-red-400/20',
}

function StatusBadge({ status }: { status: string }) {
  const colors = STATUS_COLORS[status] ?? 'text-text-secondary bg-surface border-border'
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md border text-[11px] font-mono tracking-wide ${colors}`}>
      {status === 'processing' && <span className="h-1.5 w-1.5 rounded-full bg-yellow-400 animate-pulse" />}
      {status}
    </span>
  )
}

function formatDate(iso: string | null): string {
  if (!iso) return '-'
  const d = new Date(iso)
  return d.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'medium' })
}

export default function AgentRunsPage() {
  const [runs, setRuns] = useState<AgentRun[]>([])
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState('')
  const [selected, setSelected] = useState<AgentRun | null>(null)

  const load = useCallback(async () => {
    try {
      setLoading(true)
      const params: { limit: number; offset: number; status?: string } = {
        limit: PAGE_SIZE,
        offset,
      }
      if (statusFilter) params.status = statusFilter
      const data = await api.listAgentRuns(params)
      setRuns(data.runs)
      setTotal(data.total)
    } catch {
      // silently fail
    } finally {
      setLoading(false)
    }
  }, [offset, statusFilter])

  useEffect(() => { load() }, [load])

  const totalPages = Math.ceil(total / PAGE_SIZE)
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1

  if (selected) {
    return (
      <div className="p-8 max-w-5xl">
        <button
          onClick={() => setSelected(null)}
          className="mb-4 text-[12px] font-mono text-text-secondary hover:text-accent transition-colors cursor-pointer"
        >
          &larr; Voltar
        </button>

        <h1 className="font-display font-bold text-[18px] tracking-[0.15em] uppercase text-text-primary/90 mb-6">
          Run #{selected.id}
        </h1>

        <div className="space-y-3">
          <DetailRow label="Repo" value={selected.repo} />
          <DetailRow label="Issue" value={`#${selected.issue_number} - ${selected.issue_title}`} />
          <DetailRow label="Action" value={selected.action} />
          <DetailRow label="Category" value={selected.category ?? '-'} />
          <DetailRow label="Status">
            <StatusBadge status={selected.status} />
          </DetailRow>
          <DetailRow label="Tool steps" value={String(selected.tool_steps)} />
          <DetailRow label="Iniciado" value={formatDate(selected.started_at)} />
          <DetailRow label="Finalizado" value={formatDate(selected.finished_at)} />
          {selected.error_message && (
            <div className="mt-4">
              <span className="text-[11px] font-mono text-text-muted tracking-wide uppercase block mb-2">Erro</span>
              <pre className="text-[12px] font-mono text-red-400 bg-red-400/5 border border-red-400/15 rounded-xl px-4 py-3 whitespace-pre-wrap">
                {selected.error_message}
              </pre>
            </div>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="p-8 max-w-5xl">
      <h1 className="font-display font-bold text-[18px] tracking-[0.15em] uppercase text-text-primary/90 mb-6">
        Agent Runs
      </h1>

      {/* Filter */}
      <div className="flex items-center gap-3 mb-5">
        <label className="text-[11px] font-mono text-text-muted tracking-wide uppercase">Status:</label>
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setOffset(0) }}
          className="bg-surface border border-border rounded-lg px-3 py-1.5 text-[13px] text-text-primary outline-none focus:border-accent/30 font-mono"
        >
          <option value="">Todos</option>
          <option value="processing">processing</option>
          <option value="completed">completed</option>
          <option value="failed">failed</option>
        </select>
        <span className="text-[11px] text-text-muted font-mono">
          {total} run{total !== 1 ? 's' : ''}
        </span>
      </div>

      {loading ? (
        <div className="flex items-center gap-2 text-text-muted text-[13px] font-mono">
          <div className="h-1.5 w-1.5 rounded-full bg-accent animate-pulse" />
          Carregando...
        </div>
      ) : runs.length === 0 ? (
        <p className="text-text-muted text-[13px] font-mono">Nenhum agent run encontrado.</p>
      ) : (
        <div className="border border-border rounded-xl overflow-hidden">
          <table className="w-full text-[13px]">
            <thead>
              <tr className="bg-surface/60 text-text-secondary font-mono text-[11px] tracking-wide uppercase">
                <th className="text-left px-4 py-3">ID</th>
                <th className="text-left px-4 py-3">Repo</th>
                <th className="text-left px-4 py-3">Issue</th>
                <th className="text-left px-4 py-3">Categoria</th>
                <th className="text-left px-4 py-3">Status</th>
                <th className="text-left px-4 py-3">Inicio</th>
                <th className="text-right px-4 py-3">Acoes</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {runs.map((run) => (
                <tr key={run.id} className="hover:bg-elevated/20 transition-colors">
                  <td className="px-4 py-3 font-mono text-text-muted text-[12px]">
                    #{run.id}
                  </td>
                  <td className="px-4 py-3 font-mono text-text-primary text-[12px]">
                    {run.repo}
                  </td>
                  <td className="px-4 py-3 text-text-primary text-[12px]">
                    <span className="text-text-muted font-mono">#{run.issue_number}</span>{' '}
                    {run.issue_title}
                  </td>
                  <td className="px-4 py-3 font-mono text-text-secondary text-[12px]">
                    {run.category ?? '-'}
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={run.status} />
                  </td>
                  <td className="px-4 py-3 font-mono text-text-muted text-[11px]">
                    {formatDate(run.started_at)}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => setSelected(run)}
                      className="px-3 py-1 rounded-md text-[11px] font-mono tracking-wide border border-border text-text-secondary hover:text-accent hover:border-accent/20 transition-colors cursor-pointer"
                    >
                      detalhes
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
    </div>
  )
}

function DetailRow({ label, value, children }: { label: string; value?: string; children?: React.ReactNode }) {
  return (
    <div className="flex items-center gap-4 px-4 py-2.5 rounded-lg border border-border bg-surface/40">
      <span className="text-[11px] font-mono text-text-muted tracking-wide uppercase w-28 shrink-0">{label}</span>
      {children ?? <span className="text-[13px] font-mono text-text-primary">{value}</span>}
    </div>
  )
}
