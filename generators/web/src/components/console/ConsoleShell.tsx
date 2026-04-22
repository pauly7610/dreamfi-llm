import { useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react'

import { navigateConsole } from '../../utils/consoleRoutes'

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
  const [isAskOverlayOpen, setIsAskOverlayOpen] = useState(false)
  const [commandQuestion, setCommandQuestion] = useState('')
  const commandInputRef = useRef<HTMLTextAreaElement | null>(null)
  const shellClassName = [
    'console-shell',
    isConnectorDetail ? 'console-shell-source-detail' : '',
    connectorId ? `console-shell-${connectorId}` : '',
  ]
    .filter(Boolean)
    .join(' ')

  useEffect(() => {
    function handleKeydown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setIsAskOverlayOpen(false)
        return
      }

      if (!(event.metaKey || event.ctrlKey) || event.key.toLowerCase() !== 'k' || shouldIgnoreShortcutTarget(event.target)) {
        return
      }

      event.preventDefault()
      setCommandQuestion('')
      setIsAskOverlayOpen(true)
    }

    window.addEventListener('keydown', handleKeydown)

    return () => {
      window.removeEventListener('keydown', handleKeydown)
    }
  }, [])

  useEffect(() => {
    if (!isAskOverlayOpen) {
      return
    }

    commandInputRef.current?.focus()
  }, [isAskOverlayOpen])

  function submitCommandQuestion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const href = `/console/knowledge/ask${commandQuestion.trim() ? `?q=${encodeURIComponent(commandQuestion.trim())}` : ''}`
    setIsAskOverlayOpen(false)
    navigateConsole(href)
  }

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
      {isAskOverlayOpen ? (
        <div
          className="ask-command-overlay"
          role="dialog"
          aria-modal="true"
          aria-label="Ask DreamFi from anywhere"
          onClick={() => setIsAskOverlayOpen(false)}
        >
          <form className="ask-command-dialog panel" onSubmit={submitCommandQuestion} onClick={(event) => event.stopPropagation()}>
            <div className="ask-command-header">
              <span className="eyebrow">Ask from anywhere</span>
              <button type="button" className="button ghost" onClick={() => setIsAskOverlayOpen(false)}>Close</button>
            </div>
            <label htmlFor="shell-ask-command">Question</label>
            <textarea
              ref={commandInputRef}
              id="shell-ask-command"
              value={commandQuestion}
              onChange={(event) => setCommandQuestion(event.target.value)}
              placeholder="What changed since the last readiness review?"
            />
            <div className="ask-box-actions">
              <button type="submit" className="button primary">Open Ask</button>
              <small>Ask stays in product flow now, then opens the full answer view only when you submit.</small>
            </div>
          </form>
        </div>
      ) : null}
      <main className="console-main">{children}</main>
    </div>
  )
}

export default ConsoleShell
