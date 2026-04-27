import { useEffect, useMemo, useState, type FormEvent, type MouseEvent } from 'react'

import AskPalette from './components/console/AskPalette'
import LoadingSkeleton from './components/console/LoadingSkeleton'
import { ConsoleWorkspaceProvider, useConsoleWorkspace } from './components/console/ConsoleWorkspaceContext'
import { shouldForceDevelopmentSlice, shouldUseDevelopmentSlice } from './content/consoleDevelopmentSlice'
import { AppFrame, Topbar, type Crumb } from './components/shell/Topbar'
import { Sidebar, type NavGroup } from './components/shell/Sidebar'
import type { ProductTopic } from './content/productTopics'
import { workflowByTopicId } from './content/productWorkflows'
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
import type { ConsoleIntegration } from './types/console'
import { generatorSlugFromIdentifier, generatorTitleFromSlug } from './utils/consoleRoutes'
import {
  CONSOLE_NAVIGATE_EVENT,
  currentConsoleLocation,
  hrefForConsoleNavigation,
  isInternalConsoleHref,
  navigateConsole,
  type ConsoleLocation,
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
  if (path === '/console/inbox' || path.startsWith('/console/inbox/')) {
    return '/console/review'
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

function shouldIgnoreShortcutTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) {
    return false
  }

  return target.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName)
}

function shouldBrowserHandleLink(event: MouseEvent<Element>, anchor: HTMLAnchorElement): boolean {
  if (event.defaultPrevented || event.button !== 0) {
    return true
  }

  if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
    return true
  }

  if (anchor.target && anchor.target !== '_self') {
    return true
  }

  if (anchor.hasAttribute('download')) {
    return true
  }

  return false
}

function hrefForConsoleForm(form: HTMLFormElement): string | null {
  const method = (form.getAttribute('method') || form.method || 'get').toLowerCase()
  if (method !== 'get') {
    return null
  }

  const actionAttr = form.getAttribute('action') || currentConsoleLocation().href
  if (!isInternalConsoleHref(actionAttr)) {
    return null
  }

  const action = new URL(actionAttr, window.location.origin)
  const params = new URLSearchParams(action.search)
  const clearedKeys = new Set<string>()
  const formData = new FormData(form)

  formData.forEach((value, key) => {
    if (typeof value !== 'string') {
      return
    }

    if (!clearedKeys.has(key)) {
      params.delete(key)
      clearedKeys.add(key)
    }

    params.append(key, value)
  })

  action.search = params.toString() ? `?${params.toString()}` : ''
  return `${action.pathname}${action.search}${action.hash}`
}

function topicDot(topicId: string): 'good' | 'warn' | 'bad' | undefined {
  const workflow = workflowByTopicId(topicId)
  if (!workflow) {
    return undefined
  }
  if (workflow.currentState.tone === 'blocked') {
    return 'bad'
  }
  if (workflow.currentState.tone === 'watch') {
    return 'warn'
  }
  return 'good'
}

function sourceDot(integration: ConsoleIntegration): 'warn' | 'bad' | undefined {
  if (integration.status === 'degraded') {
    return 'warn'
  }
  if (integration.status === 'not_configured') {
    return 'bad'
  }
  return undefined
}

function navGroupsForData(data: ReturnType<typeof useConsoleData>['data'], topics: ProductTopic[]): NavGroup[] {
  const integrations = data?.integrations ?? []
  const summary = data?.summary

  return [
    {
      items: [
        { id: 'home', label: 'Home', icon: 'home', href: '/console' },
        { id: 'ask', label: 'Ask', icon: 'ask', href: '/console/knowledge/ask' },
        {
          id: 'inbox',
          label: 'Inbox',
          icon: 'inbox',
          href: '/console/review',
          count: summary?.needs_review_count ?? 0,
          dot: (summary?.blocked_artifact_count ?? 0) > 0 ? 'warn' : undefined,
        },
        {
          id: 'artifacts',
          label: 'Artifacts',
          icon: 'artifacts',
          href: '/console/artifacts',
          count: data?.artifact_queue.length ?? 0,
        },
        { id: 'trust', label: 'Trust', icon: 'trust', href: '/console/trust' },
        { id: 'methodology', label: 'Methodology', icon: 'methodology', href: '/console/methodology' },
      ],
    },
    {
      label: 'Topic rooms',
      items: topics.map((topic) => ({
        id: `topic-${topic.id}`,
        label: topic.title,
        icon: 'topic',
        href: `/console/topics/${topic.id}`,
        dot: topicDot(topic.id),
      })),
    },
    {
      label: 'Sources',
      items: integrations.map((integration) => ({
        id: `source-${integration.id}`,
        label: integration.name,
        icon: 'source',
        href: `/console/integrations/${integration.id}`,
        dot: sourceDot(integration),
      })),
    },
  ]
}

function navIdForPath(path: string, location: ConsoleLocation): string {
  const segments = path.split('/').filter(Boolean)
  if (path === '/console') {
    return 'home'
  }
  if (path.startsWith('/console/knowledge/ask')) {
    return 'ask'
  }
  if (path.startsWith('/console/review')) {
    return 'inbox'
  }
  if (path.startsWith('/console/artifacts')) {
    return 'artifacts'
  }
  if (path.startsWith('/console/trust')) {
    return 'trust'
  }
  if (path.startsWith('/console/methodology')) {
    return 'methodology'
  }
  if (path.startsWith('/console/topics/') && segments[2]) {
    return `topic-${decodeURIComponent(segments[2])}`
  }
  if (path.startsWith('/console/integrations/') && segments[2]) {
    return `source-${decodeURIComponent(segments[2])}`
  }
  if (path.startsWith('/console/generate/')) {
    const searchParams = new URLSearchParams(location.search)
    const topicId = searchParams.get('topic')
    const sourceId = searchParams.get('source')
    if (topicId) {
      return `topic-${topicId}`
    }
    if (sourceId) {
      return `source-${sourceId}`
    }
    return 'artifacts'
  }
  return 'home'
}

function crumbsForPath(
  path: string,
  location: ConsoleLocation,
  data: ReturnType<typeof useConsoleData>['data'],
  topics: ProductTopic[],
): Crumb[] {
  const searchParams = new URLSearchParams(location.search)
  const topicId = searchParams.get('topic')
  const sourceId = searchParams.get('source')
  const topic = topics.find((item) => item.id === topicId) ?? null
  const source = (data?.integrations ?? []).find((item) => item.id === sourceId) ?? null

  if (path.startsWith('/console/knowledge/ask')) {
    return [{ label: 'Ask', strong: true }]
  }
  if (path.startsWith('/console/review')) {
    return [{ label: 'Inbox', strong: true }]
  }
  if (path.startsWith('/console/artifacts')) {
    return [{ label: 'Artifacts', strong: true }]
  }
  if (path.startsWith('/console/trust')) {
    return [{ label: 'Trust', strong: true }]
  }
  if (path.startsWith('/console/methodology')) {
    return [{ label: 'Methodology', strong: true }]
  }
  if (path.startsWith('/console/topics/')) {
    const currentTopicId = decodeURIComponent(path.split('/').filter(Boolean)[2] ?? '')
    const currentTopic = topics.find((item) => item.id === currentTopicId)
    return [
      { label: 'Topics', href: '/console/topics' },
      { label: currentTopic?.title ?? 'Topic room', strong: true },
    ]
  }
  if (path === '/console/topics') {
    return [{ label: 'Topics', strong: true }]
  }
  if (path.startsWith('/console/integrations/')) {
    const currentSourceId = decodeURIComponent(path.split('/').filter(Boolean)[2] ?? '')
    const currentSource = (data?.integrations ?? []).find((item) => item.id === currentSourceId)
    return [
      { label: 'Sources', href: '/console/integrations' },
      { label: currentSource?.name ?? 'Connector', strong: true },
    ]
  }
  if (path === '/console/integrations') {
    return [{ label: 'Sources', strong: true }]
  }
  if (path.startsWith('/console/generate/')) {
    const slug = generatorSlugFromIdentifier(path.split('/').filter(Boolean)[2])
    const title = generatorTitleFromSlug(slug)
    if (topic) {
      return [
        { label: 'Topics', href: '/console/topics' },
        { label: topic.title, href: `/console/topics/${topic.id}` },
        { label: title, strong: true },
      ]
    }
    if (source) {
      return [
        { label: 'Sources', href: '/console/integrations' },
        { label: source.name, href: `/console/integrations/${source.id}` },
        { label: title, strong: true },
      ]
    }
    return [
      { label: 'Artifacts', href: '/console/artifacts' },
      { label: title, strong: true },
    ]
  }
  return [{ label: 'Home', strong: true }]
}

function ConsoleScaffold({
  data,
  error,
  loading,
  location,
  path,
  retry,
}: {
  data: ReturnType<typeof useConsoleData>['data']
  error: string | null
  loading: boolean
  location: ConsoleLocation
  path: string
  retry: () => void
}) {
  const { openAskPalette, topics } = useConsoleWorkspace()

  useEffect(() => {
    function handleKeydown(event: KeyboardEvent) {
      if (!(event.metaKey || event.ctrlKey) || event.key.toLowerCase() !== 'k' || shouldIgnoreShortcutTarget(event.target)) {
        return
      }

      event.preventDefault()
      openAskPalette()
    }

    window.addEventListener('keydown', handleKeydown)

    return () => {
      window.removeEventListener('keydown', handleKeydown)
    }
  }, [openAskPalette])

  const navGroups = useMemo(() => navGroupsForData(data, topics), [data, topics])
  const activeNavId = useMemo(() => navIdForPath(path, location), [location, path])
  const crumbs = useMemo(() => crumbsForPath(path, location, data, topics), [data, location, path, topics])

  function handleClickCapture(event: MouseEvent<HTMLDivElement>) {
    const target = event.target
    if (!(target instanceof HTMLElement)) {
      return
    }

    const anchor = target.closest('a[href]')
    if (!(anchor instanceof HTMLAnchorElement) || !event.currentTarget.contains(anchor)) {
      return
    }

    const href = anchor.getAttribute('href')
    if (!href || !isInternalConsoleHref(href) || shouldBrowserHandleLink(event, anchor)) {
      return
    }

    event.preventDefault()
    navigateConsole(hrefForConsoleNavigation(href))
  }

  function handleSubmitCapture(event: FormEvent<HTMLDivElement>) {
    const target = event.target
    if (!(target instanceof HTMLFormElement) || !event.currentTarget.contains(target)) {
      return
    }

    const href = hrefForConsoleForm(target)
    if (!href) {
      return
    }

    event.preventDefault()
    navigateConsole(href)
  }

  return (
    <div onClickCapture={handleClickCapture} onSubmitCapture={handleSubmitCapture}>
      <AppFrame
        sidebar={<Sidebar activeId={activeNavId} groups={navGroups} />}
        topbar={
          <Topbar
            crumbs={crumbs}
            actions={
              <button className="btn btn-ghost btn-sm" onClick={() => openAskPalette()} type="button">
                <span className="kbd">Cmd/Ctrl+K</span>
                <span style={{ color: 'var(--ink-2)' }}>Ask anything</span>
              </button>
            }
          />
        }
      >
        {renderPage(path, data, loading, error, retry)}
      </AppFrame>
    </div>
  )
}

function AppShell() {
  const [location, setLocation] = useState(currentConsoleLocation)
  const { data, loading, error, retry } = useConsoleData()
  const persistTopicsToBackend = !(shouldUseDevelopmentSlice() || shouldForceDevelopmentSlice())
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
    <ConsoleWorkspaceProvider
      initialCustomTopics={data?.custom_topics}
      location={normalizedLocation}
      integrations={data?.integrations ?? []}
      persistTopicsToBackend={persistTopicsToBackend}
    >
      <ConsoleScaffold data={data} error={error} loading={loading} location={normalizedLocation} path={path} retry={retry} />
      <AskPalette />
    </ConsoleWorkspaceProvider>
  )
}

export default AppShell
