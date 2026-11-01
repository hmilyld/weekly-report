/**
 * Empty states are an invitation, not a mood: one line saying what is
 * missing, one line saying what to do about it, and the action itself.
 */
export default function EmptyState({ icon: Icon, title, description, actions, className = '' }) {
  return (
    <div className={`empty ${className}`.trim()}>
      {Icon && (
        <span className="empty-icon">
          <Icon size={20} aria-hidden="true" />
        </span>
      )}
      {title && <p className="empty-title">{title}</p>}
      {description && <p>{description}</p>}
      {actions && <div className="empty-actions">{actions}</div>}
    </div>
  )
}
