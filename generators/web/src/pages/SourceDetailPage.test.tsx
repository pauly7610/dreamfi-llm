// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { consoleDevelopmentSlice } from '../content/consoleDevelopmentSlice'
import SourceDetailPage from './SourceDetailPage'

afterEach(() => {
  cleanup()
})

describe('SourceDetailPage', () => {
  it('shows breadcrumbs and Metabase data rows', () => {
    render(<SourceDetailPage data={consoleDevelopmentSlice} sourceId="metabase" />)

    expect(screen.getByRole('navigation', { name: 'Breadcrumb' }).textContent).toContain('Product Source Room')
    expect(screen.getByRole('link', { name: 'Product Source Room' }).getAttribute('href')).toBe('/console')
    expect(screen.getByRole('heading', { name: 'Metabase' })).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Stay inside this connector while you decide' })).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Use trust as an active guide from the source view' })).toBeTruthy()
    expect(screen.getByText('Best artifact next')).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Dashboard collection' })).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Official KPI boards' })).toBeTruthy()
    expect(screen.getAllByText('KYC conversion funnel').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Product KPI warehouse').length).toBeGreaterThan(0)
    expect(screen.getByText('KYC conversion by source')).toBeTruthy()
    expect(screen.getByRole('navigation', { name: 'Metabase workspace sections' })).toBeTruthy()
    expect(screen.getAllByRole('link', { name: 'Ask with this source' })[0].getAttribute('href')).toContain('/console/knowledge/ask?source=metabase')
    expect(screen.getByRole('link', { name: /KYC funnel dashboard/i }).getAttribute('href')).toContain('/console/knowledge/ask?source=metabase')
    expect(screen.getByRole('link', { name: /Metric definitions/i }).getAttribute('href')).toContain('/console/knowledge/ask?source=metabase')
    expect(screen.getByRole('link', { name: /KYC conversion by source/i }).getAttribute('href')).toContain('/console/knowledge/ask?source=metabase')
    expect(screen.getByText('Product KPIs')).toBeTruthy()
    expect(screen.getAllByText('Official').length).toBeGreaterThan(0)
  })

  it('shows product analytics data for PostHog', () => {
    render(<SourceDetailPage data={consoleDevelopmentSlice} sourceId="posthog" />)

    expect(screen.getByRole('heading', { name: 'PostHog' })).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Product analytics' })).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Graphs, trends, and replay context' })).toBeTruthy()
    expect(screen.getAllByText('started_kyc to completed_kyc').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Feature flag exposure').length).toBeGreaterThan(0)
    expect(screen.getByText('document_retry')).toBeTruthy()
    expect(screen.getByText('Conversion trend')).toBeTruthy()
    expect(screen.getByText('Recent friction callouts')).toBeTruthy()
    const kycTopicLink = screen
      .getAllByRole('link', { name: /KYC conversion/i })
      .find((link) => link.getAttribute('href') === '/console/topics/kyc-conversion')
    expect(kycTopicLink?.getAttribute('href')).toBe('/console/topics/kyc-conversion')
  })

  it('shows lifecycle messaging data for Klaviyo', () => {
    render(<SourceDetailPage data={consoleDevelopmentSlice} sourceId="klaviyo" />)

    expect(screen.getByRole('heading', { name: 'Klaviyo' })).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Lifecycle workspace' })).toBeTruthy()
    expect(screen.getAllByText('Onboarding nudge flow').length).toBeGreaterThan(0)
    expect(screen.getAllByText('KYC reminder SMS').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Lifecycle messaging workspace').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Flow performance by lifecycle step').length).toBeGreaterThan(0)
    expect(screen.getByRole('heading', { name: 'Flow library and current performance' })).toBeTruthy()
    expect(screen.getByText('Welcome series')).toBeTruthy()
    expect(screen.getByText('Marketing impact brief')).toBeTruthy()
    expect(screen.getByText('30-day analytics snapshot')).toBeTruthy()
    expect(screen.getByText('Business performance summary')).toBeTruthy()
  })

  it('personalizes Socure around fraud tiers and reason codes', () => {
    render(<SourceDetailPage data={consoleDevelopmentSlice} sourceId="socure" />)

    expect(screen.getByRole('heading', { name: 'Socure' })).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Case review queue' })).toBeTruthy()
    expect(screen.getAllByText('Low-risk approvals').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Medium-risk review queue').length).toBeGreaterThan(0)
    expect(screen.getAllByText('High-risk fraud tier').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Fraud risk by tier').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Decision reason codes').length).toBeGreaterThan(0)
    expect(screen.getByText('Risk BRD draft')).toBeTruthy()
    expect(screen.getByRole('textbox', { name: 'Review the selected case' })).toBeTruthy()
    expect(screen.getAllByText('KYC-10421').length).toBeGreaterThan(0)
    expect(screen.getAllByText('KYC-10488').length).toBeGreaterThan(0)
    expect(screen.getByRole('button', { name: /Which Socure signals are driving manual review\?/i })).toBeTruthy()
    expect(screen.queryByRole('link', { name: /Which Socure signals are driving manual review\?/i })).toBeNull()
    expect(screen.getByRole('navigation', { name: 'Socure workspace sections' })).toBeTruthy()
  })

  it('keeps prioritized Socure questions on the same page', () => {
    render(<SourceDetailPage data={consoleDevelopmentSlice} sourceId="socure" />)

    const textarea = screen.getByRole('textbox', { name: 'Review the selected case' }) as HTMLTextAreaElement

    fireEvent.click(screen.getByRole('button', { name: /KYC-10488/i }))

    expect(textarea.value).toBe('Why was KYC-10488 stepped up and should Product keep that rule?')
    expect(screen.getAllByText('Stepped up').length).toBeGreaterThan(0)

    fireEvent.change(textarea, { target: { value: 'Explain why device mismatch is driving review volume.' } })
    fireEvent.click(screen.getByRole('button', { name: 'Run explainability' }))

    expect(screen.getAllByText('Explain why device mismatch is driving review volume.').length).toBeGreaterThan(0)
  })

  it('personalizes Jira around delivered-vs-implemented audits', () => {
    render(<SourceDetailPage data={consoleDevelopmentSlice} sourceId="jira" />)

    expect(screen.getByRole('heading', { name: 'Jira' })).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Delivery board' })).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Current sprint board' })).toBeTruthy()
    expect(screen.getAllByText('Done tickets missing repo evidence').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Done but still behind a flag').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Done vs implemented').length).toBeGreaterThan(0)
    expect(screen.getByText('KYC-231')).toBeTruthy()
    expect(screen.getByText('Done vs codebase audit')).toBeTruthy()
    expect(screen.getByText('Which tickets conflict with the current PRD?')).toBeTruthy()
    expect(screen.getByRole('link', { name: /KYC-231/i }).getAttribute('href')).toContain('/console/knowledge/ask?source=jira')
    expect(screen.getByText('Sprint burndown')).toBeTruthy()
  })

  it('turns the integrations route into a clickable source directory', () => {
    render(<SourceDetailPage data={consoleDevelopmentSlice} sourceId={null} />)

    expect(screen.getByRole('heading', { name: 'Choose a connector to inspect its data slice.' })).toBeTruthy()
    expect(screen.getByRole('link', { name: /Metabase/i }).getAttribute('href')).toBe('/console/integrations/metabase')
    expect(screen.getByRole('link', { name: /PostHog/i }).getAttribute('href')).toBe('/console/integrations/posthog')
    expect(screen.getByRole('link', { name: /Klaviyo/i }).getAttribute('href')).toBe('/console/integrations/klaviyo')
  })
})
