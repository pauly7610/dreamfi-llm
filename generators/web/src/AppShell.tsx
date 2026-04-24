import { useEffect, useState } from 'react'

import AskPalette from './components/console/AskPalette'
import ConsoleShell from './components/console/ConsoleShell'
import { ConsoleWorkspaceProvider } from './components/console/ConsoleWorkspaceContext'
import LoadingSkeleton from './components/console/LoadingSkeleton'
import useConsoleData from './hooks/useConsoleData'
import AskPage from './pages/AskPage'
import ArtifactsPage from './pages/ArtifactsPage'
import GeneratePage from './pages/GeneratePage'
import MethodologyPage from './pages/MethodologyPage'
import OperatorConsolePage from './pages/OperatorConsolePage'
import ReviewPage from './pages/ReviewPage'
import SourceDetailPage from './pages/SourceDetailPage'
import TopicRoomPage from './pages/TopicRoomPage'
import TrustPage from './pages/TrustPage'
import { generatorSlugFromIdentifier } from './utils/consoleRoutes'
import {
  CONSOLE_NAVIGATE_EVENT,
  currentConsoleLocation,
  navigateConsole,
} from './utils/consoleNavigation'

export function normalizeLegacyPath(path: string): string {
  if (path === '/console/knowledge') {
    return '/console/knowledge/ask'
  }
  if (path.startsWith('/console/knowledge/') && !path.startsWith('/console/knowledge/ask')) {
    return '/console/knowledge/ask'
  }
  if (path === '/console/planning' || path.startsWith('/console/planning/')) {
    return '/console/topics'
  }
  if (path === '/console/metrics' || path.startsWith('/console/metrics/')) {
    return '/console/integrations/metabase'
  }
  if (path === '/console/ui-support' || path.startsWith('/console/ui-support/')) {
    return '/console/topics/onboarding'
  }
  if (path === '/console/generators' || path.startsWith('/console/generators/')) {
    return '/console/generate/weekly-brief'
  }
  if (path.startsWith('/console/generate/')) {
    const segments = path.split('/').filter(Boolean)
    const rawTemplateName = segments[2]
    const canonicalTemplateName = generatorSlugFromIdentifier(rawTemplateName)
    if (rawTemplateName && rawTemplateName !== canonicalTemplateName) {
      return `/console/generate/${canonicalTemplateName}`
    }
  }

  return path
}

function renderPage(path: string, data: ReturnType<typeof useConsoleData>['data'], loading: boolean, error: string | null, retry: () => void) {
  if (loading && !data) {
    return <LoadingSkeleton />
  }
  if (path.startsWith('/console/artifacts')) {
    return <ArtifactsPage data={data} />
  }
  if (path.startsWith('/console/review')) {
    return <ReviewPage data={data} />
  }
  if (path.startsWith('/console/trust')) {
    return <TrustPage data={data} />
  }
  if (path.startsWith('/console/methodology')) {
    return <MethodologyPage />
  }
  if (path.startsWith('/console/generate')) {
    const templateName = path.split('/').pop() || 'weekly-brief'
    return <GeneratePage data={data} templateName={templateName} />
  }
  if (path.startsWith('/console/knowledge/ask')) {
    return <AskPage data={data} />
  }
  if (path.startsWith('/console/topics')) {
    const topicId = path.split('/').filter(Boolean)[2] ?? null
    return <TopicRoomPage data={data} topicId={topicId ? decodeURIComponent(topicId) : null} />
  }
  if (path.startsWith('/console/integrations')) {
    const sourceId = path.split('/').filter(Boolean)[2] ?? null
    return <SourceDetailPage data={data} sourceId={sourceId ? decodeURIComponent(sourceId) : null} />
  }
  return <OperatorConsolePage data={data} loading={loading} error={error} retry={retry} />
}

function AppShell() {
  const [location, setLocation] = useState(currentConsoleLocation)
  const { data, loading, error, retry } = useConsoleData()
  const path = normalizeLegacyPath(location.path)
  const normalizedLocation = path === location.path
    ? location
    : {
        path,
        search: location.search,
        hash: location.hash,
        href: `${path}${location.search}${location.hash}`,
      }

  useEffect(() => {
    function syncLocation() {
      setLocation(currentConsoleLocation())
    }

    window.addEventListener('popstate', syncLocation)
    window.addEventListener(CONSOLE_NAVIGATE_EVENT, syncLocation as EventListener)

    return () => {
      window.removeEventListener('popstate', syncLocation)
      window.removeEventListener(CONSOLE_NAVIGATE_EVENT, syncLocation as EventListener)
    }
  }, [])

  useEffect(() => {
    if (path !== location.path) {
      navigateConsole(`${path}${location.search}${location.hash}`, { replace: true })
    }
  }, [location.hash, location.path, location.search, path])

  return (
    <ConsoleWorkspaceProvider location={normalizedLocation} integrations={data?.integrations ?? []}>
      <ConsoleShell activePath={path}>
        {renderPage(path, data, loading, error, retry)}
      </ConsoleShell>
      <AskPalette />
    </ConsoleWorkspaceProvider>
  )
}

export default AppShell
