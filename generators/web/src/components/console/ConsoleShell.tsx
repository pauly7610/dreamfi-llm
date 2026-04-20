import type { ReactNode } from 'react'

type ConsoleShellProps = {
  title: string
  subtitle: string
  activePath: string
  children: ReactNode
}

const navItems = [
  { href: '/console', label: 'Console' },
  { href: '/console/artifacts', label: 'Artifacts' },
  { href: '/console/review', label: 'Review' },
  { href: '/console/trust', label: 'Trust' },
  { href: '/console/generate/weekly-brief', label: 'Generate' }
]

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
        <nav className="shell-nav">
          {navItems.map((item) => {
            const isActive = activePath === item.href || (item.href !== '/console' && activePath.startsWith(item.href))
            return (
              <a key={item.href} className={isActive ? 'active' : ''} href={item.href}>
                {item.label}
              </a>
            )
          })}
        </nav>
      </header>
      <main className="console-main">{children}</main>
    </div>
  )
}

export default ConsoleShell
