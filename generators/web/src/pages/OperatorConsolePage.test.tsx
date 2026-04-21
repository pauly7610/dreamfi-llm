// @vitest-environment jsdom
import { cleanup, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { ConsolePayload } from '../types/console'
import OperatorConsolePage from './OperatorConsolePage'

afterEach(() => {
  cleanup()
})

const consolePayload: ConsolePayload = {
  headline: 'Trust, measured.',
  summary: {
    skill_count: 9,
    active_prompt_count: 9,
    average_latest_score: 0.88,
    average_confidence: 0.82,
    average_export_readiness: 0.91,
    publish_success_rate: 0.75,
    hard_gate_pass_rate: 0.8,
    blocked_artifact_count: 1,
    publish_ready_count: 2,
    published_artifact_count: 4,
    needs_review_count: 0,
  },
  skills: [],
  artifact_queue: [
    {
      output_id: 'out-1',
      skill_id: 'technical_prd',
      skill_display_name: 'Technical PRD',
      round_id: 'round-1',
      test_input_label: 'KYC onboarding review',
      attempt: 1,
      pass_fail: 'pass',
      confidence: 0.88,
      export_readiness: 0.92,
      created_at: '2026-04-21T12:00:00Z',
      status: 'publish_ready',
      artifacts_path: 'artifacts/round-1',
      latest_publish: null,
    },
  ],
  publish_activity: [],
  alerts: [],
  quick_actions: [
    {
      id: 'weekly-brief',
      label: 'Run weekly PM brief',
      href: '/console/generate/weekly-brief',
      kind: 'primary',
    },
    {
      id: 'technical-prd',
      label: 'Create Technical PRD',
      href: '/console/generate/technical-prd',
      kind: 'secondary',
    },
    {
      id: 'business-prd',
      label: 'Create Business PRD',
      href: '/console/generate/business-prd',
      kind: 'secondary',
    },
    {
      id: 'risk-brd',
      label: 'Create Risk BRD',
      href: '/console/generate/risk-brd',
      kind: 'secondary',
    },
    {
      id: 'review-blocked',
      label: 'Review blocked artifacts',
      href: '/console/review?status=blocked',
      kind: 'secondary',
    },
    {
      id: 'trust-dashboard',
      label: 'Open trust dashboard',
      href: '/console/trust',
      kind: 'secondary',
    },
  ],
  integrations: [
    {
      id: 'jira',
      name: 'Jira',
      category: 'planning',
      purpose: 'Sprints, issues, and delivery state',
      used_for: ['weekly-brief', 'technical-prd'],
      status: 'available',
      href: '/console/integrations/jira',
    },
    {
      id: 'posthog',
      name: 'PostHog',
      category: 'product_analytics',
      purpose: 'Product events, funnels, and session data',
      used_for: ['weekly-brief'],
      status: 'connected',
      href: '/console/integrations/posthog',
    },
  ],
  domain_health: [
    {
      domain: 'planning',
      trust_score: 0.91,
      pass_rate: 0.8,
      issue_count: 0,
    },
  ],
}

describe('OperatorConsolePage', () => {
  it('leads with the shared source-room experience', () => {
    render(<OperatorConsolePage data={consolePayload} loading={false} error={null} retry={vi.fn()} />)

    expect(screen.getByRole('heading', { name: 'Ask across every product system. Get answers with evidence.' })).toBeTruthy()
    expect(screen.getByText('Product connector space')).toBeTruthy()
    expect(screen.getAllByLabelText('Jira connector').length).toBeGreaterThan(0)
    expect(screen.getAllByLabelText('PostHog connector').length).toBeGreaterThan(0)
    expect(screen.getByText('Planning + docs')).toBeTruthy()
    expect(screen.getByText('Metrics + growth')).toBeTruthy()
    expect(screen.getByText('Problem rooms')).toBeTruthy()
    const kycTopicLink = screen
      .getAllByRole('link', { name: /KYC conversion/i })
      .find((link) => link.getAttribute('href') === '/console/topics/kyc-conversion')
    expect(kycTopicLink?.getAttribute('href')).toBe('/console/topics/kyc-conversion')
    expect(screen.getByText('Pick a connector')).toBeTruthy()
    expect(screen.getByText('View its data slice')).toBeTruthy()
    expect(screen.queryByText('Ways Product uses the source room')).toBeNull()
    expect(screen.queryByText(/queue/i)).toBeNull()
    const posthogLink = screen
      .getAllByRole('link')
      .find((link) => link.getAttribute('href') === '/console/integrations/posthog' && link.textContent?.includes('View data'))
    expect(posthogLink?.getAttribute('href')).toBe('/console/integrations/posthog')
    expect(posthogLink?.textContent).toContain('View data')
    const sourcesMapped = screen.getByText('Mapped sources').closest('div')
    expect(sourcesMapped?.textContent).toContain('2')
  })

  it('keeps creation actions prominent and leaves operator-only actions out of the main action center', () => {
    const { container } = render(<OperatorConsolePage data={consolePayload} loading={false} error={null} retry={vi.fn()} />)

    expect(screen.getByText('Create from context')).toBeTruthy()
    const actionCenter = container.querySelector('.action-center')

    expect(actionCenter).toBeTruthy()

    expect(within(actionCenter as HTMLElement).getByText('Run weekly PM brief')).toBeTruthy()
    expect(within(actionCenter as HTMLElement).getByText('Create Technical PRD')).toBeTruthy()
    expect(within(actionCenter as HTMLElement).getByText('Create Risk BRD')).toBeTruthy()
    expect(within(actionCenter as HTMLElement).queryByText('Create Business PRD')).toBeNull()
    expect(within(actionCenter as HTMLElement).queryByText('Review blocked artifacts')).toBeNull()
    expect(within(actionCenter as HTMLElement).queryByText('Open trust dashboard')).toBeNull()
  })
})
