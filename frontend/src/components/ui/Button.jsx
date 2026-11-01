import { Loader2 } from 'lucide-react'

/**
 * One button for the whole product.
 * variant: primary | accent | outline | ghost | danger
 * size:    md (default) | sm | lg
 */
export default function Button({
  variant = 'outline',
  size,
  icon: Icon,
  iconSize,
  loading = false,
  block = false,
  iconOnly = false,
  className = '',
  children,
  type = 'button',
  ...rest
}) {
  const classes = [
    'btn',
    `btn-${variant}`,
    size && `btn-${size}`,
    block && 'btn-block',
    iconOnly && 'btn-icon',
    loading && 'is-loading',
    className,
  ]
    .filter(Boolean)
    .join(' ')

  const glyph = iconSize || (size === 'sm' ? 14 : 16)

  return (
    <button
      type={type}
      className={classes}
      disabled={rest.disabled || loading}
      aria-busy={loading || undefined}
      {...rest}
    >
      {loading ? (
        <Loader2 size={glyph} className="btn-spinner" aria-hidden="true" />
      ) : (
        Icon && <Icon size={glyph} aria-hidden="true" />
      )}
      {children != null && <span className="btn-label">{children}</span>}
    </button>
  )
}
