// @vitest-environment jsdom
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { consoleDevelopmentSlice } from '../content/consoleDevelopmentSlice'
import TopicRoomPage from './TopicRoomPage'

afterEach(() => {
  cleanup()
})

describe('TopicRoomPage', () => {
  it('shows a directory of product problem rooms', () => {
    render(<TopicRoomPage data={consoleDevelopmentSlice} topicId={null} />)

    expect(screen.getByRole('link', { name: 'Product Source Room' }).getAttribute('href')).toBe('/console')
    expect(screen.getByRole('heading', { name: 'Choose the product question before choosing the tool.' })).toBeTruthy()
    expect(screen.getByRole('link', { name: /KYC conversion/i }).getAttribute('href')).toBe('/console/topics/kyc-conversion')
    expect(screen.getByRole('link', { name: /Lifecycle messaging/i }).getAttribute('href')).toBe('/console/topics/lifecycle-messaging')
  })

  it('shows signals, sources, and generated work for a topic room', () => {
    render(<TopicRoomPage data={consoleDevelopmentSlice} topicId="kyc-conversion" />)

    expect(screen.getByRole('heading', { name: 'KYC conversion' })).toBeTruthy()
    expect(screen.getByText('Approved KYC')).toBeTruthy()
    expect(screen.getByText('Manual review load')).toBeTruthy()
    expect(screen.getByText('Workflow state')).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Where this work stands' })).toBeTruthy()
    expect(screen.getByText('Gate 2 · Sponsor-bank alignment')).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'What each system can tell us' })).toBeTruthy()
    expect(screen.getByText('System of record')).toBeTruthy()
    expect(screen.getByRole('link', { name: /What step are we in right now\\?/i }).getAttribute('href')).toContain(
      '/console/knowledge/ask?topic=kyc-conversion',
    )
    expect(screen.getByText('Metabase funnel')).toBeTruthy()
    expect(screen.getByText('PostHog completion')).toBeTruthy()
    expect(screen.getByText('Evidence receipt')).toBeTruthy()
    expect(screen.getByText('Technical PRD')).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Ask about this topic' }).getAttribute('href')).toContain('topic=kyc-conversion')
    const approvedKycLink = screen
      .getAllByRole('link', { name: /Approved KYC/i })
      .find((link) => link.getAttribute('href') === '/console/integrations/metabase#source-data')
    const manualReviewLink = screen
      .getAllByRole('link', { name: /Manual review load/i })
      .find((link) => link.getAttribute('href') === '/console/integrations/socure#source-data')
    expect(approvedKycLink?.getAttribute('href')).toBe('/console/integrations/metabase#source-data')
    expect(manualReviewLink?.getAttribute('href')).toBe('/console/integrations/socure#source-data')
    expect(screen.getByRole('link', { name: /Metabase funnel/i }).getAttribute('href')).toBe('/console/integrations/metabase#source-data')
    expect(screen.getByRole('link', { name: /Socure health/i }).getAttribute('href')).toBe('/console/integrations/socure#source-data')
    expect(screen.getByRole('link', { name: 'Weekly PM Brief' }).getAttribute('href')).toBe('/console/generate/weekly-brief')
  })
})
