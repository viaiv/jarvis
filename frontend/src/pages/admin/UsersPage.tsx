import { useCallback, useEffect, useState } from 'react'
import type { AdminUser, UserCreate } from '../../types'
import * as api from '../../api/adminApi'

export default function UsersPage() {
  const [users, setUsers] = useState<AdminUser[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showCreate, setShowCreate] = useState(false)

  const load = useCallback(async () => {
    try {
      setLoading(true)
      setUsers(await api.listUsers())
      setError(null)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Erro ao carregar usuarios')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  return (
    <div className="p-8 max-w-5xl">
      <div className="flex items-center justify-between mb-6">
        <h1 className="font-display font-bold text-[18px] tracking-[0.15em] uppercase text-text-primary/90">
          Usuarios
        </h1>
        <button
          onClick={() => setShowCreate(true)}
          className="px-4 py-2 rounded-lg bg-accent/10 border border-accent/20 text-accent font-mono text-[12px] tracking-wide hover:bg-accent/20 hover:border-accent/30 transition-all duration-200 cursor-pointer"
        >
          + Novo usuario
        </button>
      </div>

      {error && (
        <div className="mb-4 px-4 py-2.5 rounded-lg border border-red-500/20 bg-red-500/5 text-[12px] text-red-400 font-mono">
          {error}
        </div>
      )}

      {showCreate && (
        <CreateUserForm
          onCreated={() => { setShowCreate(false); load() }}
          onCancel={() => setShowCreate(false)}
        />
      )}

      {loading ? (
        <div className="flex items-center gap-2 text-text-muted text-[13px] font-mono">
          <div className="h-1.5 w-1.5 rounded-full bg-accent animate-pulse" />
          Carregando...
        </div>
      ) : (
        <div className="border border-border rounded-xl overflow-hidden">
          <table className="w-full text-[13px]">
            <thead>
              <tr className="bg-surface/60 text-text-secondary font-mono text-[11px] tracking-wide uppercase">
                <th className="text-left px-4 py-3">ID</th>
                <th className="text-left px-4 py-3">Username</th>
                <th className="text-left px-4 py-3">Email</th>
                <th className="text-left px-4 py-3">Role</th>
                <th className="text-left px-4 py-3">Status</th>
                <th className="text-right px-4 py-3">Acoes</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {users.map((u) => (
                <UserRow key={u.id} user={u} onUpdated={load} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function UserRow({ user, onUpdated }: { user: AdminUser; onUpdated: () => void }) {
  const [editing, setEditing] = useState(false)
  const [email, setEmail] = useState(user.email)
  const [role, setRole] = useState(user.role)
  const [isActive, setIsActive] = useState(user.is_active)
  const [newPassword, setNewPassword] = useState('')
  const [saving, setSaving] = useState(false)

  async function handleSave() {
    setSaving(true)
    try {
      await api.updateUser(user.id, { email, role, is_active: isActive })
      if (newPassword) {
        await api.updatePassword(user.id, newPassword)
      }
      setEditing(false)
      setNewPassword('')
      onUpdated()
    } catch {
      // error handling via parent reload
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete() {
    if (!confirm(`Remover usuario "${user.username}"?`)) return
    try {
      await api.deleteUser(user.id)
      onUpdated()
    } catch {
      // silently fail, will show stale
    }
  }

  if (editing) {
    return (
      <tr className="bg-elevated/30">
        <td className="px-4 py-3 font-mono text-text-muted">{user.id}</td>
        <td className="px-4 py-3 font-mono text-text-secondary">{user.username}</td>
        <td className="px-4 py-3">
          <input
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full bg-surface border border-border rounded-lg px-3 py-1.5 text-[13px] text-text-primary outline-none focus:border-accent/30 font-mono"
          />
        </td>
        <td className="px-4 py-3">
          <select
            value={role}
            onChange={(e) => setRole(e.target.value)}
            className="bg-surface border border-border rounded-lg px-3 py-1.5 text-[13px] text-text-primary outline-none focus:border-accent/30 font-mono"
          >
            <option value="user">user</option>
            <option value="admin">admin</option>
          </select>
        </td>
        <td className="px-4 py-3">
          <button
            onClick={() => setIsActive(!isActive)}
            className={`px-2.5 py-1 rounded-md text-[11px] font-mono tracking-wide border transition-colors ${
              isActive
                ? 'border-emerald-500/20 bg-emerald-500/8 text-emerald-400'
                : 'border-red-500/20 bg-red-500/8 text-red-400'
            }`}
          >
            {isActive ? 'ativo' : 'inativo'}
          </button>
        </td>
        <td className="px-4 py-3">
          <div className="flex flex-col items-end gap-2">
            <input
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="nova senha (opcional)"
              type="password"
              className="w-40 bg-surface border border-border rounded-lg px-3 py-1.5 text-[12px] text-text-primary outline-none focus:border-accent/30 font-mono placeholder:text-text-muted"
            />
            <div className="flex gap-2">
              <button
                onClick={handleSave}
                disabled={saving}
                className="px-3 py-1 rounded-md text-[11px] font-mono tracking-wide bg-accent/10 border border-accent/20 text-accent hover:bg-accent/20 transition-colors cursor-pointer disabled:opacity-50"
              >
                {saving ? '...' : 'salvar'}
              </button>
              <button
                onClick={() => { setEditing(false); setEmail(user.email); setRole(user.role); setIsActive(user.is_active); setNewPassword('') }}
                className="px-3 py-1 rounded-md text-[11px] font-mono tracking-wide border border-border text-text-secondary hover:text-text-primary transition-colors cursor-pointer"
              >
                cancelar
              </button>
            </div>
          </div>
        </td>
      </tr>
    )
  }

  return (
    <tr className="hover:bg-elevated/20 transition-colors">
      <td className="px-4 py-3 font-mono text-text-muted">{user.id}</td>
      <td className="px-4 py-3 font-mono text-text-primary">{user.username}</td>
      <td className="px-4 py-3 text-text-secondary">{user.email}</td>
      <td className="px-4 py-3">
        <span className={`px-2 py-0.5 rounded text-[11px] font-mono tracking-wide ${
          user.role === 'admin'
            ? 'bg-accent/8 text-accent border border-accent/15'
            : 'bg-surface text-text-secondary border border-border'
        }`}>
          {user.role}
        </span>
      </td>
      <td className="px-4 py-3">
        <span className={`inline-flex items-center gap-1.5 text-[11px] font-mono tracking-wide ${
          user.is_active ? 'text-emerald-400' : 'text-red-400'
        }`}>
          <span className={`h-1.5 w-1.5 rounded-full ${user.is_active ? 'bg-emerald-400' : 'bg-red-400'}`} />
          {user.is_active ? 'ativo' : 'inativo'}
        </span>
      </td>
      <td className="px-4 py-3 text-right">
        <div className="flex justify-end gap-2">
          <button
            onClick={() => setEditing(true)}
            className="px-3 py-1 rounded-md text-[11px] font-mono tracking-wide border border-border text-text-secondary hover:text-accent hover:border-accent/20 transition-colors cursor-pointer"
          >
            editar
          </button>
          <button
            onClick={handleDelete}
            className="px-3 py-1 rounded-md text-[11px] font-mono tracking-wide border border-border text-text-secondary hover:text-red-400 hover:border-red-500/20 transition-colors cursor-pointer"
          >
            remover
          </button>
        </div>
      </td>
    </tr>
  )
}

function CreateUserForm({ onCreated, onCancel }: { onCreated: () => void; onCancel: () => void }) {
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState('user')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    setError(null)
    try {
      const data: UserCreate = { username, email, password }
      if (role !== 'user') data.role = role
      await api.createUser(data)
      onCreated()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Erro ao criar usuario')
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="mb-6 p-5 rounded-xl border border-border bg-surface/40 space-y-4">
      <h3 className="font-mono text-[12px] text-text-secondary tracking-wide uppercase">Novo usuario</h3>

      {error && (
        <p className="text-[12px] text-red-400 font-mono">{error}</p>
      )}

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-[11px] font-mono text-text-muted tracking-wide uppercase mb-1">Username</label>
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-[13px] text-text-primary outline-none focus:border-accent/30 font-mono"
          />
        </div>
        <div>
          <label className="block text-[11px] font-mono text-text-muted tracking-wide uppercase mb-1">Email</label>
          <input
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            type="email"
            required
            className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-[13px] text-text-primary outline-none focus:border-accent/30 font-mono"
          />
        </div>
        <div>
          <label className="block text-[11px] font-mono text-text-muted tracking-wide uppercase mb-1">Senha</label>
          <input
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            type="password"
            required
            className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-[13px] text-text-primary outline-none focus:border-accent/30 font-mono"
          />
        </div>
        <div>
          <label className="block text-[11px] font-mono text-text-muted tracking-wide uppercase mb-1">Role</label>
          <select
            value={role}
            onChange={(e) => setRole(e.target.value)}
            className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-[13px] text-text-primary outline-none focus:border-accent/30 font-mono"
          >
            <option value="user">user</option>
            <option value="admin">admin</option>
          </select>
        </div>
      </div>

      <div className="flex gap-2">
        <button
          type="submit"
          disabled={saving}
          className="px-4 py-2 rounded-lg bg-accent/10 border border-accent/20 text-accent font-mono text-[12px] tracking-wide hover:bg-accent/20 transition-colors cursor-pointer disabled:opacity-50"
        >
          {saving ? 'Criando...' : 'Criar'}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 rounded-lg border border-border text-text-secondary font-mono text-[12px] tracking-wide hover:text-text-primary transition-colors cursor-pointer"
        >
          Cancelar
        </button>
      </div>
    </form>
  )
}
