interface AppHeaderProps {
  userName?: string
}

/**
 * Full header region: logo row + navy gradient banner.
 * Logo and welcome sit above the banner on a clean line.
 * Spec: 5.5 Header Bar
 */
export function AppHeader({ userName }: AppHeaderProps) {
  return (
    <div className="flex flex-col gap-3">
      {/* Top row: logo + welcome */}
      <div className="flex items-center justify-between">
        <img
          src="/citadel-logo-hd-transparent.png"
          alt="Citadel Health"
          className="h-[52px] w-auto object-contain"
        />
        {userName && (
          <p className="text-[14px]" style={{ color: '#556e81' }}>
            Welcome, <span className="font-semibold" style={{ color: '#132e45' }}>{userName}</span>
          </p>
        )}
      </div>

      {/* Navy gradient banner */}
      <div
        className="relative rounded-[14px] px-7 py-4 overflow-hidden w-full"
        style={{
          background: 'linear-gradient(135deg, #132e45 0%, #1b4459 100%)',
          boxShadow: '0 4px 18px rgba(19,46,69,0.18)',
        }}
      >
        <div>
          <h1 className="text-[24px] font-extrabold text-white leading-tight">
            Discharge Report Dashboard
          </h1>
          <p className="text-[12.5px] text-[#a8c4d8] mt-0.5">
            Live discharge activity — filter, explore, and export
          </p>
        </div>
        {/* Right orange accent bar */}
        <div
          className="absolute right-0 top-0 bottom-0 w-[5px] rounded-r-[14px]"
          style={{ background: 'linear-gradient(180deg, #e07b2a 0%, #c96920 100%)' }}
          aria-hidden="true"
        />
      </div>
    </div>
  )
}
