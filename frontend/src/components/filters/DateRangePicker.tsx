const labelStyle = {
  display: 'block',
  color: '#a8c4d8',
  fontSize: '11px',
  fontWeight: 600,
  textTransform: 'uppercase' as const,
  letterSpacing: '0.06em',
  marginBottom: '4px',
}

const inputStyle = {
  width: '100%',
  backgroundColor: '#ffffff',
  color: '#1a1a2e',  // dark text — critical per spec
  border: '1px solid #1b4459',
  borderRadius: '6px',
  padding: '6px 8px',
  fontSize: '13px',
  outline: 'none',
}

interface DateRangePickerProps {
  dateFrom: string | null
  dateTo: string | null
  min?: string
  max?: string
  onChangeDateFrom: (value: string | null) => void
  onChangeDateTo: (value: string | null) => void
}

export function DateRangePicker({
  dateFrom,
  dateTo,
  min,
  max,
  onChangeDateFrom,
  onChangeDateTo,
}: DateRangePickerProps) {
  return (
    <div className="flex flex-col gap-2">
      <div>
        <label style={labelStyle}>From Date</label>
        <input
          type="date"
          value={dateFrom ?? ''}
          min={min}
          max={dateTo ?? max}
          onChange={e => onChangeDateFrom(e.target.value || null)}
          style={inputStyle}
        />
      </div>
      <div>
        <label style={labelStyle}>To Date</label>
        <input
          type="date"
          value={dateTo ?? ''}
          min={dateFrom ?? min}
          max={max}
          onChange={e => onChangeDateTo(e.target.value || null)}
          style={inputStyle}
        />
      </div>
    </div>
  )
}
