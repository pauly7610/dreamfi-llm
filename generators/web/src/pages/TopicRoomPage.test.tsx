// @vitest-environment jsdom
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { consoleDevelopmentSlice } from '../fixtures/consoleDevelopmentSlice'
import TopicRoomPage from './TopicRoomPage'

afterEach(() => {
  cleanup()
})

describe('TopicRoomPage', () => {
  it('shows a directory of product problem rooms', () => {
    render(<TopicRoomPage data={consoleDevelopmentSlice} topicId={null} />)

    expect(screen.getByRole('heading', { name: 'Choose the product question before choosing the tool.' })).toBeTruthy()
    expect(screen.getByRole('link', { name: /KYC conversion/i }).getAttribute('href')).toBe('/console/topics/kyc-conversion')
    expect(screen.getByRole('link', { name: /Lifecycle messaging/i }).getAttribute('href')).toBe('/console/topics/lifecycle-messaging')
  })

  it('shows signals, sources, and generated work for a topic room', () => {
    render(<TopicRoomPage data={consoleDevelopmentSlice} topicId="kyc-conversion" />)

    expect(screen.getByRole('heading', { name: 'KYC conversion' })).toBeTruthy()
    expect(screen.getByText('Metabase funnel')).toBeTruthy()
    expect(screen.getByText('PostHog completion')).toBeTruthy()
    expect(screen.getByText('Evidence receipt')).toBeTruthy()
    expect(screen.getByText('Technical PRD')).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Ask about this topic' }).getAttribute('href')).toContain('topic=kyc-conversion')
  })
})
