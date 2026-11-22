import { cloneElement, isValidElement, useId } from 'react'

/**
 * Label + control + hint/error, wired for accessibility.
 * The single child control receives id, aria-describedby and aria-invalid.
 */
export default function Field({ label, hint, error, optional, id, className = '', children }) {
  const autoId = useId()
  // A control that brings its own id keeps it, and the label must point at that
  // id instead of an unrelated generated one.
  const childId = isValidElement(children) ? children.props.id : undefined
  const fieldId = id || childId || autoId
  const hintId = hint && !error ? `${fieldId}-hint` : undefined
  const errorId = error ? `${fieldId}-error` : undefined
  const describedBy = [hintId, errorId].filter(Boolean).join(' ') || undefined

  const control = isValidElement(children)
    ? cloneElement(children, {
        id: childId || fieldId,
        'aria-describedby': describedBy ?? children.props['aria-describedby'],
        'aria-invalid': error ? true : undefined,
      })
    : children

  return (
    <div className={`field ${className}`.trim()}>
      {label && (
        <label className="field-label" htmlFor={fieldId}>
          <span>{label}</span>
          {optional && <span className="optional">可选</span>}
        </label>
      )}
      {control}
      {hint && !error && (
        <p className="field-hint" id={hintId}>
          {hint}
        </p>
      )}
      {error && (
        <p className="field-error" id={errorId} role="alert">
          {error}
        </p>
      )}
    </div>
  )
}
