import { useCallback, useEffect, useState } from 'react'
import type { ToolInfo } from '../../types'
import * as api from '../../api/adminApi'

export default function ToolsPage() {
  const [tools, setTools] = useState<ToolInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    try {
      setLoading(true)
      const data = await api.listTools()
      setTools(data.tools)
    } catch {
      // silently fail
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  async function toggle(name: string) {
    setSaving(true)
    try {
      const updated = tools.map((t) =>
        t.name === name ? { ...t, enabled: !t.enabled } : t,
      )
      setTools(updated)

      const disabledTools = updated.filter((t) => !t.enabled).map((t) => t.name)
      const result = await api.updateTools(disabledTools)
      setTools(result.tools)
    } catch {
      await load()
    } finally {
      setSaving(false)
    }
  }

  // Agrupar por prefixo
  const groups: Record<string, ToolInfo[]> = {}
  for (const t of tools) {
    let group = 'Base'
    if (t.name.startsWith('cartola_')) group = 'Cartola FC'
    else if (t.name.startsWith('github_')) group = 'GitHub'
    if (!groups[group]) groups[group] = []
    groups[group].push(t)
  }

  return (
    <div className="p-8 max-w-3xl">
      <h1 className="font-display font-bold text-[18px] tracking-[0.15em] uppercase text-text-primary/90 mb-8">
        Ferramentas
      </h1>

      {loading ? (
        <div className="flex items-center gap-2 text-text-muted text-[13px] font-mono">
          <div className="h-1.5 w-1.5 rounded-full bg-accent animate-pulse" />
          Carregando...
        </div>
      ) : (
        <div className="space-y-6">
          {Object.entries(groups).map(([group, groupTools]) => (
            <section key={group}>
              <h2 className="font-mono text-[12px] text-text-secondary tracking-wide uppercase mb-3">
                {group}
              </h2>
              <div className="rounded-xl border border-border bg-surface/40 divide-y divide-border">
                {groupTools.map((t) => (
                  <div key={t.name} className="flex items-center justify-between px-5 py-3.5">
                    <div className="min-w-0 mr-4">
                      <p className="font-mono text-[13px] text-text-primary truncate">{t.name}</p>
                      <p className="text-[11px] text-text-muted mt-0.5 line-clamp-1">{t.description}</p>
                    </div>
                    <button
                      onClick={() => toggle(t.name)}
                      disabled={saving}
                      className={`relative flex-shrink-0 w-10 h-5.5 rounded-full transition-colors cursor-pointer disabled:opacity-50 ${
                        t.enabled
                          ? 'bg-accent/30 border border-accent/40'
                          : 'bg-surface border border-border'
                      }`}
                    >
                      <span
                        className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full transition-transform ${
                          t.enabled
                            ? 'translate-x-[18px] bg-accent'
                            : 'translate-x-0 bg-text-muted/40'
                        }`}
                      />
                    </button>
                  </div>
                ))}
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  )
}
