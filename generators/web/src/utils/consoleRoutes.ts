function normalizeGeneratorKey(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/[_-]+/g, ' ')
    .replace(/[^a-z0-9 ]+/g, ' ')
    .replace(/\s+/g, ' ')
}

const GENERATOR_ROUTE_ALIASES: Record<string, string> = {
  'weekly brief': 'weekly-brief',
  'weekly pm brief': 'weekly-brief',
  'technical prd': 'technical-prd',
  'business prd': 'business-prd',
  'risk brd': 'risk-brd',
}

const GENERATOR_TITLES: Record<string, string> = {
  'weekly-brief': 'Weekly PM Brief',
  'technical-prd': 'Technical PRD',
  'business-prd': 'Business PRD',
  'risk-brd': 'Risk BRD',
}

function prettifyGeneratorSlug(value: string): string {
  return value
    .split('-')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
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

export function generatorTitleFromSlug(value: string | null | undefined): string {
  const slug = generatorSlugFromIdentifier(value)
  return GENERATOR_TITLES[slug] ?? prettifyGeneratorSlug(slug)
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
    path === '/console/inbox' ||
    path === '/console/review' ||
    path === '/console/trust' ||
    path === '/console/methodology' ||
    path === '/console/knowledge/ask' ||
    path === '/console/topics' ||
    path.startsWith('/console/topics/') ||
    path === '/console/integrations' ||
    path.startsWith('/console/integrations/') ||
    path.startsWith('/console/generate/')
  )
}
