import type { ReactNode } from 'react'

type ConsoleShellProps = {
  title: string
  subtitle: string
  activePath: string
  children: ReactNode
}

const navItems = [
  { href: '/console#sources', label: 'Sources' },
  { href: '/console/trust', label: 'Trust' },
]

function isActiveFor(activePath: string, href: string): boolean {
  const cleanHref = href.split('#')[0]
  if (cleanHref === '/console') {
    return activePath === '/console' || activePath.startsWith('/console/integrations')
  }
  return activePath === cleanHref || activePath.startsWith(`${cleanHref}/`)
}

function connectorIdForPath(activePath: string): string | null {
  const segments = activePath.split('/').filter(Boolean)
  if (segments[0] !== 'console' || segments[1] !== 'integrations' || !segments[2]) {
    return null
  }
  return decodeURIComponent(segments[2])
}

function ConsoleShell({ title, subtitle, activePath, children }: ConsoleShellProps) {
  const connectorId = connectorIdForPath(activePath)
  const isConnectorDetail = connectorId !== null
  const shellClassName = [
    'console-shell',
    isConnectorDetail ? 'console-shell-source-detail' : '',
    connectorId ? `console-shell-${connectorId}` : '',
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <div className={shellClassName}>
      <header className={`shell-header${isConnectorDetail ? ' shell-header-compact' : ''}`}>
        <a className="shell-brand shell-brand-link" href="/console" aria-label="DreamFi home">
          <span className="brand-chip">{isConnectorDetail ? 'DreamFi layer' : 'DreamFi'}</span>
          <div>
            <h1>{title}</h1>
            <p>{subtitle}</p>
          </div>
        </a>
        <nav className="shell-nav" aria-label="Primary">
          {navItems.map((item) => (
            <a
              key={item.href}
              className={isActiveFor(activePath, item.href) ? 'active' : ''}
              href={item.href}
            >
              {item.label}
            </a>
          ))}
          <a
            className={`shell-ask-button${activePath.startsWith('/console/knowledge/ask') ? ' active' : ''}`}
            href="/console/knowledge/ask"
          >
            Ask
          </a>
        </nav>
      </header>
      <main className="console-main">{children}</main>
    </div>
  )
}

export default ConsoleShell
