import { NavLink } from 'react-router-dom'
import { LayoutDashboard, Cpu, Server, BarChart3, PlusCircle } from 'lucide-react'
import clsx from 'clsx'

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard', end: true },
  { to: '/jobs', icon: Cpu, label: 'Jobs' },
  { to: '/jobs/new', icon: PlusCircle, label: 'Submit Job' },
  { to: '/providers', icon: Server, label: 'Providers' },
  { to: '/analytics', icon: BarChart3, label: 'Analytics' },
]

export function Sidebar() {
  return (
    <aside className="w-60 bg-surface-800 border-r border-surface-700 flex flex-col shrink-0">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-surface-700">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
            <Cpu className="w-5 h-5 text-white" />
          </div>
          <div>
            <p className="font-bold text-sm leading-tight text-white">GPU Orchestrator</p>
            <p className="text-xs text-slate-400">Multi-Cloud Scheduler</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {navItems.map(({ to, icon: Icon, label, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                isActive
                  ? 'bg-primary-600 text-white'
                  : 'text-slate-400 hover:bg-surface-700 hover:text-white',
              )
            }
          >
            <Icon className="w-4 h-4 shrink-0" />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-surface-700 text-xs text-slate-500">
        v1.0.0 · 3 Providers
      </div>
    </aside>
  )
}
