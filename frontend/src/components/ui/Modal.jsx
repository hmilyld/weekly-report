import { useEffect, useId, useRef } from 'react'
import { createPortal } from 'react-dom'
import { X } from 'lucide-react'
import { promoteToastLayer } from './toastLayer'

/* Open dialogs in opening order. The browser fires `cancel` on every open
   modal, not only the topmost, so this stack decides which one may act on a
   close request — otherwise one Escape closes a confirm and the form under it. */
const dialogStack = []

/**
 * One modal for the product, built on the native <dialog> element.
 *
 * The browser supplies what a hand-rolled overlay has to rebuild: the top
 * layer, an inert page behind it, focus containment and its return to the
 * trigger, Esc and the mobile back gesture, and light dismissal. The page
 * underneath is held still with overscroll-behavior rather than by locking
 * body scroll, which would remove the scrollbar and shift the layout.
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
  const descriptionId = useId()
  const dialogRef = useRef(null)
  const onCloseRef = useRef(onClose)

  useEffect(() => {
    onCloseRef.current = onClose
  }, [onClose])

  // Open and close the native dialog, and report every close back to React:
  // Esc, the back gesture and a backdrop press all arrive as `close`.
  useEffect(() => {
    const node = dialogRef.current
    if (!node) return undefined

    const handleClose = () => onCloseRef.current?.()
    node.addEventListener('close', handleClose)

    // The browser restores focus to whatever was focused before showModal(),
    // but only while the dialog is still connected. React removes the node as
    // soon as the parent clears its state, so remember the target and put
    // focus back on it ourselves.
    const restoreRef = { current: document.activeElement }
    if (open && !node.open) {
      node.showModal()
      dialogStack.push(node)
    }
    if (!open && node.open) node.close()
    // A dialog enters the top layer; toasts have to be moved above it again.
    if (node.open) promoteToastLayer()

    return () => {
      node.removeEventListener('close', handleClose)
      const index = dialogStack.indexOf(node)
      if (index !== -1) dialogStack.splice(index, 1)
      if (node.open) node.close()
      const target = restoreRef.current
      if (target instanceof HTMLElement && target.isConnected && target !== document.body) {
        target.focus()
      }
    }
  }, [open])

  useEffect(() => {
    const node = dialogRef.current
    if (!node) return undefined

    // A non-dismissible dialog still has to survive Esc and the back gesture.
    // The browser fires `cancel` on every open modal, not just the topmost, so
    // only the last one in document order may act on it; otherwise one Escape
    // would close a confirm and the form underneath it.
    const handleCancel = (event) => {
      const isTopmost = dialogStack[dialogStack.length - 1] === node
      if (!dismissible || !isTopmost) event.preventDefault()
      // Otherwise the browser closes it and the `close` listener reports in.
    }
    node.addEventListener('cancel', handleCancel)

    // Safari does not implement closedby: dismiss on a press and release that
    // both land outside the dialog, so a text selection ending on the backdrop
    // does not close it.
    const supportsClosedBy = 'closedBy' in HTMLDialogElement.prototype
    let pressedOutside = false
    const isOutside = (event) => {
      const rect = node.getBoundingClientRect()
      return (
        event.clientX < rect.left ||
        event.clientX > rect.right ||
        event.clientY < rect.top ||
        event.clientY > rect.bottom
      )
    }
    const handlePointerDown = (event) => {
      pressedOutside = dismissible && isOutside(event)
    }
    const handlePointerUp = (event) => {
      if (pressedOutside && isOutside(event)) node.close()
      pressedOutside = false
    }
    if (!supportsClosedBy) {
      node.addEventListener('pointerdown', handlePointerDown)
      node.addEventListener('pointerup', handlePointerUp)
    }

    return () => {
      node.removeEventListener('cancel', handleCancel)
      if (!supportsClosedBy) {
        node.removeEventListener('pointerdown', handlePointerDown)
        node.removeEventListener('pointerup', handlePointerUp)
      }
    }
  }, [dismissible])

  // The browser focuses the first focusable control on open; a field that asks
  // for the cursor takes precedence, as long as it is actually usable.
  useEffect(() => {
    const node = dialogRef.current
    if (!node || !open) return
    const preferred = node.querySelector('[data-autofocus]')
    const usable = preferred && preferred.offsetParent !== null && !preferred.matches(':disabled')
    if (usable) preferred.focus()
  }, [open])

  if (!open) return null

  return createPortal(
    <dialog
      ref={dialogRef}
      className={`modal ${size === 'sm' ? 'modal-sm' : ''}`.trim()}
      aria-labelledby={title ? titleId : undefined}
      aria-describedby={description ? descriptionId : undefined}
      /* React 18 does not know `closedby` yet; spread it as a DOM attribute. */
      {...{ closedby: dismissible ? 'any' : 'none' }}
    >
      {(title || dismissible) && (
        <div className="modal-header">
          <div className="modal-title">
            {title && <h2 id={titleId}>{title}</h2>}
            {description && <p id={descriptionId}>{description}</p>}
          </div>
          {dismissible && (
            <button
              className="icon-btn"
              onClick={() => dialogRef.current?.close()}
              aria-label="关闭"
            >
              <X size={18} />
            </button>
          )}
        </div>
      )}
      <div className="modal-body">{children}</div>
      {footer && <div className="modal-footer">{footer}</div>}
    </dialog>,
    document.body,
  )
}
