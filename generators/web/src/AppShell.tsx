import ConsoleShell from './components/console/ConsoleShell'
import LoadingSkeleton from './components/console/LoadingSkeleton'
import useConsoleData from './hooks/useConsoleData'
import ArtifactsPage from './pages/ArtifactsPage'
import GeneratePage from './pages/GeneratePage'
import OperatorConsolePage from './pages/OperatorConsolePage'
import ReviewPage from './pages/ReviewPage'
import TrustPage from './pages/TrustPage'

function currentPath(): string {
  const pathname = window.location.pathname.replace(/\/$/, '')
  return pathname || '/console'
}

function shellTitle(path: string): { title: string; subtitle: string } {
  if (path.startsWith('/console/artifacts')) {
    return { title: 'Artifact console', subtitle: 'Inspect, review, and move through governed artifact workflows.' }
  }
  if (path.startsWith('/console/review')) {
    return { title: 'Review console', subtitle: 'Focus on blocked work and risky artifacts that need operator judgment.' }
  }
  if (path.startsWith('/console/trust')) {
    return { title: 'Trust dashboard', subtitle: 'Understand health, risk, and how DreamFi is governing the work.' }
  }
  if (path.startsWith('/console/generate')) {
    return { title: 'Generation workflows', subtitle: 'Start governed generation flows for product artifacts and briefs.' }
  }
  return { title: 'Operator console', subtitle: 'Today’s operating state across product trust workflows.' }
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
