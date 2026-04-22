import { useEffect, type ReactNode } from 'react'

type ConsoleShellProps = {
  activePath: string
  children: ReactNode
}

const navItems = [
  { href: '/console/integrations', label: 'Sources' },
  { href: '/console/trust', label: 'Trust' },
]

function isActiveFor(activePath: string, href: string): boolean {
  const cleanHref = href.split('#')[0]
  return activePath === cleanHref || activePath.startsWith(`${cleanHref}/`)
}

function connectorIdForPath(activePath: string): string | null {
  const segments = activePath.split('/').filter(Boolean)
  if (segments[0] !== 'console' || segments[1] !== 'integrations' || !segments[2]) {
    return null
  }
  return decodeURIComponent(segments[2])
}

function shouldIgnoreShortcutTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) {
    return false
  }

  return target.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName)
}

function ConsoleShell({ activePath, children }: ConsoleShellProps) {
  const connectorId = connectorIdForPath(activePath)
  const isConnectorDetail = connectorId !== null
  const shellClassName = [
    'console-shell',
    isConnectorDetail ? 'console-shell-source-detail' : '',
    connectorId ? `console-shell-${connectorId}` : '',
  ]
    .filter(Boolean)
    .join(' ')

  useEffect(() => {
    function handleKeydown(event: KeyboardEvent) {
      if (!(event.metaKey || event.ctrlKey) || event.key.toLowerCase() !== 'k' || shouldIgnoreShortcutTarget(event.target)) {
        return
      }

      event.preventDefault()

      if (window.location.pathname !== '/console/knowledge/ask') {
        window.location.assign('/console/knowledge/ask')
      }
    }

    window.addEventListener('keydown', handleKeydown)

    return () => {
      window.removeEventListener('keydown', handleKeydown)
    }
  }, [])

  return (
    <div className={shellClassName}>
      <header className={`shell-header${isConnectorDetail ? ' shell-header-compact' : ''}`}>
        <a className="shell-brand shell-brand-link" href="/console" aria-label="DreamFi home">
          <span className="brand-chip">DreamFi</span>
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
            aria-label="Ask from anywhere"
          >
            <span>Ask</span>
            <kbd className="shell-ask-shortcut" aria-hidden="true">⌘K</kbd>
          </a>
        </nav>
      </header>
      <main className="console-main">{children}</main>
    </div>
  )
}

export default ConsoleShell
