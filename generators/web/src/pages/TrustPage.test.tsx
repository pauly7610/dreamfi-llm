// @vitest-environment jsdom
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { consoleDevelopmentSlice } from '../content/consoleDevelopmentSlice'
import TrustPage from './TrustPage'

afterEach(() => {
  cleanup()
})

describe('TrustPage', () => {
  it('shows the redesigned trust posture and actions', () => {
    render(<TrustPage data={consoleDevelopmentSlice} />)

    expect(screen.getByRole('heading', { name: 'Where the system stands' })).toBeTruthy()
    expect(screen.getByText('Connector health')).toBeTruthy()
    expect(screen.getByText('Artifact posture')).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Open inbox' }).getAttribute('href')).toBe('/console/review')
    expect(screen.getAllByText('Socure').length).toBeGreaterThan(0)
  })
})
