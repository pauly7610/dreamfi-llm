// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import AppShell from './AppShell'

afterEach(() => {
  cleanup()
  window.history.replaceState(null, '', '/')
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
})

describe('AppShell navigation', () => {
  it('soft-navigates internal console links and form submissions', async () => {
    vi.stubEnv('DEV', true)
    window.history.replaceState(null, '', '/console?demo=1')
    vi.stubGlobal('fetch', vi.fn())

    render(<AppShell />)

    expect(await screen.findByText(/Good morning/i)).toBeTruthy()

    fireEvent.click(screen.getByRole('link', { name: 'Browse connectors' }))

    expect(await screen.findByRole('heading', { name: /Open the connector workspace you need\./i })).toBeTruthy()
    expect(window.location.pathname).toBe('/console/integrations')

    fireEvent.click(screen.getByRole('link', { name: 'DreamFi home' }))

    expect(await screen.findByText(/Good morning/i)).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: /Ask anything/i }))
    expect(await screen.findByRole('dialog', { name: 'Ask DreamFi' })).toBeTruthy()

    const textarea = screen.getByRole('textbox', { name: 'Question' })
    fireEvent.change(textarea, { target: { value: 'Where are users getting stuck before first funding?' } })
    fireEvent.submit(textarea.closest('form') as HTMLFormElement)

    expect(await screen.findByRole('heading', { name: 'Where are users getting stuck before first funding?' })).toBeTruthy()
    expect(window.location.pathname).toBe('/console/knowledge/ask')
    expect(new URLSearchParams(window.location.search).get('q')).toBe('Where are users getting stuck before first funding?')
  })

  it('submits the ask page composer as an in-app query flow', async () => {
    vi.stubEnv('DEV', true)
    window.history.replaceState(null, '', '/console/knowledge/ask?demo=1')
    vi.stubGlobal('fetch', vi.fn())

    render(<AppShell />)

    expect(await screen.findByRole('heading', { name: 'Ask the company what it already knows.' })).toBeTruthy()

    const textarea = screen.getByRole('textbox', { name: 'Question' })
    fireEvent.change(textarea, { target: { value: 'Should onboarding stay in discovery or move forward?' } })
    fireEvent.submit(textarea.closest('form') as HTMLFormElement)

    expect(await screen.findByRole('heading', { name: 'Should onboarding stay in discovery or move forward?' })).toBeTruthy()
    expect(window.location.pathname).toBe('/console/knowledge/ask')
    expect(new URLSearchParams(window.location.search).get('q')).toBe('Should onboarding stay in discovery or move forward?')
  })

  it('normalizes the inbox alias onto the review route', async () => {
    vi.stubEnv('DEV', true)
    window.history.replaceState(null, '', '/console/inbox?demo=1')
    vi.stubGlobal('fetch', vi.fn())

    render(<AppShell />)

    expect(await screen.findByRole('heading', { name: 'What needs you' })).toBeTruthy()
    await waitFor(() => expect(window.location.pathname).toBe('/console/review'))
  })
})
