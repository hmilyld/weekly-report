import { useCallback, useEffect, useId, useRef } from 'react'
import { createPortal } from 'react-dom'
import { X } from 'lucide-react'

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'

/**
 * One modal for the product: focus is trapped, Esc closes, the page
 * behind stops scrolling, and focus returns to the trigger on close.
 */
export default function Modal({
  open = true,
  title,
  description,
  size,
  dismissible = true,
  onClose,
  footer,
  children,
}) {
  const titleId = useId()
  const dialogRef = useRef(null)
  const restoreRef = useRef(null)

  const requestClose = useCallback(() => {
    if (dismissible) onClose?.()
  }, [dismissible, onClose])

  useEffect(() => {
    if (!open) return undefined

    restoreRef.current = document.activeElement
    const { overflow } = document.body.style
    document.body.style.overflow = 'hidden'

    const node = dialogRef.current
    const first = node?.querySelector(FOCUSABLE)
    if (first) first.focus()
    else node?.focus()

    const onKeyDown = (event) => {
      // Two dialogs can be open at once (a confirm over a form). Only the
      // one that holds focus reacts to Esc and Tab.
      if (!node || !node.contains(document.activeElement)) return
      if (event.key === 'Escape') {
        event.stopPropagation()
        requestClose()
        return
      }
      if (event.key !== 'Tab' || !node) return
      const items = Array.from(node.querySelectorAll(FOCUSABLE)).filter(
        (el) => el.offsetParent !== null,
      )
      if (items.length === 0) return
      const firstItem = items[0]
      const lastItem = items[items.length - 1]
      if (event.shiftKey && document.activeElement === firstItem) {
        event.preventDefault()
        lastItem.focus()
      } else if (!event.shiftKey && document.activeElement === lastItem) {
        event.preventDefault()
        firstItem.focus()
      }
    }

    document.addEventListener('keydown', onKeyDown, true)
    return () => {
      document.removeEventListener('keydown', onKeyDown, true)
      document.body.style.overflow = overflow
      if (restoreRef.current instanceof HTMLElement) restoreRef.current.focus()
    }
  }, [open, requestClose])

  if (!open) return null

  return createPortal(
    <div
      className="modal-overlay"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) requestClose()
      }}
    >
      <div
        ref={dialogRef}
        className={`modal ${size === 'sm' ? 'modal-sm' : ''}`.trim()}
        role="dialog"
        aria-modal="true"
        aria-labelledby={title ? titleId : undefined}
        tabIndex={-1}
      >
        {(title || dismissible) && (
          <div className="modal-header">
            <div className="modal-title">
              {title && <h3 id={titleId}>{title}</h3>}
              {description && <p>{description}</p>}
            </div>
            {dismissible && (
              <button className="icon-btn" onClick={requestClose} aria-label="关闭">
                <X size={18} />
              </button>
            )}
          </div>
        )}
        <div className="modal-body">{children}</div>
        {footer && <div className="modal-footer">{footer}</div>}
      </div>
    </div>,
    document.body,
  )
}
