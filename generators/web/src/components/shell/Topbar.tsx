import type { ReactNode } from 'react'

export type Crumb = {
  href?: string
  label: string
  strong?: boolean
}

export function Topbar({ actions, crumbs }: { actions?: ReactNode; crumbs: Crumb[] }) {
  return (
    <header className="topbar">
      <nav className="crumb" aria-label="Breadcrumb">
        {crumbs.map((crumb, index) => (
          <span className="row" key={`${crumb.label}-${index}`} style={{ gap: 8 }}>
            {index > 0 ? <span className="sep">/</span> : null}
            {crumb.strong ? (
              <b>{crumb.label}</b>
            ) : crumb.href ? (
              <a href={crumb.href}>{crumb.label}</a>
            ) : (
              <span>{crumb.label}</span>
            )}
          </span>
        ))}
      </nav>
      <div className="topbar-actions">{actions}</div>
    </header>
  )
}

export function AppFrame({
  children,
  sidebar,
  topbar,
}: {
  children: ReactNode
  sidebar: ReactNode
  topbar: ReactNode
}) {
  return (
    <div className="app-shell">
      {sidebar}
      <div className="main">
        {topbar}
        <div className="scroll">{children}</div>
      </div>
    </div>
  )
}
