import type { AssigneeInfo } from '../../types/api'

interface AssigneeSelectProps {
  assignees: AssigneeInfo[]
  value: string
  onChange: (value: string) => void
}

const labelStyle = {
  display: 'block',
  color: '#a8c4d8',
  fontSize: '11px',
  fontWeight: 600,
  textTransform: 'uppercase' as const,
  letterSpacing: '0.06em',
  marginBottom: '4px',
}

const selectStyle = {
  width: '100%',
  backgroundColor: '#ffffff',
  color: '#1a1a2e',  // dark text — critical per spec feedback
  border: '1px solid #1b4459',
  borderRadius: '6px',
  padding: '6px 8px',
  fontSize: '13px',
  outline: 'none',
}

export function AssigneeSelect({ assignees, value, onChange }: AssigneeSelectProps) {
  return (
    <div>
      <label style={labelStyle}>Assigned To</label>
      <select
        value={value}
        onChange={e => onChange(e.target.value)}
        style={selectStyle}
      >
        <option value="All">All Staff</option>
        {assignees.map(a => (
          <option key={a.name} value={a.name}>
            {a.name}
          </option>
        ))}
      </select>
    </div>
  )
}
