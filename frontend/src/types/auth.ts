export interface User {
  email: string
  name: string
  role: string | null
}

export type UserRole = 'staff' | 'manager' | 'admin' | null
