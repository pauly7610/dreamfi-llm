// @vitest-environment jsdom
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import type { ArtifactRecord } from '../../types/console'
import PriorityQueue from './PriorityQueue'

afterEach(() => {
  cleanup()
})

const artifacts: ArtifactRecord[] = [
  {
    output_id: 'artifact-1',
    skill_id: 'technical_prd',
    skill_display_name: 'Technical PRD',
    round_id: 'round-1',
    test_input_label: 'KYC drop review',
    attempt: 1,
    pass_fail: 'pass',
    confidence: 0.91,
    export_readiness: 0.88,
    created_at: '2026-04-21T12:00:00Z',
    status: 'publish_ready',
    artifacts_path: 'dev/artifacts/technical-prd',
    latest_publish: null,
  },
]

describe('PriorityQueue', () => {
  it('uses canonical generator routes for regenerate links', () => {
    render(<PriorityQueue artifacts={artifacts} />)

    expect(screen.getByRole('link', { name: 'Regenerate' }).getAttribute('href')).toBe('/console/generate/technical-prd?source=artifact-1')
  })
})
