/**
 * The toast stack lives outside every screen, so it must be able to paint above
 * a modal <dialog>. A dialog sits in the browser's top layer, where no z-index
 * reaches; the toast container therefore becomes a manual popover. Top-layer
 * order follows insertion, so the container is re-promoted whenever a toast
 * arrives, which puts it back above any dialog that opened after it.
 */
let layer = null
let observer = null

export function registerToastLayer(element) {
  if (!element || !('popover' in HTMLElement.prototype)) return
  layer = element
  element.setAttribute('popover', 'manual')
  promote()

  if (observer) observer.disconnect()
  observer = new MutationObserver(promote)
  observer.observe(element, { childList: true })
}

function promote() {
  if (!layer || !layer.isConnected) return
  if (!('popover' in HTMLElement.prototype)) return
  try {
    // Re-showing moves the container to the end of the top layer.
    if (layer.matches(':popover-open')) layer.hidePopover()
    layer.showPopover()
  } catch {
    /* A popover that cannot open is not worth breaking a toast over. */
  }
}

/** Call after a dialog opens: top-layer order follows insertion, not z-index. */
export function promoteToastLayer() {
  promote()
}
