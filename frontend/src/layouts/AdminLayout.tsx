import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

const navItems = [
  { to: '/admin/users', label: 'Usuarios' },
  { to: '/admin/logs', label: 'Logs' },
  { to: '/admin/config', label: 'Config' },
]

export default function AdminLayout() {
  const { user } = useAuth()

  return (
    <div className="flex h-screen bg-deep font-body text-text-primary">
      {/* Sidebar */}
      <aside className="w-56 border-r border-border flex flex-col shrink-0">
        {/* Brand */}
        <div className="flex items-center gap-3 px-5 h-14 border-b border-border">
          <div className="w-7 h-7 rounded-md bg-accent/10 border border-accent/25 flex items-center justify-center shadow-[0_0_12px_rgba(0,212,255,0.08)]">
            <span className="font-display font-bold text-accent text-xs leading-none">J</span>
          </div>
          <span className="font-display font-bold text-[11px] tracking-[0.2em] uppercase text-text-primary/90">
            Admin
          </span>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `block px-3 py-2 rounded-lg text-[13px] font-mono tracking-wide transition-all duration-200 ${
                  isActive
                    ? 'bg-accent/8 text-accent border border-accent/15'
                    : 'text-text-secondary hover:text-text-primary hover:bg-elevated/50 border border-transparent'
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div className="px-5 py-4 border-t border-border">
          <div className="text-[11px] text-text-muted font-mono tracking-wide mb-3">
            {user?.username}
          </div>
          <NavLink
            to="/"
            className="text-[11px] font-mono tracking-wide text-text-secondary hover:text-accent transition-colors duration-200"
          >
            &larr; Voltar ao chat
          </NavLink>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  )
}
