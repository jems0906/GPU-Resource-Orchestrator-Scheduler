import { useLocation } from 'react-router-dom'
import { Bell, RefreshCw } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'

const titles: Record<string, string> = {
  '/': 'Dashboard',
  '/dashboard': 'Dashboard',
  '/jobs': 'Jobs',
  '/jobs/new': 'Submit Job',
  '/providers': 'Providers',
  '/analytics': 'Analytics',
}

export function Header() {
  const { pathname } = useLocation()
  const queryClient = useQueryClient()

  const title =
    titles[pathname] ||
    (pathname.startsWith('/jobs/') ? 'Job Detail' : 'GPU Orchestrator')

  return (
    <header className="h-14 bg-surface-800 border-b border-surface-700 flex items-center justify-between px-6 shrink-0">
      <h1 className="text-white font-semibold text-base">{title}</h1>
      <div className="flex items-center gap-2">
        <button
          onClick={() => queryClient.invalidateQueries()}
          className="p-2 text-slate-400 hover:text-white hover:bg-surface-700 rounded-lg transition-colors"
          title="Refresh all data"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
        <button aria-label="Notifications" className="p-2 text-slate-400 hover:text-white hover:bg-surface-700 rounded-lg transition-colors">
          <Bell className="w-4 h-4" />
        </button>
      </div>
    </header>
  )
}
