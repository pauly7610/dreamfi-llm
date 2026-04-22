// @vitest-environment jsdom
import { cleanup, render } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import ConsoleShell from './components/console/ConsoleShell'
import { consoleDevelopmentSlice } from './content/consoleDevelopmentSlice'
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
  const forms = Array.from(container.querySelectorAll<HTMLFormElement>('form[action]'))

  for (const element of [...anchors, ...forms]) {
    const attribute = element instanceof HTMLAnchorElement ? 'href' : 'action'
    const rawTarget = element.getAttribute(attribute)

    expect(rawTarget, `${attribute} should exist on ${element.outerHTML}`).toBeTruthy()

    if (!rawTarget) {
      continue
    }

    if (rawTarget.startsWith('#')) {
      const hashTarget = rawTarget.slice(1)
      expect(container.querySelector(`#${hashTarget}`), `Missing in-page target for ${rawTarget}`).toBeTruthy()
      continue
    }

    if (rawTarget.startsWith('/console')) {
      expect(isKnownConsoleHref(rawTarget), `Unknown console route: ${rawTarget}`).toBe(true)
    }
  }
}

describe('Console internal links', () => {
  it('keep the main console surfaces wired to known routes', () => {
    const pages = [
      {
        activePath: '/console',
        renderPage: (
          <OperatorConsolePage
            data={consoleDevelopmentSlice}
            loading={false}
            error={null}
            retry={() => undefined}
          />
        ),
      },
      {
        activePath: '/console/knowledge/ask',
        setup: () => window.history.replaceState(null, '', '/console/knowledge/ask?topic=kyc-conversion'),
        renderPage: <AskPage data={consoleDevelopmentSlice} />,
      },
      {
        activePath: '/console/topics/kyc-conversion',
        renderPage: <TopicRoomPage data={consoleDevelopmentSlice} topicId="kyc-conversion" />,
      },
      {
        activePath: '/console/integrations/socure',
        renderPage: <SourceDetailPage data={consoleDevelopmentSlice} sourceId="socure" />,
      },
      {
        activePath: '/console/review',
        renderPage: <ReviewPage data={consoleDevelopmentSlice} />,
      },
      {
        activePath: '/console/artifacts',
        renderPage: <ArtifactsPage data={consoleDevelopmentSlice} />,
      },
      {
        activePath: '/console/trust',
        renderPage: <TrustPage data={consoleDevelopmentSlice} />,
      },
      {
        activePath: '/console/generate/technical-prd',
        renderPage: <GeneratePage data={consoleDevelopmentSlice} templateName="technical-prd" />,
      },
    ]

    for (const page of pages) {
      page.setup?.()
      const { container, unmount } = render(
        <ConsoleShell activePath={page.activePath}>
          {page.renderPage}
        </ConsoleShell>,
      )

      expectInternalLinksToResolve(container)
      unmount()
    }
  })
})
