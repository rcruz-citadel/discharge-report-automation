import { clsx, type ClassValue } from 'clsx'
import { format, parseISO } from 'date-fns'

/** Merge class names conditionally. */
export function cn(...inputs: ClassValue[]) {
  return clsx(inputs)
}

/** Format an ISO date string as "MMM d, yyyy" (e.g. "Mar 15, 2026"). */
export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return '—'
  try {
    return format(parseISO(dateStr), 'MMM d, yyyy')
  } catch {
    return dateStr
  }
}

/** Format an ISO datetime string as "MMM d, yyyy h:mm a". */
export function formatDateTime(dateStr: string | null | undefined): string {
  if (!dateStr) return '—'
  try {
    return format(parseISO(dateStr), 'MMM d, yyyy h:mm a')
  } catch {
    return dateStr
  }
}

/** Truncate a string to maxLen, appending '…' if truncated. */
export function truncate(str: string | null | undefined, maxLen: number): string {
  if (!str) return '—'
  return str.length > maxLen ? str.slice(0, maxLen) + '…' : str
}

/** Render a value or em dash for null/undefined/empty. */
export function orDash(val: string | number | null | undefined): string {
  if (val === null || val === undefined || val === '' || val === 0) return '—'
  return String(val)
}

/** Generate a filename-safe timestamp string like "20260415_143022". */
export function fileTimestamp(): string {
  return format(new Date(), 'yyyyMMdd_HHmmss')
}

/** Export an array of objects to CSV and trigger a browser download. */
export function exportToCsv(rows: Record<string, unknown>[], columns: string[], filename: string): void {
  const header = columns.join(',')
  const body = rows
    .map(row => columns.map(col => `"${String(row[col] ?? '').replace(/"/g, '""')}"`).join(','))
    .join('\n')
  const blob = new Blob([header + '\n' + body], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
