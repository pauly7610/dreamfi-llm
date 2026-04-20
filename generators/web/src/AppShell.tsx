import ConsoleShell from './components/console/ConsoleShell'
import LoadingSkeleton from './components/console/LoadingSkeleton'
import { moduleById, modules } from './config/modules'
import type { ModuleId } from './config/modules'
import useConsoleData from './hooks/useConsoleData'
import ArtifactsPage from './pages/ArtifactsPage'
import GeneratePage from './pages/GeneratePage'
import ModulePage from './pages/ModulePage'
import OperatorConsolePage from './pages/OperatorConsolePage'
import ReviewPage from './pages/ReviewPage'
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
  return {
    title: 'DreamFi',
    subtitle: 'Make product teams smarter with grounded answers, trusted briefs, and publishable artifacts.',
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
