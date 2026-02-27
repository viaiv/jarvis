import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)

    const err = await login({ username, password })
    setSubmitting(false)

    if (err) {
      setError(err)
    } else {
      navigate('/', { replace: true })
    }
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-deep font-body text-text-primary px-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="flex flex-col items-center mb-10 animate-fade-in select-none">
          <div className="relative mb-6">
            <div className="absolute inset-0 rounded-2xl bg-accent/5 blur-2xl scale-150" />
            <div className="relative w-14 h-14 rounded-2xl bg-accent/8 border border-accent/20 flex items-center justify-center shadow-[0_0_40px_rgba(0,212,255,0.08)]">
              <span className="font-display font-extrabold text-accent text-xl leading-none">J</span>
            </div>
          </div>
          <h1 className="font-display font-bold text-[22px] tracking-[0.35em] uppercase text-text-primary/80 mb-3">
            Jarvis
          </h1>
          <div className="w-24 h-px bg-gradient-to-r from-transparent via-accent/30 to-transparent" />
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="username" className="block text-[11px] font-mono text-text-secondary tracking-wide uppercase mb-1.5">
              Usuario
            </label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              autoFocus
              autoComplete="username"
              className="w-full bg-surface/60 border border-border rounded-xl px-4 py-2.5 text-[14px] text-text-primary placeholder:text-text-muted outline-none font-body focus:border-accent/30 focus:shadow-[0_0_24px_rgba(0,212,255,0.04)] transition-all duration-300"
              placeholder="seu usuario"
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-[11px] font-mono text-text-secondary tracking-wide uppercase mb-1.5">
              Senha
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
              className="w-full bg-surface/60 border border-border rounded-xl px-4 py-2.5 text-[14px] text-text-primary placeholder:text-text-muted outline-none font-body focus:border-accent/30 focus:shadow-[0_0_24px_rgba(0,212,255,0.04)] transition-all duration-300"
              placeholder="sua senha"
            />
          </div>

          {error && (
            <p className="text-[12px] text-red-400 font-mono tracking-wide">{error}</p>
          )}

          <button
            type="submit"
            disabled={submitting || !username.trim() || !password}
            className="w-full py-2.5 rounded-xl bg-accent/10 border border-accent/20 text-accent font-display font-bold text-[13px] tracking-[0.15em] uppercase hover:bg-accent/20 hover:border-accent/30 disabled:opacity-30 disabled:cursor-not-allowed transition-all duration-200 cursor-pointer"
          >
            {submitting ? 'Entrando...' : 'Entrar'}
          </button>
        </form>
      </div>
    </div>
  )
}
