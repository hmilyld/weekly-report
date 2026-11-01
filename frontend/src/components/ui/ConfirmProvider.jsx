import { createContext, useCallback, useContext, useMemo, useRef, useState } from 'react'
import Modal from './Modal'
import Button from './Button'

const ConfirmContext = createContext(null)

/**
 * Replaces window.confirm across the product: same call shape, but the
 * dialog is ours — named action, named consequence, danger tone on request.
 *
 *   const confirm = useConfirm()
 *   if (!(await confirm({ title: '删除这条日报？', confirmLabel: '删除', tone: 'danger' }))) return
 */
export function ConfirmProvider({ children }) {
  const [request, setRequest] = useState(null)
  const resolverRef = useRef(null)

  const confirm = useCallback((options) => {
    const normalized = typeof options === 'string' ? { title: options } : (options ?? {})
    setRequest(normalized)
    return new Promise((resolve) => {
      resolverRef.current = resolve
    })
  }, [])

  const settle = useCallback((value) => {
    resolverRef.current?.(value)
    resolverRef.current = null
    setRequest(null)
  }, [])

  const value = useMemo(() => confirm, [confirm])

  return (
    <ConfirmContext.Provider value={value}>
      {children}
      {request && (
        <Modal
          size="sm"
          title={request.title || '确认操作'}
          description={request.description}
          onClose={() => settle(false)}
          footer={
            <>
              <Button variant="outline" onClick={() => settle(false)}>
                {request.cancelLabel || '取消'}
              </Button>
              <Button
                variant={request.tone === 'danger' ? 'danger' : 'primary'}
                className={request.tone === 'danger' ? 'btn-danger-solid' : ''}
                onClick={() => settle(true)}
              >
                {request.confirmLabel || '确定'}
              </Button>
            </>
          }
        >
          {request.body && <p className="section-note">{request.body}</p>}
        </Modal>
      )}
    </ConfirmContext.Provider>
  )
}

export function useConfirm() {
  const ctx = useContext(ConfirmContext)
  if (!ctx) throw new Error('useConfirm must be used within ConfirmProvider')
  return ctx
}
