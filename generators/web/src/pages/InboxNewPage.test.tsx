// @vitest-environment jsdom
import { cleanup, fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { consoleDevelopmentSlice } from '../content/consoleDevelopmentSlice'
import { renderWithConsoleWorkspace } from '../test/renderWithConsoleWorkspace'
import type { ConsolePayload } from '../types/console'
import { InboxNewPage } from './InboxNewPage'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  window.history.replaceState(null, '', '/')
})

describe('InboxNewPage', () => {
  it('sends review outcomes and production outcomes into the learning loop', async () => {
    const fetchMock = vi.fn().mockImplementation(() =>
      Promise.resolve(new Response(
        JSON.stringify({
          feedback: { feedback_id: 'feedback-1', outcome: 'rejected' },
          gold: { gold_id: 'gold-1' },
          outcome: { outcome_id: 'outcome-1', outcome: 'used_in_decision' },
        }),
        { headers: { 'Content-Type': 'application/json' }, status: 201 },
      )),
    )
    vi.stubGlobal('fetch', fetchMock)
    const onDataChanged = vi.fn()
    const blockedArtifact = {
      ...consoleDevelopmentSlice.artifact_queue[0],
      output_id: 'blocked-output-1',
      status: 'blocked' as const,
      test_input_label: 'Blocked launch artifact',
    }
    const data: ConsolePayload = {
      ...consoleDevelopmentSlice,
      alerts: [],
      artifact_queue: [blockedArtifact],
    }

    renderWithConsoleWorkspace(<InboxNewPage data={data} onDataChanged={onDataChanged} />, {
      path: '/console/inbox',
    })

    fireEvent.click(screen.getByRole('button', { name: 'Reject' }))
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1))
    const feedbackBody = JSON.parse(String(fetchMock.mock.calls[0][1].body)) as Record<string, unknown>
    expect(fetchMock.mock.calls[0][0]).toBe('/api/learning/feedback')
    expect(feedbackBody).toMatchObject({
      outcome: 'rejected',
      output_id: 'blocked-output-1',
      promote_to_gold_role: 'regression',
      reason: 'blocked_by_review',
      reviewer_id: 'console-reviewer',
    })

    await waitFor(() => expect(onDataChanged).toHaveBeenCalledTimes(1))
    fireEvent.click(screen.getByRole('button', { name: 'Used' }))
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
    const outcomeBody = JSON.parse(String(fetchMock.mock.calls[1][1].body)) as Record<string, unknown>
    expect(fetchMock.mock.calls[1][0]).toBe('/api/learning/outcomes')
    expect(outcomeBody).toMatchObject({
      actor_id: 'console-operator',
      outcome: 'used_in_decision',
      output_id: 'blocked-output-1',
    })
    await waitFor(() => expect(onDataChanged).toHaveBeenCalledTimes(2))
  })
})
