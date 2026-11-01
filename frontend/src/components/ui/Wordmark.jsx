/**
 * The product mark: a drawn 3×2 grid (one cell in signal blue) and a
 * slash. Replaces the emoji that used to stand in for a logo.
 */
export default function Wordmark({ compact = false, className = '' }) {
  return (
    <span className={`wordmark ${className}`.trim()}>
      <span className="wordmark-mark" aria-hidden="true">
        <i />
        <i />
        <i />
        <i />
        <i />
        <i />
      </span>
      {compact ? '日周报' : '日周报管理系统'}
      <span className="wordmark-slash" aria-hidden="true" />
    </span>
  )
}
