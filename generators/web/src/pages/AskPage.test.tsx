// @vitest-environment jsdom
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { consoleDevelopmentSlice } from '../fixtures/consoleDevelopmentSlice'
import AskPage from './AskPage'

afterEach(() => {
  cleanup()
  window.history.replaceState(null, '', '/')
})

describe('AskPage', () => {
  it('centers the question-first workflow with evidence receipts', () => {
    window.history.replaceState(null, '', '/console/knowledge/ask?topic=kyc-conversion&q=Why%20did%20KYC%20conversion%20move%3F')

    render(<AskPage data={consoleDevelopmentSlice} />)

    expect(screen.getByRole('heading', { name: 'Ask the company what it already knows.' })).toBeTruthy()
    expect(screen.getByDisplayValue('Why did KYC conversion move?')).toBeTruthy()
    expect(screen.getAllByText('KYC conversion').length).toBeGreaterThan(0)
    expect(screen.getByText('Evidence receipt')).toBeTruthy()
    expect(screen.getByText('Metabase')).toBeTruthy()
    expect(screen.getByText('PostHog')).toBeTruthy()
    expect(screen.getByText('Known limits')).toBeTruthy()
  })

  it('can scope an ask to a single source from source pages', () => {
    window.history.replaceState(null, '', '/console/knowledge/ask?source=klaviyo&q=What%20should%20Product%20know%20from%20Klaviyo%3F')

    render(<AskPage data={consoleDevelopmentSlice} />)

    expect(screen.getAllByText('Klaviyo').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Lifecycle messaging, audiences, and campaign sends.').length).toBeGreaterThan(0)
    expect(screen.getByText('Use the source detail page to inspect the available data slice before generating a publishable artifact.')).toBeTruthy()
  })
})
