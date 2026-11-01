/**
 * The page frame every screen shares: title, one line of orientation,
 * and the page's own actions on the right.
 */
export default function PageHeader({ title, subtitle, actions, children }) {
  return (
    <header className="page-head">
      <div className="page-head-text">
        <h1 className="page-title">{title}</h1>
        {subtitle && <p className="page-sub">{subtitle}</p>}
        {children}
      </div>
      {actions && <div className="page-actions">{actions}</div>}
    </header>
  )
}
