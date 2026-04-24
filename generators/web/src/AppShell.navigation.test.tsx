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
  it('soft-navigates internal console links and forms', async () => {
    vi.stubEnv('DEV', true)
    window.history.replaceState(null, '', '/console?demo=1')
    vi.stubGlobal('fetch', vi.fn())

    render(<AppShell />)

    expect(await screen.findByRole('heading', { name: 'Ask across every product system. Get answers with evidence.' })).toBeTruthy()

    fireEvent.click(screen.getByRole('link', { name: 'Open source directory' }))

    expect(await screen.findByRole('heading', { name: 'Choose a connector to inspect its data slice.' })).toBeTruthy()
    expect(window.location.pathname).toBe('/console/integrations')

    fireEvent.click(screen.getByRole('link', { name: 'Product Source Room' }))

    expect(await screen.findByRole('heading', { name: 'Ask across every product system. Get answers with evidence.' })).toBeTruthy()

    const textarea = screen.getByRole('textbox', { name: 'Start with a question' })
    fireEvent.change(textarea, { target: { value: 'Where are users getting stuck before first funding?' } })
    fireEvent.submit(textarea.closest('form') as HTMLFormElement)

    expect(await screen.findByRole('heading', { name: 'Ask the company what it already knows.' })).toBeTruthy()
    expect(window.location.pathname).toBe('/console/knowledge/ask')
    expect(new URLSearchParams(window.location.search).get('q')).toBe('Where are users getting stuck before first funding?')
  })

  it('preserves hash-only navigation inside the console', async () => {
    vi.stubEnv('DEV', true)
    window.history.replaceState(null, '', '/console?demo=1')
    vi.stubGlobal('fetch', vi.fn())

    render(<AppShell />)

    expect(await screen.findByRole('heading', { name: 'Ask across every product system. Get answers with evidence.' })).toBeTruthy()

    fireEvent.click(screen.getByRole('link', { name: 'Browse connectors' }))

    await waitFor(() => expect(window.location.hash).toBe('#sources'))
  })
})
