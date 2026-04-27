// @vitest-environment jsdom
import { cleanup, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { consoleDevelopmentSlice } from '../content/consoleDevelopmentSlice'
import { renderWithConsoleWorkspace } from '../test/renderWithConsoleWorkspace'
import AskPage from './AskPage'

afterEach(() => {
  cleanup()
  window.history.replaceState(null, '', '/')
})

describe('AskPage', () => {
  it('keeps the active question grounded in topic sources and next moves', () => {
    renderWithConsoleWorkspace(<AskPage data={consoleDevelopmentSlice} />, {
      path: '/console/knowledge/ask?topic=kyc-conversion&q=Why%20did%20KYC%20conversion%20move%3F',
    })

    expect(screen.getByRole('heading', { name: 'Why did KYC conversion move?' })).toBeTruthy()
    expect(screen.getByRole('heading', { name: /Reasoning/i })).toBeTruthy()
    expect(screen.getByRole('heading', { name: /Next moves/i })).toBeTruthy()
    expect(screen.getAllByRole('link', { name: 'Metabase' })[0].getAttribute('href')).toBe('/console/integrations/metabase')
    expect(screen.getByRole('link', { name: 'Open room' }).getAttribute('href')).toBe('/console/topics/kyc-conversion')

    const generateLink = screen.getByRole('link', { name: 'Compose' })
    const generateUrl = new URL(generateLink.getAttribute('href') ?? '', 'https://dreamfi.test')
    expect(generateUrl.pathname).toBe('/console/generate/risk-brd')
    expect(generateUrl.searchParams.get('q')).toBe('Why did KYC conversion move?')
    expect(generateUrl.searchParams.get('topic')).toBe('kyc-conversion')
  })

  it('can scope an ask to a single source and keep the next artifact source-aware', () => {
    renderWithConsoleWorkspace(<AskPage data={consoleDevelopmentSlice} />, {
      path: '/console/knowledge/ask?source=klaviyo&q=What%20should%20Product%20know%20from%20Klaviyo%3F',
    })

    expect(screen.getByRole('heading', { name: 'What should Product know from Klaviyo?' })).toBeTruthy()
    expect(screen.getAllByText('Klaviyo').length).toBeGreaterThan(0)
    expect(screen.getByText('source-scoped')).toBeTruthy()

    const generateLink = screen.getByRole('link', { name: 'Compose' })
    const generateUrl = new URL(generateLink.getAttribute('href') ?? '', 'https://dreamfi.test')
    expect(generateUrl.pathname).toBe('/console/generate/business-prd')
    expect(generateUrl.searchParams.get('q')).toBe('What should Product know from Klaviyo?')
    expect(generateUrl.searchParams.get('source')).toBe('klaviyo')

    expect(screen.getByRole('link', { name: 'Inspect' }).getAttribute('href')).toBe('/console/integrations/klaviyo')
  })
})
