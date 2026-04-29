// @vitest-environment jsdom
import { cleanup, fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { consoleDevelopmentSlice } from '../content/consoleDevelopmentSlice'
import { renderWithConsoleWorkspace } from '../test/renderWithConsoleWorkspace'
import TopicRoomPage from './TopicRoomPage'

afterEach(() => {
  cleanup()
  window.localStorage.clear()
  window.history.replaceState(null, '', '/')
})

describe('TopicRoomPage', () => {
  it('shows a directory of product problem rooms', () => {
    renderWithConsoleWorkspace(<TopicRoomPage data={consoleDevelopmentSlice} topicId={null} />, {
      path: '/console/topics',
    })

    expect(screen.getByRole('heading', { name: /Choose the decision room before choosing the tool\./i })).toBeTruthy()
    expect(screen.getByRole('link', { name: 'KYC conversion' }).getAttribute('href')).toBe('/console/topics/kyc-conversion')
    expect(screen.getByRole('link', { name: 'Lifecycle messaging' }).getAttribute('href')).toBe('/console/topics/lifecycle-messaging')
  })

  it('shows signals and generated work for a topic room', () => {
    renderWithConsoleWorkspace(<TopicRoomPage data={consoleDevelopmentSlice} topicId="kyc-conversion" />, {
      path: '/console/topics/kyc-conversion',
    })

    expect(screen.getByRole('heading', { name: 'KYC conversion' })).toBeTruthy()
    expect(screen.getAllByText(/APPROVED KYC/i).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/MANUAL REVIEW LOAD/i).length).toBeGreaterThan(0)
    expect(screen.getByText(/Timeline/i)).toBeTruthy()
    expect(screen.getByText('Linked work')).toBeTruthy()

    const askLink = screen.getByRole('link', { name: 'Ask about this topic' })
    const askUrl = new URL(askLink.getAttribute('href') ?? '', 'https://dreamfi.test')
    expect(askUrl.pathname).toBe('/console/knowledge/ask')
    expect(askUrl.searchParams.get('topic')).toBe('kyc-conversion')
    expect(askUrl.searchParams.get('q')).toBe('Why did KYC conversion move this week?')

    const generateLink = screen.getByRole('link', { name: 'Generate' })
    const generateUrl = new URL(generateLink.getAttribute('href') ?? '', 'https://dreamfi.test')
    expect(generateUrl.pathname).toBe('/console/generate/risk-brd')
    expect(generateUrl.searchParams.get('topic')).toBe('kyc-conversion')
  })

  it('lets the user add a custom topic room from the directory', async () => {
    renderWithConsoleWorkspace(<TopicRoomPage data={consoleDevelopmentSlice} topicId={null} />, {
      path: '/console/topics',
    })

    fireEvent.click(screen.getByRole('button', { name: 'New topic' }))
    fireEvent.change(screen.getByRole('textbox', { name: 'Topic name' }), {
      target: { value: 'Card disputes' },
    })
    fireEvent.change(screen.getByRole('textbox', { name: 'Starter question' }), {
      target: { value: 'Where do card disputes create the most support load' },
    })
    fireEvent.submit(screen.getByRole('button', { name: 'Create topic' }).closest('form') as HTMLFormElement)

    await waitFor(() => expect(screen.getByRole('link', { name: 'Card disputes' }).getAttribute('href')).toBe('/console/topics/card-disputes'))
    expect(window.localStorage.getItem('dreamfi.console.custom-topics')).toContain('card-disputes')
  })
})
