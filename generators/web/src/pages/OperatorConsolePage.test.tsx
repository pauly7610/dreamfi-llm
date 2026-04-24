// @vitest-environment jsdom
import { cleanup, fireEvent, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { ConsolePayload } from '../types/console'
import { renderWithConsoleWorkspace } from '../test/renderWithConsoleWorkspace'
import OperatorConsolePage from './OperatorConsolePage'

afterEach(() => {
  cleanup()
  window.history.replaceState(null, '', '/')
  window.localStorage.clear()
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
    needs_review_count: 1,
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
  it('proves the product-thread story from the first screen', () => {
    renderWithConsoleWorkspace(
      <OperatorConsolePage data={consolePayload} loading={false} error={null} retry={vi.fn()} />,
      { path: '/console' },
    )

    expect(screen.getByRole('heading', { name: 'Ask once. DreamFi pulls the product context, receipts, and next artifact.' })).toBeTruthy()
    expect(screen.getByText(/This is not chat plus tabs/i)).toBeTruthy()
    expect(screen.getByText(/I know the rooms, sources, and trust rails/i)).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Ask DreamFi' })).toBeTruthy()
    expect(screen.getAllByRole('link', { name: 'Generate Risk BRD' })[0].getAttribute('href')).toContain('/console/generate/risk-brd')
    expect(screen.getByText('Knows the room')).toBeTruthy()
    expect(screen.getByText('Pulls live sources')).toBeTruthy()
    expect(screen.getByText('Carries trust')).toBeTruthy()
    expect(screen.getByText('Why this beats tabs')).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'The product world is changing right now' })).toBeTruthy()
    expect(screen.getByText('Latest draft')).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Act on trust without leaving the thread' })).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Open review' }).getAttribute('href')).toBe('/console/review')
    expect(screen.getByText('Problem rooms')).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Open source directory' }).getAttribute('href')).toBe('/console/integrations')
  })

  it('lets starter questions drive both ask and generate-from-context', () => {
    renderWithConsoleWorkspace(
      <OperatorConsolePage data={consolePayload} loading={false} error={null} retry={vi.fn()} />,
      { path: '/console' },
    )

    const textarea = screen.getByRole('textbox', { name: 'Start with a question' }) as HTMLTextAreaElement

    fireEvent.click(screen.getByRole('button', { name: 'Which lifecycle messages are helping users finish onboarding?' }))

    expect(textarea.value).toBe('Which lifecycle messages are helping users finish onboarding?')
    expect(screen.getByDisplayValue('lifecycle-messaging')).toBeTruthy()

    const generateLink = screen.getAllByRole('link', { name: 'Generate Business PRD' })[0]
    const generateUrl = new URL(generateLink.getAttribute('href') ?? '', 'https://dreamfi.test')
    expect(generateUrl.pathname).toBe('/console/generate/business-prd')
    expect(generateUrl.searchParams.get('topic')).toBe('lifecycle-messaging')
    expect(generateUrl.searchParams.get('q')).toBe('Which lifecycle messages are helping users finish onboarding?')
  })

  it('surfaces recent thread memory on the home page', () => {
    window.localStorage.setItem(
      'dreamfi.console.recent-asks',
      JSON.stringify([
        {
          question: 'Why did KYC conversion move this week?',
          topicId: 'kyc-conversion',
          sourceId: null,
        },
      ]),
    )

    renderWithConsoleWorkspace(
      <OperatorConsolePage data={consolePayload} loading={false} error={null} retry={vi.fn()} />,
      { path: '/console' },
    )

    expect(screen.getByText('Resume recent thread')).toBeTruthy()
    const resumeLink = screen.getByRole('link', { name: 'Reopen with receipts' })
    const resumeUrl = new URL(resumeLink.getAttribute('href') ?? '', 'https://dreamfi.test')
    expect(resumeUrl.pathname).toBe('/console/knowledge/ask')
    expect(resumeUrl.searchParams.get('q')).toBe('Why did KYC conversion move this week?')
    expect(resumeUrl.searchParams.get('topic')).toBe('kyc-conversion')
  })
})
