import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

import type { ConsoleIntegration } from '../../types/console'
import type { ConsoleLocation } from '../../utils/consoleNavigation'
import { navigateConsole } from '../../utils/consoleNavigation'
import {
  recommendedGeneratorSlugForContext,
  recommendedGeneratorTitleForContext,
} from '../../utils/generatorRecommendations'
import AskPalette from './AskPalette'

type ConsoleWorkspaceProviderProps = {
  children: ReactNode
  integrations: ConsoleIntegration[]
  location: ConsoleLocation
}

type ContextOptions = {
  question?: string | null
  sourceId?: string | null
  topicId?: string | null
}

type RecentAsk = {
  question: string
  sourceId: string | null
  topicId: string | null
}

type ConsoleWorkspaceContextValue = {
  buildAskHref: (options?: ContextOptions) => string
  buildGenerateHref: (slug: string, options?: ContextOptions) => string
  closeAskPalette: () => void
  currentQuestion: string
  currentSourceId: string | null
  currentSourceLabel: string | null
  currentTopicId: string | null
  currentTopicLabel: string | null
  isAskPaletteOpen: boolean
  openAskPalette: (options?: ContextOptions) => void
  paletteQuestion: string
  paletteSourceId: string | null
  paletteSourceLabel: string | null
  paletteTopicId: string | null
  paletteTopicLabel: string | null
  recentAsks: RecentAsk[]
  recommendedGeneratorSlug: string
  recommendedGeneratorTitle: string
  reopenRecentAsk: (recentAsk: RecentAsk) => void
  setPaletteQuestion: (question: string) => void
  submitPaletteAsk: () => void
}

const RECENT_ASK_STORAGE_KEY = 'dreamfi.console.recent-asks'

const ConsoleWorkspaceContext = createContext<ConsoleWorkspaceContextValue | null>(null)

function normalizeQuestion(question: string | null | undefined): string {
  return (question ?? '').trim()
}

function askContextFromLocation(location: ConsoleLocation) {
  const searchParams = new URLSearchParams(location.search)
  const segments = location.path.split('/').filter(Boolean)
  const topicFromPath = segments[0] === 'console' && segments[1] === 'topics' && segments[2]
    ? decodeURIComponent(segments[2])
    : null
  const sourceFromPath = segments[0] === 'console' && segments[1] === 'integrations' && segments[2]
    ? decodeURIComponent(segments[2])
    : null

  return {
    question: normalizeQuestion(searchParams.get('q')),
    sourceId: searchParams.get('source') ?? sourceFromPath,
    topicId: searchParams.get('topic') ?? topicFromPath,
  }
}

function contextSearch(options: ContextOptions): string {
  const params = new URLSearchParams()
  const question = normalizeQuestion(options.question)

  if (question) {
    params.set('q', question)
  }
  if (options.topicId) {
    params.set('topic', options.topicId)
  }
  if (options.sourceId) {
    params.set('source', options.sourceId)
  }

  const query = params.toString()
  return query ? `?${query}` : ''
}

function readRecentAsks(): RecentAsk[] {
  if (typeof window === 'undefined') {
    return []
  }

  try {
    const stored = window.localStorage.getItem(RECENT_ASK_STORAGE_KEY)
    if (!stored) {
      return []
    }

    const parsed = JSON.parse(stored) as RecentAsk[]
    return parsed.filter((entry) => typeof entry.question === 'string' && entry.question.trim().length > 0)
  } catch {
    return []
  }
}

function upsertRecentAsk(recentAsks: RecentAsk[], recentAsk: RecentAsk): RecentAsk[] {
  const question = normalizeQuestion(recentAsk.question)
  if (!question) {
    return recentAsks
  }

  const normalizedAsk = {
    question,
    sourceId: recentAsk.sourceId,
    topicId: recentAsk.topicId,
  }

  return [normalizedAsk, ...recentAsks.filter((entry) => (
    entry.question !== normalizedAsk.question ||
    entry.topicId !== normalizedAsk.topicId ||
    entry.sourceId !== normalizedAsk.sourceId
  ))].slice(0, 5)
}

export function ConsoleWorkspaceProvider({ children, integrations, location }: ConsoleWorkspaceProviderProps) {
  const currentContext = useMemo(() => askContextFromLocation(location), [location.path, location.search])
  const [recentAsks, setRecentAsks] = useState<RecentAsk[]>(() => readRecentAsks())
  const [isAskPaletteOpen, setIsAskPaletteOpen] = useState(false)
  const [paletteQuestion, setPaletteQuestion] = useState(currentContext.question)
  const [paletteTopicId, setPaletteTopicId] = useState<string | null>(currentContext.topicId)
  const [paletteSourceId, setPaletteSourceId] = useState<string | null>(currentContext.sourceId)

  const currentSource = useMemo(
    () => integrations.find((integration) => integration.id === currentContext.sourceId) ?? null,
    [currentContext.sourceId, integrations],
  )
  const paletteSource = useMemo(
    () => integrations.find((integration) => integration.id === paletteSourceId) ?? null,
    [integrations, paletteSourceId],
  )
  const currentTopic = useMemo(
    () => currentContext.topicId ? integrations.length >= 0 ? undefined : undefined : undefined,
    [currentContext.topicId, integrations.length],
  )

  useEffect(() => {
    if (typeof window === 'undefined') {
      return
    }

    window.localStorage.setItem(RECENT_ASK_STORAGE_KEY, JSON.stringify(recentAsks))
  }, [recentAsks])

  useEffect(() => {
    if (location.path !== '/console/knowledge/ask' || !currentContext.question) {
      return
    }

    setRecentAsks((existing) => upsertRecentAsk(existing, {
      question: currentContext.question,
      topicId: currentContext.topicId,
      sourceId: currentContext.sourceId,
    }))
  }, [currentContext.question, currentContext.sourceId, currentContext.topicId, location.path])

  useEffect(() => {
    if (isAskPaletteOpen) {
      return
    }

    setPaletteQuestion(currentContext.question)
    setPaletteTopicId(currentContext.topicId)
    setPaletteSourceId(currentContext.sourceId)
  }, [currentContext.question, currentContext.sourceId, currentContext.topicId, isAskPaletteOpen])

  function buildAskHref(options: ContextOptions = {}): string {
    return `/console/knowledge/ask${contextSearch({
      question: options.question ?? currentContext.question,
      topicId: options.topicId ?? currentContext.topicId,
      sourceId: options.sourceId ?? currentContext.sourceId,
    })}`
  }

  function buildGenerateHref(slug: string, options: ContextOptions = {}): string {
    return `/console/generate/${slug}${contextSearch({
      question: options.question ?? currentContext.question,
      topicId: options.topicId ?? currentContext.topicId,
      sourceId: options.sourceId ?? currentContext.sourceId,
    })}`
  }

  function openAskPalette(options: ContextOptions = {}) {
    setIsAskPaletteOpen(true)

    if (options.question !== undefined) {
      setPaletteQuestion(options.question ?? '')
    } else if (!paletteQuestion && currentContext.question) {
      setPaletteQuestion(currentContext.question)
    }

    if (options.topicId !== undefined) {
      setPaletteTopicId(options.topicId)
    } else if (paletteTopicId === null && currentContext.topicId) {
      setPaletteTopicId(currentContext.topicId)
    }

    if (options.sourceId !== undefined) {
      setPaletteSourceId(options.sourceId)
    } else if (paletteSourceId === null && currentContext.sourceId) {
      setPaletteSourceId(currentContext.sourceId)
    }
  }

  function closeAskPalette() {
    setIsAskPaletteOpen(false)
  }

  function submitPaletteAsk() {
    navigateConsole(buildAskHref({
      question: paletteQuestion,
      topicId: paletteTopicId,
      sourceId: paletteSourceId,
    }))
    setIsAskPaletteOpen(false)
  }

  function reopenRecentAsk(recentAsk: RecentAsk) {
    setPaletteQuestion(recentAsk.question)
    setPaletteTopicId(recentAsk.topicId)
    setPaletteSourceId(recentAsk.sourceId)
    navigateConsole(buildAskHref(recentAsk))
    setIsAskPaletteOpen(false)
  }

  const recommendedGeneratorSlug = recommendedGeneratorSlugForContext({
    topicId: currentContext.topicId,
    source: currentSource,
  })
  const recommendedGeneratorTitle = recommendedGeneratorTitleForContext({
    topicId: currentContext.topicId,
    source: currentSource,
  })

  const value = useMemo<ConsoleWorkspaceContextValue>(() => ({
    buildAskHref,
    buildGenerateHref,
    closeAskPalette,
    currentQuestion: currentContext.question,
    currentSourceId: currentContext.sourceId,
    currentSourceLabel: currentSource?.name ?? null,
    currentTopicId: currentContext.topicId,
    currentTopicLabel: currentContext.topicId,
    isAskPaletteOpen,
    openAskPalette,
    paletteQuestion,
    paletteSourceId,
    paletteSourceLabel: paletteSource?.name ?? null,
    paletteTopicId,
    paletteTopicLabel: paletteTopicId,
    recentAsks,
    recommendedGeneratorSlug,
    recommendedGeneratorTitle,
    reopenRecentAsk,
    setPaletteQuestion,
    submitPaletteAsk,
  }), [
    closeAskPalette,
    currentContext.question,
    currentContext.sourceId,
    currentContext.topicId,
    currentSource?.name,
    isAskPaletteOpen,
    openAskPalette,
    paletteQuestion,
    paletteSource?.name,
    paletteSourceId,
    paletteTopicId,
    recentAsks,
    recommendedGeneratorSlug,
    recommendedGeneratorTitle,
  ])

  return (
    <ConsoleWorkspaceContext.Provider value={value}>
      {children}
      <AskPalette />
    </ConsoleWorkspaceContext.Provider>
  )
}

export function useConsoleWorkspace() {
  const context = useContext(ConsoleWorkspaceContext)
  if (!context) {
    throw new Error('useConsoleWorkspace must be used within ConsoleWorkspaceProvider')
  }
  return context
}
