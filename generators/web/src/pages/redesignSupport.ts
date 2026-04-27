import type { ProductWorkflowTone } from '../content/productWorkflows'
import type { ArtifactRecord, ConsoleIntegration, IntegrationStatus } from '../types/console'
import type { ChipTone } from '../components/system/atoms'
import { generatorSlugFromIdentifier } from '../utils/consoleRoutes'

const TOPIC_SPARKS: Record<string, number[]> = {
  'funding': [3, 4, 4, 5, 4, 5, 6, 6, 7, 7, 8, 7, 8, 9],
  'kyc-conversion': [3, 4, 3, 5, 4, 3, 5, 4, 6, 5, 7, 9, 11, 11],
  'lifecycle-messaging': [4, 5, 4, 5, 6, 5, 4, 5, 4, 3, 4, 3, 3, 3],
  'onboarding': [2, 3, 3, 4, 5, 4, 4, 5, 5, 6, 5, 6, 7, 7],
}

export function topicSparkValues(topicId: string): number[] {
  return TOPIC_SPARKS[topicId] ?? [2, 3, 4, 3, 5, 4, 5, 6, 5, 6, 7, 6, 7, 8]
}

export function toneForIntegrationStatus(status: IntegrationStatus): Extract<ChipTone, 'ready' | 'warn' | 'bad'> {
  if (status === 'degraded') {
    return 'warn'
  }
  if (status === 'not_configured') {
    return 'bad'
  }
  return 'ready'
}

export function labelForIntegrationStatus(status: IntegrationStatus): string {
  if (status === 'degraded') {
    return 'lagging'
  }
  if (status === 'available') {
    return 'available'
  }
  if (status === 'not_configured') {
    return 'setup needed'
  }
  return 'fresh'
}

export function toneForWorkflowTone(tone: ProductWorkflowTone): Extract<ChipTone, 'ready' | 'warn' | 'bad'> {
  if (tone === 'blocked') {
    return 'bad'
  }
  if (tone === 'watch') {
    return 'warn'
  }
  return 'ready'
}

export function toneForArtifactStatus(status: ArtifactRecord['status']): Extract<ChipTone, 'ready' | 'warn' | 'bad'> {
  if (status === 'blocked') {
    return 'bad'
  }
  if (status === 'needs_review') {
    return 'warn'
  }
  return 'ready'
}

export function labelForArtifactStatus(status: ArtifactRecord['status']): string {
  return status.replace('_', ' ')
}

export function artifactHref(outputId: string): string {
  return `/console/review?focus=${encodeURIComponent(outputId)}`
}

export function sourceHref(sourceId: string): string {
  return `/console/integrations/${encodeURIComponent(sourceId)}`
}

export function topicHref(topicId: string): string {
  return `/console/topics/${encodeURIComponent(topicId)}`
}

export function generatorSourcesForArtifact(artifact: ArtifactRecord, integrations: ConsoleIntegration[]): ConsoleIntegration[] {
  const skillKey = generatorSlugFromIdentifier(artifact.skill_id?.replace(/_/g, '-') ?? artifact.skill_display_name ?? '')
  return integrations.filter((integration) => integration.used_for.includes(skillKey)).slice(0, 4)
}
