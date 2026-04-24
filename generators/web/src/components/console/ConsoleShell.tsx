import { useEffect, type FormEvent, type MouseEvent, type ReactNode } from 'react'

import {
  currentConsoleLocation,
  isInternalConsoleHref,
  navigateConsole,
} from '../../utils/consoleNavigation'

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

function shouldBrowserHandleLink(event: MouseEvent<Element>, anchor: HTMLAnchorElement): boolean {
  if (event.defaultPrevented || event.button !== 0) {
    return true
  }

  if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
    return true
  }

  if (anchor.target && anchor.target !== '_self') {
    return true
  }

  if (anchor.hasAttribute('download')) {
    return true
  }

  return false
}

function hrefForConsoleForm(form: HTMLFormElement): string | null {
  const method = (form.getAttribute('method') || form.method || 'get').toLowerCase()
  if (method !== 'get') {
    return null
  }

  const actionAttr = form.getAttribute('action') || currentConsoleLocation().href
  if (!isInternalConsoleHref(actionAttr)) {
    return null
  }

  const action = new URL(actionAttr, window.location.origin)
  const params = new URLSearchParams(action.search)
  const clearedKeys = new Set<string>()
  const formData = new FormData(form)

  formData.forEach((value, key) => {
    if (typeof value !== 'string') {
      return
    }

    if (!clearedKeys.has(key)) {
      params.delete(key)
      clearedKeys.add(key)
    }

    params.append(key, value)
  })

  action.search = params.toString() ? `?${params.toString()}` : ''
  return `${action.pathname}${action.search}${action.hash}`
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
        navigateConsole('/console/knowledge/ask')
      }
    }

    window.addEventListener('keydown', handleKeydown)

    return () => {
      window.removeEventListener('keydown', handleKeydown)
    }
  }, [])

  function handleConsoleClick(event: MouseEvent<HTMLDivElement>) {
    const target = event.target
    if (!(target instanceof HTMLElement)) {
      return
    }

    const anchor = target.closest('a[href]')
    if (!(anchor instanceof HTMLAnchorElement) || !event.currentTarget.contains(anchor)) {
      return
    }

    const href = anchor.getAttribute('href')
    if (!href || !isInternalConsoleHref(href) || shouldBrowserHandleLink(event, anchor)) {
      return
    }

    event.preventDefault()
    navigateConsole(href)
  }

  function handleConsoleSubmit(event: FormEvent<HTMLDivElement>) {
    const target = event.target
    if (!(target instanceof HTMLFormElement) || !event.currentTarget.contains(target)) {
      return
    }

    const href = hrefForConsoleForm(target)
    if (!href) {
      return
    }

    event.preventDefault()
    navigateConsole(href)
  }

  return (
    <div className={shellClassName} onClickCapture={handleConsoleClick} onSubmitCapture={handleConsoleSubmit}>
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
