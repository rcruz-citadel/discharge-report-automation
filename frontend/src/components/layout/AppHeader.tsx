interface AppHeaderProps {
  userName?: string
}

/**
 * Header: logo to the left, navy gradient banner to the right.
 * Spec: 5.5 Header Bar
 */
export function AppHeader({ userName }: AppHeaderProps) {
  return (
    <div className="flex items-center gap-5">
      {/* Logo — outside the banner */}
      <img
        src="/citadel-logo-hd-transparent.png"
        alt="Citadel Health"
        className="h-[56px] w-auto object-contain shrink-0"
      />

      {/* Navy gradient banner */}
      <div
        className="relative rounded-[14px] px-7 py-[18px] overflow-hidden flex-1"
        style={{
          background: 'linear-gradient(135deg, #132e45 0%, #1b4459 100%)',
          boxShadow: '0 4px 18px rgba(19,46,69,0.18)',
        }}
      >
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-[26px] font-extrabold text-white leading-tight">
              Discharge Report Dashboard
            </h1>
            <p className="text-[13px] text-[#a8c4d8] mt-0.5">
              Citadel Health — Outreach Tracking
            </p>
          </div>
          {userName && (
            <p className="text-[13px] text-[#a8c4d8]">
              Welcome, <span className="text-white font-semibold">{userName}</span>
            </p>
          )}
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
