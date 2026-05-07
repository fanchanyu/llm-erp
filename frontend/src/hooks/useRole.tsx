import { createContext, useContext, useState, ReactNode } from 'react'
import type { RoleId, RoleConfig } from '../roles'
import { ROLES, ROLE_LIST } from '../roles'

interface RoleContextValue {
  role: RoleId
  setRole: (r: RoleId) => void
  roleConfig: RoleConfig
  roleList: typeof ROLE_LIST
}

const RoleContext = createContext<RoleContextValue | null>(null)

export function RoleProvider({ children }: { children: ReactNode }) {
  const [role, setRole] = useState<RoleId>('director')
  const roleConfig = ROLES[role]

  return (
    <RoleContext.Provider value={{ role, setRole, roleConfig, roleList: ROLE_LIST }}>
      {children}
    </RoleContext.Provider>
  )
}

export function useRole() {
  const ctx = useContext(RoleContext)
  if (!ctx) throw new Error('useRole must be inside RoleProvider')
  return ctx
}
