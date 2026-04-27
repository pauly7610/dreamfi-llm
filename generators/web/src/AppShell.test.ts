import { describe, expect, it } from 'vitest'

import { normalizeLegacyPath } from './AppShell'

describe('normalizeLegacyPath', () => {
  it('redirects removed module routes into the current IA', () => {
    expect(normalizeLegacyPath('/console/knowledge')).toBe('/console/knowledge/ask')
    expect(normalizeLegacyPath('/console/planning')).toBe('/console/topics')
    expect(normalizeLegacyPath('/console/metrics')).toBe('/console/integrations/metabase')
    expect(normalizeLegacyPath('/console/ui-support')).toBe('/console/topics/onboarding')
    expect(normalizeLegacyPath('/console/generators')).toBe('/console/generate/weekly-brief')
    expect(normalizeLegacyPath('/console/generate/technical_prd')).toBe('/console/generate/technical-prd')
    expect(normalizeLegacyPath('/console/generate/weekly-pm-brief')).toBe('/console/generate/weekly-brief')
    expect(normalizeLegacyPath('/console/inbox')).toBe('/console/review')
  })

  it('leaves current routes alone', () => {
    expect(normalizeLegacyPath('/console')).toBe('/console')
    expect(normalizeLegacyPath('/console/methodology')).toBe('/console/methodology')
    expect(normalizeLegacyPath('/console/knowledge/ask')).toBe('/console/knowledge/ask')
    expect(normalizeLegacyPath('/console/integrations/posthog')).toBe('/console/integrations/posthog')
  })
})
