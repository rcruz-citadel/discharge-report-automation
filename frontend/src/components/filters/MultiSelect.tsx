/**
 * Reusable multi-select control for filter sidebar.
 * Tags shown as orange pills. Dark input text per spec feedback.
 */

const labelStyle = {
  display: 'block',
  color: '#a8c4d8',
  fontSize: '11px',
  fontWeight: 600,
  textTransform: 'uppercase' as const,
  letterSpacing: '0.06em',
  marginBottom: '4px',
}

interface MultiSelectProps {
  label: string
  options: string[]
  value: string[]
  onChange: (value: string[]) => void
  placeholder?: string
}

export function MultiSelect({ label, options, value, onChange, placeholder }: MultiSelectProps) {
  const toggleOption = (option: string) => {
    if (value.includes(option)) {
      onChange(value.filter(v => v !== option))
    } else {
      onChange([...value, option])
    }
  }

  return (
    <div>
      <label style={labelStyle}>{label}</label>

      {/* Selected tags */}
      {value.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-2">
          {value.map(v => (
            <button
              key={v}
              onClick={() => toggleOption(v)}
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium text-white"
              style={{ backgroundColor: '#e07b2a' }}
              title={`Remove ${v}`}
            >
              {v}
              <span aria-hidden="true" className="ml-0.5">×</span>
            </button>
          ))}
        </div>
      )}

      {/* Dropdown */}
      <select
        value=""
        onChange={e => {
          if (e.target.value) toggleOption(e.target.value)
          e.target.value = ''
        }}
        style={{
          width: '100%',
          backgroundColor: '#ffffff',
          color: '#1a1a2e',  // dark text — critical per spec
          border: '1px solid #1b4459',
          borderRadius: '6px',
          padding: '6px 8px',
          fontSize: '13px',
          outline: 'none',
        }}
      >
        <option value="" disabled>
          {value.length === 0 ? (placeholder ?? 'Select...') : `+ Add ${label.toLowerCase()}...`}
        </option>
        {options
          .filter(o => !value.includes(o))
          .map(o => (
            <option key={o} value={o}>
              {o}
            </option>
          ))}
      </select>
    </div>
  )
}
