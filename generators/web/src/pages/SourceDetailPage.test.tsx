// @vitest-environment jsdom
import { cleanup, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { consoleDevelopmentSlice } from '../content/consoleDevelopmentSlice'
import { renderWithConsoleWorkspace } from '../test/renderWithConsoleWorkspace'
import SourceDetailPage from './SourceDetailPage'

afterEach(() => {
  cleanup()
  window.history.replaceState(null, '', '/')
})

describe('SourceDetailPage', () => {
  it('turns the integrations route into a connector directory', () => {
    renderWithConsoleWorkspace(<SourceDetailPage data={consoleDevelopmentSlice} sourceId={null} />, {
      path: '/console/integrations',
    })

    expect(screen.getByRole('heading', { name: /Open the connector workspace you need\./i })).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Metabase' }).getAttribute('href')).toBe('/console/integrations/metabase')
    expect(screen.getByRole('link', { name: 'PostHog' }).getAttribute('href')).toBe('/console/integrations/posthog')
    expect(screen.getByRole('link', { name: 'Klaviyo' }).getAttribute('href')).toBe('/console/integrations/klaviyo')
  })

  it('renders a grounded Metabase workspace with ask and generate paths', () => {
    renderWithConsoleWorkspace(<SourceDetailPage data={consoleDevelopmentSlice} sourceId="metabase" />, {
      path: '/console/integrations/metabase?topic=kyc-conversion',
    })

    expect(screen.getByText('Metabase workspace')).toBeTruthy()
    expect(screen.getByText('Ask with this source')).toBeTruthy()
    expect(screen.getByText(/Inspect next/i)).toBeTruthy()
    expect(screen.getByText(/Related workflows/i)).toBeTruthy()
    expect(screen.getByText(/Official KPI boards/i)).toBeTruthy()

    const askLink = screen.getByRole('link', { name: 'Ask with this source' })
    const askUrl = new URL(askLink.getAttribute('href') ?? '', 'https://dreamfi.test')
    expect(askUrl.pathname).toBe('/console/knowledge/ask')
    expect(askUrl.searchParams.get('source')).toBe('metabase')

    const generateLink = screen.getByRole('link', { name: /Generate/i })
    const generateUrl = new URL(generateLink.getAttribute('href') ?? '', 'https://dreamfi.test')
    expect(generateUrl.pathname).toContain('/console/generate/')
    expect(generateUrl.searchParams.get('source')).toBe('metabase')
  })

  it('renders the Socure workspace with source-grounded follow-up links', () => {
    renderWithConsoleWorkspace(<SourceDetailPage data={consoleDevelopmentSlice} sourceId="socure" />, {
      path: '/console/integrations/socure?topic=kyc-conversion',
    })

    expect(screen.getAllByText('Socure workspace').length).toBeGreaterThan(0)
    expect(screen.getByText(/Fraud risk by tier/i)).toBeTruthy()
    expect(screen.getByText(/Related workflows/i)).toBeTruthy()
    expect(screen.getAllByRole('link', { name: 'Ask' }).length).toBeGreaterThan(0)
  })
})
