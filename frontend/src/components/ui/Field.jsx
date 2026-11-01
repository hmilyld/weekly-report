import { cloneElement, isValidElement, useId } from 'react'

/**
 * Label + control + hint/error, wired for accessibility.
 * The single child control receives id, aria-describedby and aria-invalid.
 */
export default function Field({ label, hint, error, optional, id, className = '', children }) {
  const autoId = useId()
  const fieldId = id || autoId
  const hintId = hint && !error ? `${fieldId}-hint` : undefined
  const errorId = error ? `${fieldId}-error` : undefined
  const describedBy = [hintId, errorId].filter(Boolean).join(' ') || undefined

  const control =
    isValidElement(children) && !children.props.id
      ? cloneElement(children, {
          id: fieldId,
          'aria-describedby': describedBy,
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
