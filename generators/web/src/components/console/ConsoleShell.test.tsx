// @vitest-environment jsdom
import { cleanup, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { renderWithConsoleWorkspace } from '../../test/renderWithConsoleWorkspace'
import ConsoleShell from './ConsoleShell'

afterEach(() => {
  cleanup()
})

describe('ConsoleShell', () => {
  it('keeps the primary navigation focused on sources, trust, and asking', () => {
    renderWithConsoleWorkspace(
      <ConsoleShell activePath="/console">
        <div>Homepage body</div>
      </ConsoleShell>,
    )

    const nav = screen.getByRole('navigation', { name: 'Primary' })
    const labels = within(nav).getAllByRole('link').map((link) => link.textContent)
    const homeLink = screen.getByRole('link', { name: 'DreamFi home' })
    const sourcesLink = screen.getByRole('link', { name: 'Sources' })
    const askLink = screen.getByRole('link', { name: 'Ask from anywhere' })

    expect(labels.length).toBe(3)
    expect(homeLink.getAttribute('href')).toBe('/console')
    expect(sourcesLink.getAttribute('href')).toBe('/console/integrations')
    expect(askLink.getAttribute('href')).toBe('/console/knowledge/ask')
    expect(screen.queryByText('Artifacts')).toBeNull()
    expect(screen.queryByText('Review')).toBeNull()
    expect(screen.queryByText('Product Source Room')).toBeNull()
  })
})
