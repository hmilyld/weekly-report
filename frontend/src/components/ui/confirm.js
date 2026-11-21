import { createContext, useContext } from 'react'

// Kept apart from ConfirmProvider.jsx so that file only exports a component
// (React Fast Refresh rewires modules that mix components and plain values).
export const ConfirmContext = createContext(null)

export function useConfirm() {
  const ctx = useContext(ConfirmContext)
  if (!ctx) throw new Error('useConfirm must be used within ConfirmProvider')
  return ctx
}
