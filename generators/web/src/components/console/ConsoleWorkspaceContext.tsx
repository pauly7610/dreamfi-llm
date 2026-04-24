import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'

import { topicById, type ProductTopic } from '../../content/productTopics'
import type { ConsoleIntegration } from '../../types/console'
import type { ConsoleLocation } from '../../utils/consoleNavigation'
import { navigateConsole } from '../../utils/consoleNavigation'
import {
  recommendedGeneratorSlugForContext,
  recommendedGeneratorTitleForContext,
} from '../../utils/generatorRecommendations'

const DEFAULT_ASK_QUESTION = 'What should Product know before the next decision?'
const RECENT_ASKS_STORAGE_KEY = 'dreamfi.console.recent-asks'
const MAX_RECENT_ASKS = 5

type WorkspaceAskOptions = {
  question?: string
  sourceId?: string | null
  topicId?: string | null
}

export type RecentAsk = {
  question: string
  sourceId: string | null
  topicId: string | null
}

type ConsoleWorkspaceContextValue = {
  buildAskHref: (options?: WorkspaceAskOptions) => string
  buildGenerateHref: (slug: string, options?: WorkspaceAskOptions) => string
  closeAskPalette: () => void
  currentQuestion: string
  currentSource: ConsoleIntegration | null
  currentSourceId: string | null
  currentSourceLabel: string | null
  currentTopic: ProductTopic | null
  currentTopicId: string | null
  currentTopicLabel: string | null
  isAskPaletteOpen: boolean
  openAskPalette: (options?: WorkspaceAskOptions) => void
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

type ConsoleWorkspaceProviderProps = {
  children: ReactNode
  integrations: ConsoleIntegration[]
  location: ConsoleLocation
}

const ConsoleWorkspaceContext = createContext<ConsoleWorkspaceContextValue | null>(null)

function topicIdFromPath(path: string): string | null {
  const segments = path.split('/').filter(Boolean)
  if (segments[0] !== 'console' || segments[1] !== 'topics' || !segments[2]) {
    return null
  }

  return decodeURIComponent(segments[2])
}

function sourceIdFromPath(path: string): string | null {
  const segments = path.split('/').filter(Boolean)
  if (segments[0] !== 'console' || segments[1] !== 'integrations' || !segments[2]) {
    return null
  }

  return decodeURIComponent(segments[2])
}

function buildContextQuestion(currentQuestion: string, currentTopic: ProductTopic | null, currentSource: ConsoleIntegration | null): string {
  if (currentQuestion) {
    return currentQuestion
  }

  if (currentTopic) {
    return currentTopic.question
  }

  if (currentSource) {
    return `What should Product know from ${currentSource.name}?`
  }

  return DEFAULT_ASK_QUESTION
}

function isRecentAsk(value: unknown): value is RecentAsk {
  if (!value || typeof value !== 'object') {
    return false
  }

  const candidate = value as Partial<RecentAsk>
  return typeof candidate.question === 'string'
}

function loadRecentAsks(): RecentAsk[] {
  if (typeof window === 'undefined') {
    return []
  }

  try {
    const raw = window.localStorage.getItem(RECENT_ASKS_STORAGE_KEY)
    if (!raw) {
      return []
    }

    const parsed = JSON.parse(raw) as unknown
    if (!Array.isArray(parsed)) {
      return []
    }

    return parsed.filter(isRecentAsk).slice(0, MAX_RECENT_ASKS)
  } catch {
    return []
  }
}

function rememberAsk(recentAsks: RecentAsk[], nextAsk: RecentAsk): RecentAsk[] {
  const question = nextAsk.question.trim()
  if (!question) {
    return recentAsks
  }

  const normalizedAsk: RecentAsk = {
    question,
    topicId: nextAsk.topicId ?? null,
    sourceId: nextAsk.sourceId ?? null,
  }

  const filtered = recentAsks.filter(
    (recentAsk) =>
      !(
        recentAsk.question === normalizedAsk.question &&
        recentAsk.topicId === normalizedAsk.topicId &&
        recentAsk.sourceId === normalizedAsk.sourceId
      ),
  )

  const nextRecentAsks = [normalizedAsk, ...filtered].slice(0, MAX_RECENT_ASKS)

  if (
    nextRecentAsks.length === recentAsks.length &&
    nextRecentAsks.every(
      (recentAsk, index) =>
        recentAsk.question === recentAsks[index]?.question &&
        recentAsk.topicId === recentAsks[index]?.topicId &&
        recentAsk.sourceId === recentAsks[index]?.sourceId,
    )
  ) {
    return recentAsks
  }

  return nextRecentAsks
}

export function ConsoleWorkspaceProvider({ children, integrations, location }: ConsoleWorkspaceProviderProps) {
  const searchParams = new URLSearchParams(location.search)
  const currentQuestion = (searchParams.get('q') || '').trim()
  const currentTopicId = searchParams.get('topic') ?? topicIdFromPath(location.path)
  const currentSourceId = searchParams.get('source') ?? sourceIdFromPath(location.path)
  const currentTopic = topicById(currentTopicId)
  const currentSource = integrations.find((source) => source.id === currentSourceId) ?? null
  const defaultPaletteQuestion = buildContextQuestion(currentQuestion, currentTopic, currentSource)
  const [recentAsks, setRecentAsks] = useState<RecentAsk[]>(loadRecentAsks)
  const [isAskPaletteOpen, setIsAskPaletteOpen] = useState(false)
  const [paletteQuestion, setPaletteQuestionState] = useState(defaultPaletteQuestion)
  const [paletteTopicId, setPaletteTopicId] = useState<string | null>(currentTopicId)
  const [paletteSourceId, setPaletteSourceId] = useState<string | null>(currentSourceId)

  useEffect(() => {
    if (typeof window === 'undefined') {
      return
    }

    try {
      if (recentAsks.length > 0) {
        window.localStorage.setItem(RECENT_ASKS_STORAGE_KEY, JSON.stringify(recentAsks))
      } else {
        window.localStorage.removeItem(RECENT_ASKS_STORAGE_KEY)
      }
    } catch {
      // Ignore storage write failures in test or private browsing environments.
    }
  }, [recentAsks])

  useEffect(() => {
    if (isAskPaletteOpen) {
      return
    }

    setPaletteQuestionState(defaultPaletteQuestion)
    setPaletteTopicId(currentTopicId)
    setPaletteSourceId(currentSourceId)
  }, [location.href])

  useEffect(() => {
    if (!location.path.startsWith('/console/knowledge/ask') || !currentQuestion) {
      return
    }

    setRecentAsks((existing) =>
      rememberAsk(existing, {
        question: currentQuestion,
        topicId: currentTopicId,
        sourceId: currentSourceId,
      }),
    )
  }, [currentQuestion, currentSourceId, currentTopicId, location.path])

  function buildAskHref(options: WorkspaceAskOptions = {}): string {
    const params = new URLSearchParams()
    const question = (options.question ?? currentQuestion).trim()
    const topicId = options.topicId === undefined ? currentTopicId : options.topicId
    const sourceId = options.sourceId === undefined ? currentSourceId : options.sourceId

    if (question) {
      params.set('q', question)
    }
    if (topicId) {
      params.set('topic', topicId)
    }
    if (sourceId) {
      params.set('source', sourceId)
    }

    const search = params.toString()
    return `/console/knowledge/ask${search ? `?${search}` : ''}`
  }

  function buildGenerateHref(slug: string, options: WorkspaceAskOptions = {}): string {
    const params = new URLSearchParams()
    const question = (options.question ?? currentQuestion).trim()
    const topicId = options.topicId === undefined ? currentTopicId : options.topicId
    const sourceId = options.sourceId === undefined ? currentSourceId : options.sourceId

    if (question) {
      params.set('q', question)
    }
    if (topicId) {
      params.set('topic', topicId)
    }
    if (sourceId) {
      params.set('source', sourceId)
    }

    const search = params.toString()
    return `/console/generate/${slug}${search ? `?${search}` : ''}`
  }

  function openAskPalette(options: WorkspaceAskOptions = {}) {
    setIsAskPaletteOpen(true)
    if (options.question !== undefined) {
      setPaletteQuestionState(options.question)
    }
    if (options.topicId !== undefined) {
      setPaletteTopicId(options.topicId)
    }
    if (options.sourceId !== undefined) {
      setPaletteSourceId(options.sourceId)
    }
  }

  function closeAskPalette() {
    setIsAskPaletteOpen(false)
  }

  function setPaletteQuestion(question: string) {
    setPaletteQuestionState(question)
  }

  function reopenRecentAsk(recentAsk: RecentAsk) {
    setPaletteQuestionState(recentAsk.question)
    setPaletteTopicId(recentAsk.topicId)
    setPaletteSourceId(recentAsk.sourceId)
    setIsAskPaletteOpen(true)
  }

  function submitPaletteAsk() {
    const nextQuestion = paletteQuestion.trim() || defaultPaletteQuestion
    const nextHref = buildAskHref({
      question: nextQuestion,
      topicId: paletteTopicId,
      sourceId: paletteSourceId,
    })

    setRecentAsks((existing) =>
      rememberAsk(existing, {
        question: nextQuestion,
        topicId: paletteTopicId,
        sourceId: paletteSourceId,
      }),
    )
    setPaletteQuestionState(nextQuestion)
    setIsAskPaletteOpen(false)
    navigateConsole(nextHref)
  }

  const paletteTopic = topicById(paletteTopicId)
  const paletteSource = integrations.find((source) => source.id === paletteSourceId) ?? null
  const recommendedGeneratorSlug = recommendedGeneratorSlugForContext({
    question: currentQuestion,
    source: currentSource,
    topicId: currentTopicId,
  })
  const recommendedGeneratorTitle = recommendedGeneratorTitleForContext({
    question: currentQuestion,
    source: currentSource,
    topicId: currentTopicId,
  })

  return (
    <ConsoleWorkspaceContext.Provider
      value={{
        buildAskHref,
        buildGenerateHref,
        closeAskPalette,
        currentQuestion,
        currentSource,
        currentSourceId,
        currentSourceLabel: currentSource?.name ?? null,
        currentTopic,
        currentTopicId,
        currentTopicLabel: currentTopic?.title ?? null,
        isAskPaletteOpen,
        openAskPalette,
        paletteQuestion,
        paletteSourceId,
        paletteSourceLabel: paletteSource?.name ?? null,
        paletteTopicId,
        paletteTopicLabel: paletteTopic?.title ?? null,
        recentAsks,
        recommendedGeneratorSlug,
        recommendedGeneratorTitle,
        reopenRecentAsk,
        setPaletteQuestion,
        submitPaletteAsk,
      }}
    >
      {children}
    </ConsoleWorkspaceContext.Provider>
  )
}

export function useConsoleWorkspace(): ConsoleWorkspaceContextValue {
  const context = useContext(ConsoleWorkspaceContext)
  if (!context) {
    throw new Error('useConsoleWorkspace must be used within a ConsoleWorkspaceProvider')
  }
  return context
}
