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
    expect(screen.getByRole('heading', { name: 'Stay inside the same product thread while you switch outputs.' })).toBeTruthy()
    expect(screen.getByText('Topic - KYC conversion')).toBeTruthy()
    expect(screen.getByText('Source - Socure')).toBeTruthy()
    expect(screen.getByText('Why did KYC conversion move this week?')).toBeTruthy()
    expect(screen.getByText('Trust review should stay inline during this run.')).toBeTruthy()
    expect(screen.getByText('Back to receipts')).toBeTruthy()

    const technicalPrdLink = screen.getByRole('link', { name: /Create Technical PRD/i })
    const technicalPrdUrl = new URL(technicalPrdLink.getAttribute('href') ?? '', 'https://dreamfi.test')
    expect(technicalPrdUrl.pathname).toBe('/console/generate/technical-prd')
    expect(technicalPrdUrl.searchParams.get('topic')).toBe('kyc-conversion')
    expect(technicalPrdUrl.searchParams.get('source')).toBe('socure')
    expect(technicalPrdUrl.searchParams.get('q')).toBe('Why did KYC conversion move this week?')

    expect(screen.getByRole('link', { name: 'Open trust rails' }).getAttribute('href')).toBe('/console/trust')
  })
})
