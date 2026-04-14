import { MultiSelect } from './MultiSelect'

interface PayerMultiSelectProps {
  options: string[]
  value: string[]
  onChange: (value: string[]) => void
}

export function PayerMultiSelect({ options, value, onChange }: PayerMultiSelectProps) {
  return (
    <MultiSelect
      label="Payer"
      options={options}
      value={value}
      onChange={onChange}
      placeholder="All payers"
    />
  )
}
