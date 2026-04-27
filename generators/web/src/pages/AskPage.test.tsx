// @vitest-environment jsdom
import { cleanup, fireEvent, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { consoleDevelopmentSlice } from '../content/consoleDevelopmentSlice'
import { renderWithConsoleWorkspace } from '../test/renderWithConsoleWorkspace'
import AskPage from './AskPage'

afterEach(() => {
  cleanup()
  window.localStorage.clear()
  window.history.replaceState(null, '', '/')
})

describe('AskPage', () => {
  it('keeps the active question grounded in topic sources and next moves', () => {
    renderWithConsoleWorkspace(<AskPage data={consoleDevelopmentSlice} />, {
      path: '/console/knowledge/ask?topic=kyc-conversion&q=Why%20did%20KYC%20conversion%20move%3F',
    })

    expect(screen.getByRole('heading', { name: 'Why did KYC conversion move?' })).toBeTruthy()
    expect(screen.getByRole('heading', { name: /How this answer was built/i })).toBeTruthy()
    expect(screen.getByRole('heading', { name: /Suggested follow-ups/i })).toBeTruthy()
    expect(screen.getByRole('heading', { name: /Next moves/i })).toBeTruthy()
    expect((screen.getByRole('textbox', { name: 'Question' }) as HTMLTextAreaElement).value).toBe('Why did KYC conversion move?')
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
    expect(screen.getByText('single source scope')).toBeTruthy()
    expect(screen.getByRole('heading', { name: /Source results/i })).toBeTruthy()

    const generateLink = screen.getByRole('link', { name: 'Compose' })
    const generateUrl = new URL(generateLink.getAttribute('href') ?? '', 'https://dreamfi.test')
    expect(generateUrl.pathname).toBe('/console/generate/business-prd')
    expect(generateUrl.searchParams.get('q')).toBe('What should Product know from Klaviyo?')
    expect(generateUrl.searchParams.get('source')).toBe('klaviyo')

    expect(screen.getByRole('link', { name: 'Inspect' }).getAttribute('href')).toBe('/console/integrations/klaviyo')
  })

  it('offers recent and connector-aware autofill suggestions inside the ask composer', () => {
    window.localStorage.setItem(
      'dreamfi.console.recent-asks',
      JSON.stringify([
        {
          question: 'Should we change the manual review threshold?',
          topicId: 'kyc-conversion',
          sourceId: 'socure',
        },
      ]),
    )

    renderWithConsoleWorkspace(<AskPage data={consoleDevelopmentSlice} />, {
      path: '/console/knowledge/ask?topic=funding',
    })

    expect(screen.getByText('Recent questions and connector-aware autofill update as you type.')).toBeTruthy()
    expect(screen.getByRole('button', { name: /Should we change the manual review threshold\?/i })).toBeTruthy()

    const textarea = screen.getByRole('textbox', { name: 'Question' }) as HTMLTextAreaElement
    fireEvent.change(textarea, { target: { value: 'fund' } })

    const autofillSuggestion = screen.getByRole('button', { name: /Where are users getting stuck before first funding\?/i })
    expect(autofillSuggestion).toBeTruthy()

    fireEvent.click(autofillSuggestion)
    expect(textarea.value).toBe('Where are users getting stuck before first funding?')
    expect(screen.getAllByText(/Metabase|PostHog|NetXD/i).length).toBeGreaterThan(0)
  })
})
