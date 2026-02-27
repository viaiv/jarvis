import { useCallback, useEffect, useState } from 'react'
import type { AdminUser, ConfigData } from '../../types'
import * as api from '../../api/adminApi'

export default function ConfigPage() {
  const [globalConfig, setGlobalConfig] = useState<ConfigData>({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  const [users, setUsers] = useState<AdminUser[]>([])
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null)
  const [userConfig, setUserConfig] = useState<ConfigData>({})
  const [userLoading, setUserLoading] = useState(false)
  const [userSaving, setUserSaving] = useState(false)
  const [userSaved, setUserSaved] = useState(false)

  const loadGlobal = useCallback(async () => {
    try {
      setLoading(true)
      const config = await api.getGlobalConfig()
      setGlobalConfig(config)
    } catch {
      // silently fail
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadGlobal() }, [loadGlobal])

  useEffect(() => {
    api.listUsers().then(setUsers).catch(() => {})
  }, [])

  useEffect(() => {
    if (selectedUserId == null) return
    setUserLoading(true)
    api.getUserConfig(selectedUserId)
      .then(setUserConfig)
      .finally(() => setUserLoading(false))
  }, [selectedUserId])

  async function saveGlobal() {
    setSaving(true)
    setSaved(false)
    try {
      const result = await api.setGlobalConfig(globalConfig)
      setGlobalConfig(result)
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch {
      // silently fail
    } finally {
      setSaving(false)
    }
  }

  async function saveUserConfig() {
    if (selectedUserId == null) return
    setUserSaving(true)
    setUserSaved(false)
    try {
      const result = await api.setUserConfig(selectedUserId, userConfig)
      setUserConfig(result)
      setUserSaved(true)
      setTimeout(() => setUserSaved(false), 2000)
    } catch {
      // silently fail
    } finally {
      setUserSaving(false)
    }
  }

  return (
    <div className="p-8 max-w-3xl">
      <h1 className="font-display font-bold text-[18px] tracking-[0.15em] uppercase text-text-primary/90 mb-8">
        Configuracao
      </h1>

      {/* Global config */}
      <section className="mb-10">
        <h2 className="font-mono text-[12px] text-text-secondary tracking-wide uppercase mb-4">
          Config global
        </h2>

        {loading ? (
          <div className="flex items-center gap-2 text-text-muted text-[13px] font-mono">
            <div className="h-1.5 w-1.5 rounded-full bg-accent animate-pulse" />
            Carregando...
          </div>
        ) : (
          <ConfigForm
            config={globalConfig}
            onChange={setGlobalConfig}
            onSave={saveGlobal}
            saving={saving}
            saved={saved}
          />
        )}
      </section>

      {/* User config */}
      <section>
        <h2 className="font-mono text-[12px] text-text-secondary tracking-wide uppercase mb-4">
          Config por usuario
        </h2>

        <div className="flex items-center gap-3 mb-4">
          <label className="text-[11px] font-mono text-text-muted tracking-wide uppercase">Usuario:</label>
          <select
            value={selectedUserId ?? ''}
            onChange={(e) => {
              const val = e.target.value
              setSelectedUserId(val ? parseInt(val) : null)
              setUserConfig({})
              setUserSaved(false)
            }}
            className="bg-surface border border-border rounded-lg px-3 py-1.5 text-[13px] text-text-primary outline-none focus:border-accent/30 font-mono"
          >
            <option value="">-- selecionar --</option>
            {users.map((u) => (
              <option key={u.id} value={u.id}>
                {u.username} (#{u.id})
              </option>
            ))}
          </select>
        </div>

        {selectedUserId != null && (
          userLoading ? (
            <div className="flex items-center gap-2 text-text-muted text-[13px] font-mono">
              <div className="h-1.5 w-1.5 rounded-full bg-accent animate-pulse" />
              Carregando...
            </div>
          ) : (
            <ConfigForm
              config={userConfig}
              onChange={setUserConfig}
              onSave={saveUserConfig}
              saving={userSaving}
              saved={userSaved}
            />
          )
        )}
      </section>
    </div>
  )
}

function ConfigForm({
  config,
  onChange,
  onSave,
  saving,
  saved,
}: {
  config: ConfigData
  onChange: (c: ConfigData) => void
  onSave: () => void
  saving: boolean
  saved: boolean
}) {
  return (
    <div className="p-5 rounded-xl border border-border bg-surface/40 space-y-4">
      <div>
        <label className="block text-[11px] font-mono text-text-muted tracking-wide uppercase mb-1">
          Model name
        </label>
        <input
          value={config.model_name ?? ''}
          onChange={(e) => onChange({ ...config, model_name: e.target.value || null })}
          placeholder="ex: gpt-4.1-mini"
          className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-[13px] text-text-primary outline-none focus:border-accent/30 font-mono placeholder:text-text-muted"
        />
      </div>

      <div>
        <label className="block text-[11px] font-mono text-text-muted tracking-wide uppercase mb-1">
          System prompt
        </label>
        <textarea
          value={config.system_prompt ?? ''}
          onChange={(e) => onChange({ ...config, system_prompt: e.target.value || null })}
          rows={4}
          placeholder="Prompt de sistema..."
          className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-[13px] text-text-primary outline-none focus:border-accent/30 font-mono placeholder:text-text-muted resize-y"
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-[11px] font-mono text-text-muted tracking-wide uppercase mb-1">
            History window
          </label>
          <input
            type="number"
            value={config.history_window ?? ''}
            onChange={(e) => onChange({ ...config, history_window: e.target.value ? parseInt(e.target.value) : null })}
            placeholder="ex: 3"
            className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-[13px] text-text-primary outline-none focus:border-accent/30 font-mono placeholder:text-text-muted"
          />
        </div>
        <div>
          <label className="block text-[11px] font-mono text-text-muted tracking-wide uppercase mb-1">
            Max tool steps
          </label>
          <input
            type="number"
            value={config.max_tool_steps ?? ''}
            onChange={(e) => onChange({ ...config, max_tool_steps: e.target.value ? parseInt(e.target.value) : null })}
            placeholder="ex: 5"
            className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-[13px] text-text-primary outline-none focus:border-accent/30 font-mono placeholder:text-text-muted"
          />
        </div>
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={onSave}
          disabled={saving}
          className="px-4 py-2 rounded-lg bg-accent/10 border border-accent/20 text-accent font-mono text-[12px] tracking-wide hover:bg-accent/20 transition-colors cursor-pointer disabled:opacity-50"
        >
          {saving ? 'Salvando...' : 'Salvar'}
        </button>
        {saved && (
          <span className="text-[11px] font-mono text-emerald-400 tracking-wide animate-fade-in">
            Salvo
          </span>
        )}
      </div>
    </div>
  )
}
