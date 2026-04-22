import { useEffect, useState } from 'react'

import ConsoleShell from './components/console/ConsoleShell'
import LoadingSkeleton from './components/console/LoadingSkeleton'
import useConsoleData from './hooks/useConsoleData'
import AskPage from './pages/AskPage'
import ArtifactsPage from './pages/ArtifactsPage'
import GeneratePage from './pages/GeneratePage'
import OperatorConsolePage from './pages/OperatorConsolePage'
import ReviewPage from './pages/ReviewPage'
import SourceDetailPage from './pages/SourceDetailPage'
import TopicRoomPage from './pages/TopicRoomPage'
import TrustPage from './pages/TrustPage'
import {
  currentConsoleLocation,
  generatorHrefForContext,
  generatorSlugFromIdentifier,
} from './utils/consoleRoutes'

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
    return '/console/generate'
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

function renderPage(
  path: string,
  search: string,
  data: ReturnType<typeof useConsoleData>['data'],
  loading: boolean,
  error: string | null,
  retry: () => void,
) {
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
  if (path === '/console/generate') {
    const searchParams = new URLSearchParams(search)
    const href = generatorHrefForContext({
      topicId: searchParams.get('topic'),
      sourceId: searchParams.get('source'),
      query: searchParams.get('q'),
    })
    const templateName = href.split('/').pop() || 'technical-prd'
    return <GeneratePage data={data} templateName={templateName} />
  }
  if (path.startsWith('/console/generate/')) {
    const templateName = path.split('/').pop() || 'technical-prd'
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
  const [locationState, setLocationState] = useState(() => currentConsoleLocation())
  const { data, loading, error, retry } = useConsoleData()
  const rawPath = locationState.path
  const search = locationState.search
  const path = normalizeLegacyPath(rawPath)

  useEffect(() => {
    function syncLocation() {
      setLocationState(currentConsoleLocation())
    }

    window.addEventListener('popstate', syncLocation)
    window.addEventListener('console:navigate', syncLocation)

    return () => {
      window.removeEventListener('popstate', syncLocation)
      window.removeEventListener('console:navigate', syncLocation)
    }
  }, [])

  if (path !== rawPath) {
    window.history.replaceState(null, '', `${path}${search}${window.location.hash}`)
  }

  return (
    <ConsoleShell activePath={path}>
      {renderPage(path, search, data, loading, error, retry)}
    </ConsoleShell>
  )
}

export default AppShell
