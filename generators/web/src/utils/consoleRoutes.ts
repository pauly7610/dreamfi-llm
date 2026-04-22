function normalizeGeneratorKey(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/[_-]+/g, ' ')
    .replace(/[^a-z0-9 ]+/g, ' ')
    .replace(/\s+/g, ' ')
}

export function currentConsoleLocation(): { path: string; search: string } {
  if (typeof window === 'undefined') {
    return { path: '/console', search: '' }
  }

  const path = window.location.pathname.replace(/\/$/, '') || '/console'
  return { path, search: window.location.search }
}

const GENERATOR_ROUTE_ALIASES: Record<string, string> = {
  'weekly brief': 'weekly-brief',
  'weekly pm brief': 'weekly-brief',
  'technical prd': 'technical-prd',
  'business prd': 'business-prd',
  'risk brd': 'risk-brd',
}

export function generatorSlugFromIdentifier(value: string | null | undefined): string {
  if (!value) {
    return 'artifact'
  }

  const normalizedKey = normalizeGeneratorKey(value)
  const aliased = GENERATOR_ROUTE_ALIASES[normalizedKey]

  if (aliased) {
    return aliased
  }

  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
}

type GeneratorContext = {
  topicId?: string | null
  sourceId?: string | null
  query?: string | null
}

export function recommendedGeneratorSlug(context: GeneratorContext): string {
  const query = normalizeGeneratorKey(context.query ?? '')
  const topicId = context.topicId ?? null
  const sourceId = context.sourceId ?? null

  if (
    query.includes('risk') ||
    query.includes('compliance') ||
    query.includes('sponsor') ||
    query.includes('manual review') ||
    query.includes('fraud') ||
    topicId === 'kyc-conversion' ||
    sourceId === 'socure' ||
    sourceId === 'sardine'
  ) {
    return 'risk-brd'
  }

  if (
    query.includes('campaign') ||
    query.includes('lifecycle') ||
    query.includes('message') ||
    query.includes('marketing') ||
    topicId === 'lifecycle-messaging' ||
    sourceId === 'klaviyo' ||
    sourceId === 'ga'
  ) {
    return 'business-prd'
  }

  if (query.includes('brief') || query.includes('weekly') || query.includes('summary')) {
    return 'weekly-brief'
  }

  if (topicId === 'onboarding' || topicId === 'funding' || sourceId === 'jira' || sourceId === 'netxd') {
    return 'technical-prd'
  }

  return 'technical-prd'
}

export function generatorHrefForContext(context: GeneratorContext): string {
  return `/console/generate/${recommendedGeneratorSlug(context)}`
}

export function buildAskHref(topicId: string, question: string): string {
  return `/console/knowledge/ask?topic=${topicId}&q=${encodeURIComponent(question)}`
}

export function navigateConsole(href: string, replace = false) {
  if (typeof window === 'undefined') {
    return
  }

  if (replace) {
    window.history.replaceState(null, '', href)
  } else {
    window.history.pushState(null, '', href)
  }

  window.dispatchEvent(new Event('console:navigate'))
}

export function isKnownConsoleHref(href: string): boolean {
  if (!href) {
    return false
  }

  if (href.startsWith('#')) {
    return true
  }

  const [path] = href.split(/[?#]/)

  if (path === '/console') {
    return true
  }

  return (
    path === '/console/artifacts' ||
    path === '/console/review' ||
    path === '/console/trust' ||
    path === '/console/knowledge/ask' ||
    path === '/console/topics' ||
    path.startsWith('/console/topics/') ||
    path === '/console/integrations' ||
    path.startsWith('/console/integrations/') ||
    path === '/console/generate' ||
    path.startsWith('/console/generate/')
  )
}
