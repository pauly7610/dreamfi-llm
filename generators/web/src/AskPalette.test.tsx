// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import AppShell from './AppShell'

afterEach(() => {
  cleanup()
  window.localStorage.clear()
  window.history.replaceState(null, '', '/')
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
})

describe('AskPalette', () => {
  it('keeps the draft intact across reopen and remembers recent asks', async () => {
    vi.stubEnv('DEV', true)
    window.history.replaceState(null, '', '/console/topics/kyc-conversion?demo=1')
    vi.stubGlobal('fetch', vi.fn())

    render(<AppShell />)

    expect(await screen.findByRole('heading', { name: 'KYC conversion' })).toBeTruthy()

    fireEvent.keyDown(window, { key: 'k', metaKey: true })

    expect(await screen.findByRole('dialog', { name: 'Ask DreamFi' })).toBeTruthy()
    const textarea = screen.getByRole('textbox', { name: 'Question' }) as HTMLTextAreaElement
    expect(textarea.value).toBe('Why did KYC conversion move this week?')
    expect(screen.getByText('Topic · KYC conversion')).toBeTruthy()

    fireEvent.change(textarea, { target: { value: 'Should we change the manual review threshold?' } })
    fireEvent.keyDown(window, { key: 'k', metaKey: true })
    expect((screen.getByRole('textbox', { name: 'Question' }) as HTMLTextAreaElement).value).toBe(
      'Should we change the manual review threshold?',
    )

    fireEvent.click(screen.getByRole('button', { name: 'Dismiss' }))
    expect(screen.queryByRole('dialog', { name: 'Ask DreamFi' })).toBeNull()

    fireEvent.keyDown(window, { key: 'k', metaKey: true })
    expect(await screen.findByRole('dialog', { name: 'Ask DreamFi' })).toBeTruthy()
    expect((screen.getByRole('textbox', { name: 'Question' }) as HTMLTextAreaElement).value).toBe(
      'Should we change the manual review threshold?',
    )

    fireEvent.submit(screen.getByRole('textbox', { name: 'Question' }).closest('form') as HTMLFormElement)

    expect(await screen.findByRole('heading', { name: 'Ask the company what it already knows.' })).toBeTruthy()
    expect(window.location.pathname).toBe('/console/knowledge/ask')
    expect(new URLSearchParams(window.location.search).get('topic')).toBe('kyc-conversion')
    expect(new URLSearchParams(window.location.search).get('q')).toBe('Should we change the manual review threshold?')

    fireEvent.keyDown(window, { key: 'k', metaKey: true })
    expect(await screen.findByRole('button', { name: 'Should we change the manual review threshold?' })).toBeTruthy()
  })
})
