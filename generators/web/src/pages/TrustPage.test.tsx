// @vitest-environment jsdom
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { consoleDevelopmentSlice } from '../content/consoleDevelopmentSlice'
import TrustPage from './TrustPage'

afterEach(() => {
  cleanup()
})

describe('TrustPage', () => {
  it('turns trust from a static summary into a live, actionable surface', () => {
    render(<TrustPage data={consoleDevelopmentSlice} />)

    expect(screen.getByRole('heading', { name: 'Trust should feel live, not archival' })).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Act on the current trust posture' })).toBeTruthy()
    expect(screen.getByText('Connector risk')).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Inspect source' }).getAttribute('href')).toBe('/console/integrations/socure')
    expect(screen.getByRole('link', { name: 'Resolve from source' }).getAttribute('href')).toBe('/console/review?focus=dev-artifact-risk-brd')
    expect(screen.getByRole('link', { name: 'Open review queue' }).getAttribute('href')).toBe('/console/review')
  })
})
