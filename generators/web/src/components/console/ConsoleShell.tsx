import type { ReactNode } from 'react'
import { modules } from '../../config/modules'

type ConsoleShellProps = {
  title: string
  subtitle: string
  activePath: string
  children: ReactNode
}

const moduleNavItems = modules.map((module) => ({
  href: module.route,
  label: module.title,
}))

const opsNavItems = [
  { href: '/console', label: 'Home' },
  { href: '/console/artifacts', label: 'Artifacts' },
  { href: '/console/review', label: 'Review' },
  { href: '/console/trust', label: 'Trust' },
]

function isActiveFor(activePath: string, href: string): boolean {
  if (href === '/console') {
    return activePath === '/console'
  }
  return activePath === href || activePath.startsWith(`${href}/`)
}

function ConsoleShell({ title, subtitle, activePath, children }: ConsoleShellProps) {
  return (
    <div className="console-shell">
      <header className="shell-header">
        <div className="shell-brand">
          <span className="brand-chip">DreamFi</span>
          <div>
            <h1>{title}</h1>
            <p>{subtitle}</p>
          </div>
        </div>
        <div className="shell-nav-groups">
          <nav className="shell-nav shell-nav-modules" aria-label="Modules">
            <span className="shell-nav-label">Modules</span>
            {moduleNavItems.map((item) => (
              <a
                key={item.href}
                className={isActiveFor(activePath, item.href) ? 'active' : ''}
                href={item.href}
              >
                {item.label}
              </a>
            ))}
          </nav>
          <nav className="shell-nav shell-nav-ops" aria-label="Operations">
            <span className="shell-nav-label">Operations</span>
            {opsNavItems.map((item) => (
              <a
                key={item.href}
                className={isActiveFor(activePath, item.href) ? 'active' : ''}
                href={item.href}
              >
                {item.label}
              </a>
            ))}
          </nav>
        </div>
      </header>
      <main className="console-main">{children}</main>
    </div>
  )
}

export default ConsoleShell
