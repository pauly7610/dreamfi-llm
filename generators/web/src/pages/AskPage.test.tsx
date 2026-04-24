// @vitest-environment jsdom
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { consoleDevelopmentSlice } from '../content/consoleDevelopmentSlice'
import { renderWithConsoleWorkspace } from '../test/renderWithConsoleWorkspace'
import AskPage from './AskPage'

afterEach(() => {
  cleanup()
  window.history.replaceState(null, '', '/')
})

describe('AskPage', () => {
  it('centers the question-first workflow with evidence receipts', () => {
    renderWithConsoleWorkspace(<AskPage data={consoleDevelopmentSlice} />, {
      path: '/console/knowledge/ask?topic=kyc-conversion&q=Why%20did%20KYC%20conversion%20move%3F',
    })

    expect(screen.getByRole('link', { name: 'Product Source Room' }).getAttribute('href')).toBe('/console')
    expect(screen.getByRole('heading', { name: 'Ask the company what it already knows.' })).toBeTruthy()
    expect(screen.getByDisplayValue('Why did KYC conversion move?')).toBeTruthy()
    expect(screen.getAllByText('KYC conversion').length).toBeGreaterThan(0)
    expect(screen.getByText('Decision support')).toBeTruthy()
    expect(screen.getByText('Current step')).toBeTruthy()
    expect(screen.getByText('Should this move to Ready for Dev or stay blocked?')).toBeTruthy()
    expect(screen.getByText('Evidence receipt')).toBeTruthy()
    expect(screen.getByText('Metabase')).toBeTruthy()
    expect(screen.getByText('PostHog')).toBeTruthy()
    expect(screen.getByText('Known limits')).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Inspect sources' }).getAttribute('href')).toBe('/console/integrations')

    const generateLink = screen.getByRole('link', { name: 'Generate Risk BRD' })
    const generateUrl = new URL(generateLink.getAttribute('href') ?? '', 'https://dreamfi.test')
    expect(generateUrl.pathname).toBe('/console/generate/risk-brd')
    expect(generateUrl.searchParams.get('q')).toBe('Why did KYC conversion move?')
    expect(generateUrl.searchParams.get('topic')).toBe('kyc-conversion')
  })

  it('can scope an ask to a single source from source pages', () => {
    renderWithConsoleWorkspace(<AskPage data={consoleDevelopmentSlice} />, {
      path: '/console/knowledge/ask?source=klaviyo&q=What%20should%20Product%20know%20from%20Klaviyo%3F',
    })

    expect(screen.getAllByText('Klaviyo').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Lifecycle messaging, audiences, and campaign sends.').length).toBeGreaterThan(0)
    expect(screen.getByText('Use the source detail page to inspect the available data slice before generating a publishable artifact.')).toBeTruthy()

    const generateLink = screen.getByRole('link', { name: 'Generate Business PRD' })
    const generateUrl = new URL(generateLink.getAttribute('href') ?? '', 'https://dreamfi.test')
    expect(generateUrl.pathname).toBe('/console/generate/business-prd')
    expect(generateUrl.searchParams.get('q')).toBe('What should Product know from Klaviyo?')
    expect(generateUrl.searchParams.get('source')).toBe('klaviyo')
  })
})
