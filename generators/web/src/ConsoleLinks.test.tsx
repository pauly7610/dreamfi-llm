// @vitest-environment jsdom
import { cleanup } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { consoleDevelopmentSlice } from './content/consoleDevelopmentSlice'
import { renderWithConsoleWorkspace } from './test/renderWithConsoleWorkspace'
import ArtifactsPage from './pages/ArtifactsPage'
import AskPage from './pages/AskPage'
import GeneratePage from './pages/GeneratePage'
import OperatorConsolePage from './pages/OperatorConsolePage'
import ReviewPage from './pages/ReviewPage'
import SourceDetailPage from './pages/SourceDetailPage'
import TopicRoomPage from './pages/TopicRoomPage'
import TrustPage from './pages/TrustPage'
import { isKnownConsoleHref } from './utils/consoleRoutes'

afterEach(() => {
  cleanup()
  window.history.replaceState(null, '', '/')
})

function expectInternalLinksToResolve(container: HTMLElement) {
  const anchors = Array.from(container.querySelectorAll<HTMLAnchorElement>('a[href]'))

  for (const anchor of anchors) {
    const rawTarget = anchor.getAttribute('href')
    expect(rawTarget, `href should exist on ${anchor.outerHTML}`).toBeTruthy()

    if (!rawTarget || !rawTarget.startsWith('/console')) {
      continue
    }

    expect(isKnownConsoleHref(rawTarget), `Unknown console route: ${rawTarget}`).toBe(true)
  }
}

describe('Console internal links', () => {
  it('keep the redesigned surfaces wired to known routes', () => {
    const pages = [
      {
        path: '/console',
        renderPage: <OperatorConsolePage data={consoleDevelopmentSlice} loading={false} error={null} retry={() => undefined} />,
      },
      {
        path: '/console/knowledge/ask?topic=kyc-conversion',
        renderPage: <AskPage data={consoleDevelopmentSlice} />,
      },
      {
        path: '/console/topics/kyc-conversion',
        renderPage: <TopicRoomPage data={consoleDevelopmentSlice} topicId="kyc-conversion" />,
      },
      {
        path: '/console/integrations/socure?topic=kyc-conversion',
        renderPage: <SourceDetailPage data={consoleDevelopmentSlice} sourceId="socure" />,
      },
      {
        path: '/console/review',
        renderPage: <ReviewPage data={consoleDevelopmentSlice} />,
      },
      {
        path: '/console/artifacts',
        renderPage: <ArtifactsPage data={consoleDevelopmentSlice} />,
      },
      {
        path: '/console/trust',
        renderPage: <TrustPage data={consoleDevelopmentSlice} />,
      },
      {
        path: '/console/generate/technical-prd?topic=kyc-conversion',
        renderPage: <GeneratePage data={consoleDevelopmentSlice} templateName="technical-prd" />,
      },
    ]

    for (const page of pages) {
      const { container, unmount } = renderWithConsoleWorkspace(page.renderPage, { path: page.path })
      expectInternalLinksToResolve(container)
      unmount()
    }
  })
})
