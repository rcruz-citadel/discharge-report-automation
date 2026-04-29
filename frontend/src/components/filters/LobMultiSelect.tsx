import { MultiSelect } from './MultiSelect'

interface LobMultiSelectProps {
  options: string[]
  value: string[]
  onChange: (value: string[]) => void
}

export function LobMultiSelect({ options, value, onChange }: LobMultiSelectProps) {
  return (
    <MultiSelect
      label="Line of Business"
      options={options}
      value={value}
      onChange={onChange}
      placeholder="All plan types"
    />
  )
}
