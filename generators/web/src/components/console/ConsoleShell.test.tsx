// @vitest-environment jsdom
import { cleanup, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import ConsoleShell from './ConsoleShell'

afterEach(() => {
  cleanup()
})

describe('ConsoleShell', () => {
  it('keeps the primary navigation focused on sources, trust, and asking', () => {
    render(
      <ConsoleShell
        title="Product Source Room"
        subtitle="Ask across DreamFi product systems."
        activePath="/console"
      >
        <div>Homepage body</div>
      </ConsoleShell>,
    )

    const nav = screen.getByRole('navigation', { name: 'Primary' })
    const labels = within(nav).getAllByRole('link').map((link) => link.textContent)
    const homeLink = screen.getByRole('link', { name: 'DreamFi home' })

    expect(labels).toEqual(['Sources', 'Trust', 'Ask'])
    expect(homeLink.getAttribute('href')).toBe('/console')
    expect(screen.queryByText('Artifacts')).toBeNull()
    expect(screen.queryByText('Review')).toBeNull()
    expect(screen.queryByText('Product Knowledge Hub')).toBeNull()
  })
})
