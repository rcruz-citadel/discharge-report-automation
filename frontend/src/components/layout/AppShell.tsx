import type { ReactNode } from 'react'

interface AppShellProps {
  sidebar: ReactNode
  children: ReactNode
}

/**
 * Main layout shell: 240px fixed sidebar + flex-1 main area.
 * Spec: 5.1 Layout Architecture
 */
export function AppShell({ sidebar, children }: AppShellProps) {
  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar: 240px fixed, navy background */}
      <aside
        className="w-60 shrink-0 overflow-y-auto flex flex-col"
        style={{ backgroundColor: '#132e45' }}
        role="navigation"
        aria-label="Filters"
      >
        {sidebar}
      </aside>

      {/* Main content area */}
      <main className="flex-1 overflow-y-auto bg-page p-6">
        {children}
      </main>
    </div>
  )
}
