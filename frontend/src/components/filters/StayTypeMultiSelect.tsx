import { MultiSelect } from './MultiSelect'

interface StayTypeMultiSelectProps {
  options: string[]
  value: string[]
  onChange: (value: string[]) => void
}

export function StayTypeMultiSelect({ options, value, onChange }: StayTypeMultiSelectProps) {
  return (
    <MultiSelect
      label="Stay Type"
      options={options}
      value={value}
      onChange={onChange}
      placeholder="All stay types"
    />
  )
}
