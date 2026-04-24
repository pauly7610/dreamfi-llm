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
  it('centers the question-first workflow with inline trust and citations', () => {
    renderWithConsoleWorkspace(<AskPage data={consoleDevelopmentSlice} />, {
      path: '/console/knowledge/ask?topic=kyc-conversion&q=Why%20did%20KYC%20conversion%20move%3F',
    })

    expect(screen.getByRole('link', { name: 'Product Source Room' }).getAttribute('href')).toBe('/console')
    expect(screen.getByRole('heading', { name: 'Ask the company what it already knows.' })).toBeTruthy()
    expect(screen.getByText('This thread already knows where to look.')).toBeTruthy()
    expect(screen.getByText('Trust posture')).toBeTruthy()
    expect(screen.getAllByText('Needs review before publish').length).toBeGreaterThan(0)
    expect(screen.getByText('Citations in scope')).toBeTruthy()
    expect(screen.getByText('6 sources')).toBeTruthy()
    expect(screen.getByText('Decision support')).toBeTruthy()
    expect(screen.getByText('Evidence receipt')).toBeTruthy()
    expect(screen.getAllByText('Metabase').length).toBeGreaterThan(0)
    expect(screen.getAllByText('PostHog').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Socure').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Ready to cite').length).toBeGreaterThan(0)
    expect(screen.getByText('Known limits')).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Trust should tell you what to do next' })).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Keep the next move source-aware and effortless' })).toBeTruthy()
    expect(screen.getByText('Inspect next')).toBeTruthy()

    const generateLink = screen.getAllByRole('link', { name: 'Generate Risk BRD' })[0]
    const generateUrl = new URL(generateLink.getAttribute('href') ?? '', 'https://dreamfi.test')
    expect(generateUrl.pathname).toBe('/console/generate/risk-brd')
    expect(generateUrl.searchParams.get('q')).toBe('Why did KYC conversion move?')
    expect(generateUrl.searchParams.get('topic')).toBe('kyc-conversion')

    const trustLink = screen.getAllByRole('link', { name: 'Open trust rails' })[0]
    expect(trustLink.getAttribute('href')).toBe('/console/trust')
    const sourceScopedAsk = screen.getByRole('link', { name: 'Ask with this source' })
    const sourceScopedUrl = new URL(sourceScopedAsk.getAttribute('href') ?? '', 'https://dreamfi.test')
    expect(sourceScopedUrl.searchParams.get('source')).toBe('socure')
  })

  it('can scope an ask to a single source and offer source-aware artifact paths', () => {
    renderWithConsoleWorkspace(<AskPage data={consoleDevelopmentSlice} />, {
      path: '/console/knowledge/ask?source=klaviyo&q=What%20should%20Product%20know%20from%20Klaviyo%3F',
    })

    expect(screen.getAllByText('Klaviyo').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Ready to draft from current context').length).toBeGreaterThan(0)
    expect(screen.getByText('1 sources')).toBeTruthy()
    expect(screen.getAllByText('Business PRD').length).toBeGreaterThan(0)
    expect(screen.getByText('Inspect next')).toBeTruthy()

    const generateLink = screen.getAllByRole('link', { name: 'Generate Business PRD' })[0]
    const generateUrl = new URL(generateLink.getAttribute('href') ?? '', 'https://dreamfi.test')
    expect(generateUrl.pathname).toBe('/console/generate/business-prd')
    expect(generateUrl.searchParams.get('q')).toBe('What should Product know from Klaviyo?')
    expect(generateUrl.searchParams.get('source')).toBe('klaviyo')
  })
})
