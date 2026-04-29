import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'

import { productTopics, type ProductTopic } from '../../content/productTopics'
import { shouldForceDevelopmentSlice, shouldUseDevelopmentSlice } from '../../content/consoleDevelopmentSlice'
import type { ConsoleIntegration, ConsoleTopicRecord } from '../../types/console'
import type { ConsoleLocation } from '../../utils/consoleNavigation'
import { navigateConsole } from '../../utils/consoleNavigation'
import {
  recommendedGeneratorSlugForContext,
  recommendedGeneratorTitleForContext,
} from '../../utils/generatorRecommendations'
import { generatorTitleFromSlug } from '../../utils/consoleRoutes'

const DEFAULT_ASK_QUESTION = 'What should Product know before the next decision?'
const RECENT_ASKS_STORAGE_KEY = 'dreamfi.console.recent-asks'
const CUSTOM_TOPICS_STORAGE_KEY = 'dreamfi.console.custom-topics'
const MAX_RECENT_ASKS = 5

type WorkspaceAskOptions = {
  question?: string
  sourceId?: string | null
  topicId?: string | null
}

export type CreateTopicInput = {
  defaultGeneratorSlug?: string
  question: string
  sourceIds: string[]
  summary?: string
  title: string
}

export type RecentAsk = {
  question: string
  sourceId: string | null
  topicId: string | null
}

type StoredCustomTopic = ConsoleTopicRecord

type ConsoleWorkspaceContextValue = {
  addTopic: (input: CreateTopicInput) => Promise<ProductTopic>
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
  topicById: (topicId: string | null) => ProductTopic | null
  topics: ProductTopic[]
  topicsForSource: (sourceId: string) => ProductTopic[]
}

type ConsoleWorkspaceProviderProps = {
  children: ReactNode
  initialCustomTopics?: StoredCustomTopic[]
  integrations: ConsoleIntegration[]
  location: ConsoleLocation
  persistTopicsToBackend?: boolean
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

function ensureQuestionMark(question: string): string {
  const trimmed = question.trim()
  if (!trimmed) {
    return DEFAULT_ASK_QUESTION
  }

  return /[?.!]$/.test(trimmed) ? trimmed : `${trimmed}?`
}

function topicSummaryForTitle(title: string, summary: string): string {
  const trimmedSummary = summary.trim()
  if (trimmedSummary) {
    return trimmedSummary
  }

  return `Track ${title.toLowerCase()} across the connected product evidence.`
}

function normalizeSourceIds(sourceIds: string[]): string[] {
  return Array.from(new Set(sourceIds.map((sourceId) => sourceId.trim()).filter(Boolean)))
}

function defaultArtifactTitles(defaultGeneratorSlug: string): string[] {
  return Array.from(
    new Set([
      generatorTitleFromSlug(defaultGeneratorSlug),
      'Weekly PM Brief',
    ]),
  )
}

function isStoredCustomTopic(value: unknown): value is StoredCustomTopic {
  if (!value || typeof value !== 'object') {
    return false
  }

  const candidate = value as Partial<StoredCustomTopic>
  return (
    typeof candidate.id === 'string' &&
    typeof candidate.title === 'string' &&
    typeof candidate.summary === 'string' &&
    typeof candidate.question === 'string' &&
    typeof candidate.default_generator_slug === 'string' &&
    typeof candidate.created_at === 'string' &&
    Array.isArray(candidate.source_ids) &&
    candidate.source_ids.every((sourceId) => typeof sourceId === 'string')
  )
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

function loadCustomTopics(): StoredCustomTopic[] {
  if (typeof window === 'undefined') {
    return []
  }

  try {
    const raw = window.localStorage.getItem(CUSTOM_TOPICS_STORAGE_KEY)
    if (!raw) {
      return []
    }

    const parsed = JSON.parse(raw) as unknown
    if (!Array.isArray(parsed)) {
      return []
    }

    return parsed.filter(isStoredCustomTopic)
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

function createTopicId(title: string, existingTopics: ProductTopic[]): string {
  const baseId =
    title
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '') || 'new-topic'

  let candidateId = baseId
  let suffix = 2
  while (existingTopics.some((topic) => topic.id === candidateId)) {
    candidateId = `${baseId}-${suffix}`
    suffix += 1
  }

  return candidateId
}

function buildCustomTopic(topic: StoredCustomTopic, integrations: ConsoleIntegration[]): ProductTopic {
  const sourceIds = normalizeSourceIds(topic.source_ids)
  const sourceIntegrations = sourceIds
    .map((sourceId) => integrations.find((integration) => integration.id === sourceId) ?? null)
    .filter((integration): integration is ConsoleIntegration => Boolean(integration))
    .slice(0, 3)

  const toplineMetrics = sourceIntegrations.length > 0
    ? sourceIntegrations.map((integration) => ({
        label: integration.name,
        value: integration.status === 'degraded' ? 'Watch' : integration.status === 'not_configured' ? 'Setup' : 'Connected',
        detail: integration.purpose,
        sourceId: integration.id,
      }))
    : [
        {
          label: 'Signals linked',
          value: '0',
          detail: 'Pick at least one connector to ground this room.',
        },
      ]

  const signals = sourceIntegrations.length > 0
    ? sourceIntegrations.map((integration) => ({
        label: `${integration.name} signal`,
        value: integration.status === 'degraded' ? 'Needs attention' : integration.status === 'not_configured' ? 'Setup needed' : 'Fresh',
        detail: `Use ${integration.name} for ${integration.purpose.toLowerCase()}.`,
        sourceId: integration.id,
      }))
    : [
        {
          label: 'Next step',
          value: 'Add grounding',
          detail: 'Choose one or more connected systems before you publish decisions from this room.',
        },
      ]

  return {
    id: topic.id,
    title: topic.title.trim(),
    summary: topicSummaryForTitle(topic.title, topic.summary),
    question: ensureQuestionMark(topic.question),
    sources: sourceIds,
    artifacts: defaultArtifactTitles(topic.default_generator_slug),
    defaultGeneratorSlug: topic.default_generator_slug,
    toplineMetrics,
    signals,
    gaps: [
      `Confirm owners, KPI definitions, and source freshness before publishing decisions from ${topic.title}.`,
    ],
  }
}

export function ConsoleWorkspaceProvider({
  children,
  initialCustomTopics,
  integrations,
  location,
  persistTopicsToBackend = !(shouldUseDevelopmentSlice() || shouldForceDevelopmentSlice()),
}: ConsoleWorkspaceProviderProps) {
  const searchParams = new URLSearchParams(location.search)
  const [customTopics, setCustomTopics] = useState<StoredCustomTopic[]>(
    () => initialCustomTopics ?? (persistTopicsToBackend ? [] : loadCustomTopics()),
  )
  const topics = [...customTopics.map((topic) => buildCustomTopic(topic, integrations)), ...productTopics]
  const currentQuestion = (searchParams.get('q') || '').trim()
  const currentTopicId = searchParams.get('topic') ?? topicIdFromPath(location.path)
  const currentSourceId = searchParams.get('source') ?? sourceIdFromPath(location.path)
  const topicById = (topicId: string | null): ProductTopic | null => {
    if (!topicId) {
      return null
    }

    return topics.find((topic) => topic.id === topicId) ?? null
  }
  const topicsForSource = (sourceId: string): ProductTopic[] => topics.filter((topic) => topic.sources.includes(sourceId))
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
    if (typeof window === 'undefined') {
      return
    }

    if (persistTopicsToBackend) {
      return
    }

    try {
      if (customTopics.length > 0) {
        window.localStorage.setItem(CUSTOM_TOPICS_STORAGE_KEY, JSON.stringify(customTopics))
      } else {
        window.localStorage.removeItem(CUSTOM_TOPICS_STORAGE_KEY)
      }
    } catch {
      // Ignore storage write failures in test or private browsing environments.
    }
  }, [customTopics, persistTopicsToBackend])

  useEffect(() => {
    if (!persistTopicsToBackend) {
      return
    }

    setCustomTopics(initialCustomTopics ?? [])
  }, [initialCustomTopics, persistTopicsToBackend])

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

  async function addTopic(input: CreateTopicInput): Promise<ProductTopic> {
    const title = input.title.trim() || 'New topic'
    const sourceIds = normalizeSourceIds(input.sourceIds)
    const defaultGeneratorSlug = input.defaultGeneratorSlug?.trim() || 'weekly-brief'
    const candidateTopic: StoredCustomTopic = {
      id: createTopicId(title, topics),
      title,
      summary: topicSummaryForTitle(title, input.summary ?? ''),
      question: ensureQuestionMark(input.question),
      source_ids: sourceIds,
      default_generator_slug: defaultGeneratorSlug,
      created_at: new Date().toISOString(),
    }

    if (!persistTopicsToBackend) {
      setCustomTopics((existing) => [candidateTopic, ...existing.filter((topic) => topic.id !== candidateTopic.id)])
      return buildCustomTopic(candidateTopic, integrations)
    }

    const response = await fetch('/api/console/topics', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        id: candidateTopic.id,
        title: candidateTopic.title,
        summary: candidateTopic.summary,
        question: candidateTopic.question,
        source_ids: candidateTopic.source_ids,
        default_generator_slug: candidateTopic.default_generator_slug,
      }),
    })

    if (!response.ok) {
      let detail = `Unable to save topic (${response.status})`
      try {
        const payload = (await response.json()) as { detail?: string }
        if (payload.detail) {
          detail = payload.detail
        }
      } catch {
        // Ignore response parsing failures and use the default message.
      }
      throw new Error(detail)
    }

    const storedTopic = (await response.json()) as StoredCustomTopic
    setCustomTopics((existing) => [storedTopic, ...existing.filter((topic) => topic.id !== storedTopic.id)])
    return buildCustomTopic(storedTopic, integrations)
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
    topic: currentTopic,
    topicId: currentTopicId,
  })
  const recommendedGeneratorTitle = recommendedGeneratorTitleForContext({
    question: currentQuestion,
    source: currentSource,
    topic: currentTopic,
    topicId: currentTopicId,
  })

  return (
    <ConsoleWorkspaceContext.Provider
      value={{
        addTopic,
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
        topicById,
        topics,
        topicsForSource,
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
