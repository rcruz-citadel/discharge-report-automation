import { MultiSelect } from './MultiSelect'

interface PracticeMultiSelectProps {
  options: string[]
  value: string[]
  onChange: (value: string[]) => void
}

export function PracticeMultiSelect({ options, value, onChange }: PracticeMultiSelectProps) {
  return (
    <MultiSelect
      label="Practice"
      options={options}
      value={value}
      onChange={onChange}
      placeholder="All practices"
    />
  )
}
