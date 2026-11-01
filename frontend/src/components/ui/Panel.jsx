/**
 * The only container shape in the product.
 * A panel is a titled block of content with an optional footer of actions.
 */
export function Panel({ children, className = '', as: Tag = 'section', ...rest }) {
  return (
    <Tag className={`panel ${className}`.trim()} {...rest}>
      {children}
    </Tag>
  )
}

export function PanelHeader({ title, icon: Icon, actions, meta, children }) {
  return (
    <div className="panel-header">
      {title && (
        <h3>
          {Icon && <Icon size={16} aria-hidden="true" />}
          {title}
          {meta}
        </h3>
      )}
      {children}
      {actions && <div className="row">{actions}</div>}
    </div>
  )
}

export function PanelBody({ children, className = '', ...rest }) {
  return (
    <div className={`panel-body ${className}`.trim()} {...rest}>
      {children}
    </div>
  )
}

export function PanelFooter({ children, className = '', ...rest }) {
  return (
    <div className={`panel-footer ${className}`.trim()} {...rest}>
      {children}
    </div>
  )
}
