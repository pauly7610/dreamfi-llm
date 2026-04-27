// @vitest-environment jsdom
import { cleanup, fireEvent, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { consoleDevelopmentSlice } from '../content/consoleDevelopmentSlice'
import { renderWithConsoleWorkspace } from '../test/renderWithConsoleWorkspace'
import OperatorConsolePage from './OperatorConsolePage'

afterEach(() => {
  cleanup()
  window.history.replaceState(null, '', '/')
})

describe('OperatorConsolePage', () => {
  it('opens on the redesigned home surface with thread and source entry points', () => {
    renderWithConsoleWorkspace(
      <OperatorConsolePage data={consoleDevelopmentSlice} loading={false} error={null} retry={vi.fn()} />,
      { path: '/console' },
    )

    expect(screen.getByText(/Good morning/i)).toBeTruthy()
    expect(screen.getByRole('img', { name: 'DreamFi opening illustration' })).toBeTruthy()
    expect(screen.getByText('Open threads')).toBeTruthy()
    expect(screen.getByText('Source health')).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Browse connectors' }).getAttribute('href')).toBe('/console/integrations')
    expect(screen.getAllByRole('link', { name: 'Open' })[0].getAttribute('href')).toContain('/console/topics/')
  })

  it('surfaces load errors with a retry affordance', () => {
    const retry = vi.fn()
    renderWithConsoleWorkspace(
      <OperatorConsolePage data={consoleDevelopmentSlice} loading={false} error="Request failed with 500" retry={retry} />,
      { path: '/console' },
    )

    expect(screen.getByText('Request failed with 500')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
    expect(retry).toHaveBeenCalledTimes(1)
  })
})
