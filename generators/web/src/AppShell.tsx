import ConsoleShell from './components/console/ConsoleShell'
import LoadingSkeleton from './components/console/LoadingSkeleton'
import { moduleById, modules } from './config/modules'
import type { ModuleId } from './config/modules'
import useConsoleData from './hooks/useConsoleData'
import AskPage from './pages/AskPage'
import ArtifactsPage from './pages/ArtifactsPage'
import GeneratePage from './pages/GeneratePage'
import ModulePage from './pages/ModulePage'
import OperatorConsolePage from './pages/OperatorConsolePage'
import ReviewPage from './pages/ReviewPage'
import SourceDetailPage from './pages/SourceDetailPage'
import TopicRoomPage from './pages/TopicRoomPage'
import TrustPage from './pages/TrustPage'

function currentPath(): string {
  const pathname = window.location.pathname.replace(/\/$/, '')
  return pathname || '/console'
}

function matchModule(path: string): ModuleId | null {
  for (const module of modules) {
    if (path === module.route || path.startsWith(`${module.route}/`)) {
      return module.id
    }
  }
  return null
}

function shellTitle(path: string): { title: string; subtitle: string } {
  const moduleId = matchModule(path)
  if (moduleId) {
    const module = moduleById[moduleId]
    return { title: module.title, subtitle: module.tagline }
  }
  if (path.startsWith('/console/artifacts')) {
    return { title: 'Artifacts', subtitle: 'Inspect and move governed artifacts through review and publish.' }
  }
  if (path.startsWith('/console/review')) {
    return { title: 'Review queue', subtitle: 'Blocked and risky artifacts that need operator judgment.' }
  }
  if (path.startsWith('/console/trust')) {
    return { title: 'Trust view', subtitle: 'Health, risk, and grounding across every module.' }
  }
  if (path.startsWith('/console/generate')) {
    return { title: 'Generators', subtitle: 'Start a governed PRD, brief, or BRD workflow.' }
  }
  if (path.startsWith('/console/knowledge/ask')) {
    return { title: 'Ask DreamFi', subtitle: 'Ask product questions with citations, evidence receipts, and gaps.' }
  }
  if (path.startsWith('/console/topics')) {
    return { title: 'Topic rooms', subtitle: 'Gather sources around recurring Product questions and decisions.' }
  }
  if (path.startsWith('/console/integrations')) {
    return { title: 'Source data', subtitle: 'Choose a connector, inspect its data slice, then ask with citations.' }
  }
  return {
    title: 'Product Source Room',
    subtitle: 'Ask across DreamFi product systems with evidence, citations, and trust signals.',
  }
}

function renderPage(path: string, data: ReturnType<typeof useConsoleData>['data'], loading: boolean, error: string | null, retry: () => void) {
  if (loading && !data) {
    return <LoadingSkeleton />
  }
  const moduleId = matchModule(path)
  if (moduleId) {
    return <ModulePage module={moduleById[moduleId]} data={data} />
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
  const path = currentPath()
  const { title, subtitle } = shellTitle(path)
  const { data, loading, error, retry } = useConsoleData()

  return (
    <ConsoleShell title={title} subtitle={subtitle} activePath={path}>
      {renderPage(path, data, loading, error, retry)}
    </ConsoleShell>
  )
}

export default AppShell
