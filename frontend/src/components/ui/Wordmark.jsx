/**
 * The product mark: the same 2×2 cell grid as the app icon, with the last
 * cell in signal blue, plus the diagonal slash. Replaces the emoji that
 * used to stand in for a logo.
 */
export default function Wordmark({ compact = false, className = '' }) {
  return (
    <span className={`wordmark ${className}`.trim()}>
      <span className="wordmark-mark" aria-hidden="true">
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
