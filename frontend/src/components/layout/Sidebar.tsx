import type { ReactNode } from 'react'
import { useAuth } from '../../auth/useAuth'

interface SidebarProps {
  filters: ReactNode
  onClearFilters: () => void
  hasActiveFilters: boolean
}

/**
 * Sidebar wrapper: logo, filters section, user info, sign out.
 * Spec: 5.5 Sidebar
 */
export function Sidebar({ filters, onClearFilters, hasActiveFilters }: SidebarProps) {
  const { user, logout } = useAuth()

  return (
    <div className="flex flex-col h-full p-4 gap-4">
      {/* Logo */}
      <div className="flex justify-center py-2">
        <img
          src="/citadel-logo-hd-transparent.png"
          alt="Citadel Health"
          className="w-[180px] object-contain"
        />
      </div>

      {/* Divider */}
      <div className="border-t border-[#1b4459]" />

      {/* Filters section */}
      <div className="flex-1 overflow-y-auto">
        <h2
          className="text-[15.2px] font-bold text-white pb-2 mb-3"
          style={{ borderBottom: '1px solid #1b4459' }}
        >
          Filters
        </h2>
        {filters}
      </div>

      {/* Divider */}
      <div className="border-t border-[#1b4459]" />

      {/* Clear filters button */}
      {hasActiveFilters && (
        <button
          onClick={onClearFilters}
          className="w-full py-1.5 px-3 rounded-md text-[13px] text-[#d6e6f0] font-medium transition-colors duration-150"
          style={{ border: '1.5px solid #1b4459' }}
          onMouseEnter={e => {
            ;(e.currentTarget as HTMLButtonElement).style.backgroundColor = '#1b4459'
            ;(e.currentTarget as HTMLButtonElement).style.color = '#ffffff'
          }}
          onMouseLeave={e => {
            ;(e.currentTarget as HTMLButtonElement).style.backgroundColor = 'transparent'
            ;(e.currentTarget as HTMLButtonElement).style.color = '#d6e6f0'
          }}
        >
          Clear All Filters
        </button>
      )}

      {/* Divider */}
      <div className="border-t border-[#1b4459]" />

      {/* User info + sign out */}
      <div className="flex flex-col gap-2">
        {user && (
          <div className="px-1">
            <p className="text-[13px] font-bold text-white truncate">{user.name}</p>
            <p className="text-[11px] text-[#7ea8c0] truncate">{user.email}</p>
          </div>
        )}
        <button
          onClick={logout}
          className="w-full py-1.5 px-3 rounded-md text-[13px] text-[#d6e6f0] font-medium transition-colors duration-150"
          style={{ border: '1.5px solid #1b4459' }}
          onMouseEnter={e => {
            ;(e.currentTarget as HTMLButtonElement).style.backgroundColor = '#1b4459'
            ;(e.currentTarget as HTMLButtonElement).style.color = '#ffffff'
          }}
          onMouseLeave={e => {
            ;(e.currentTarget as HTMLButtonElement).style.backgroundColor = 'transparent'
            ;(e.currentTarget as HTMLButtonElement).style.color = '#d6e6f0'
          }}
        >
          Sign Out
        </button>
      </div>
    </div>
  )
}
