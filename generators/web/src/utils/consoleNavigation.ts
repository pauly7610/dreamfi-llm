export const CONSOLE_NAVIGATE_EVENT = 'console:navigate'

export type ConsoleLocation = {
  path: string
  search: string
  hash: string
  href: string
}

function normalizePathname(pathname: string): string {
  const trimmed = pathname.replace(/\/$/, '')
  return trimmed || '/console'
}

export function currentConsoleLocation(): ConsoleLocation {
  if (typeof window === 'undefined') {
    return {
      path: '/console',
      search: '',
      hash: '',
      href: '/console',
    }
  }

  const path = normalizePathname(window.location.pathname)
  const search = window.location.search
  const hash = window.location.hash

  return {
    path,
    search,
    hash,
    href: `${path}${search}${hash}`,
  }
}

export function isInternalConsoleHref(href: string): boolean {
  if (!href) {
    return false
  }

  if (href.startsWith('#')) {
    return true
  }

  try {
    const url = new URL(href, window.location.origin)
    return url.origin === window.location.origin && url.pathname.startsWith('/console')
  } catch {
    return false
  }
}

export function hrefForConsoleNavigation(href: string): string {
  if (href.startsWith('#')) {
    const current = currentConsoleLocation()
    return `${current.path}${current.search}${href}`
  }

  const url = new URL(href, window.location.origin)
  const path = normalizePathname(url.pathname)
  return `${path}${url.search}${url.hash}`
}

function scrollToConsoleTarget(current: ConsoleLocation, next: ConsoleLocation) {
  if (next.hash) {
    const targetId = decodeURIComponent(next.hash.slice(1))
    const target = document.getElementById(targetId)
    if (target && typeof target.scrollIntoView === 'function') {
      target.scrollIntoView({ block: 'start' })
      return
    }
  }

  if (next.path !== current.path || next.search !== current.search) {
    try {
      window.scrollTo({ top: 0, left: 0 })
    } catch {
      // jsdom does not implement scrollTo; browsers do.
    }
  }
}

export function navigateConsole(href: string, options: { replace?: boolean } = {}): string {
  const current = currentConsoleLocation()
  const nextHref = hrefForConsoleNavigation(href)

  if (options.replace) {
    window.history.replaceState(null, '', nextHref)
  } else if (nextHref !== current.href) {
    window.history.pushState(null, '', nextHref)
  }

  window.dispatchEvent(new CustomEvent(CONSOLE_NAVIGATE_EVENT, { detail: currentConsoleLocation() }))

  const scheduleScroll = typeof window.requestAnimationFrame === 'function'
    ? window.requestAnimationFrame.bind(window)
    : (callback: FrameRequestCallback) => window.setTimeout(callback, 0)

  scheduleScroll(() => {
    scrollToConsoleTarget(current, currentConsoleLocation())
    return 0
  })

  return nextHref
}
