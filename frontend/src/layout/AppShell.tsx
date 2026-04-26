import type { ReactNode } from 'react'
import { BarChart3, FilePlus2, LayoutDashboard, Menu, NotebookText } from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { clsx } from 'clsx'

export interface AppShellProps {
  children: ReactNode
}

const navItems = [
  { to: '/', label: '대시보드', icon: LayoutDashboard },
  { to: '/survey/create', label: '설문 만들기', icon: FilePlus2 },
  { to: '/survey/demo/results', label: '결과 통계', icon: BarChart3 },
  { to: '/guide', label: '작성 가이드', icon: NotebookText },
]

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="min-h-screen bg-slate-100">
      <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3 lg:px-6">
          <NavLink to="/" className="flex items-center gap-3">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-teal-600 text-sm font-black text-white">
              SQ
            </span>
            <span className="min-w-0">
              <span className="block text-sm font-black text-slate-950">Survey Quality</span>
              <span className="hidden text-xs font-semibold text-slate-500 sm:block">
                문항 품질 및 응답 신뢰도 분석
              </span>
            </span>
          </NavLink>

          <nav className="hidden items-center gap-1 md:flex">
            {navItems.map((item) => {
              const Icon = item.icon

              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) =>
                    clsx(
                      'inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm font-semibold transition',
                      isActive
                        ? 'bg-slate-900 text-white'
                        : 'text-slate-600 hover:bg-slate-100 hover:text-slate-950',
                    )
                  }
                >
                  <Icon size={16} />
                  {item.label}
                </NavLink>
              )
            })}
          </nav>

          <button
            type="button"
            className="inline-flex rounded-md border border-slate-300 p-2 text-slate-600 md:hidden"
            aria-label="모바일 메뉴"
          >
            <Menu size={18} />
          </button>
        </div>
        <nav className="flex gap-1 overflow-x-auto border-t border-slate-100 px-3 py-2 md:hidden">
          {navItems.map((item) => {
            const Icon = item.icon

            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  clsx(
                    'inline-flex shrink-0 items-center gap-2 rounded-md px-3 py-2 text-sm font-semibold',
                    isActive ? 'bg-slate-900 text-white' : 'bg-white text-slate-600',
                  )
                }
              >
                <Icon size={15} />
                {item.label}
              </NavLink>
            )
          })}
        </nav>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-5 lg:px-6">{children}</main>
    </div>
  )
}
