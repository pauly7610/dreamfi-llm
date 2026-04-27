// @vitest-environment jsdom
import { cleanup, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { consoleDevelopmentSlice } from '../content/consoleDevelopmentSlice'
import { renderWithConsoleWorkspace } from '../test/renderWithConsoleWorkspace'
import GeneratePage from './GeneratePage'

afterEach(() => {
  cleanup()
  window.history.replaceState(null, '', '/')
})

describe('GeneratePage', () => {
  it('preserves the current question, topic, and source when switching workflows', () => {
    renderWithConsoleWorkspace(<GeneratePage data={consoleDevelopmentSlice} templateName="risk-brd" />, {
      path: '/console/generate/risk-brd?topic=kyc-conversion&source=socure&q=Why%20did%20KYC%20conversion%20move%20this%20week%3F',
    })

    expect(screen.getByRole('heading', { name: 'Risk BRD' })).toBeTruthy()
    expect(screen.getByText('Why did KYC conversion move this week?')).toBeTruthy()
    expect(screen.getByText('Topic · KYC conversion')).toBeTruthy()
    expect(screen.getByText('Source · Socure')).toBeTruthy()
    expect(screen.getByText(/Publish checklist/i)).toBeTruthy()

    const backLink = screen.getByRole('link', { name: 'Back to ask' })
    const backUrl = new URL(backLink.getAttribute('href') ?? '', 'https://dreamfi.test')
    expect(backUrl.pathname).toBe('/console/knowledge/ask')
    expect(backUrl.searchParams.get('topic')).toBe('kyc-conversion')
    expect(backUrl.searchParams.get('source')).toBe('socure')
    expect(backUrl.searchParams.get('q')).toBe('Why did KYC conversion move this week?')

    const allTemplateLinks = screen.getAllByRole('link', { name: 'Open' })
    const technicalPrdUrl = new URL(allTemplateLinks[0].getAttribute('href') ?? '', 'https://dreamfi.test')
    expect(technicalPrdUrl.pathname).toContain('/console/generate/')
    expect(technicalPrdUrl.searchParams.get('topic')).toBe('kyc-conversion')
    expect(technicalPrdUrl.searchParams.get('source')).toBe('socure')
    expect(technicalPrdUrl.searchParams.get('q')).toBe('Why did KYC conversion move this week?')
    expect(allTemplateLinks.length).toBeGreaterThan(0)
  })
})
