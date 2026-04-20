import type { ArtifactRecord } from '../../types/console'

export function formatScore(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return '—'
  }
  return value.toFixed(3)
}

export function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return '—'
  }
  return `${Math.round(value * 100)}%`
}

export function formatDate(value: string | null | undefined): string {
  if (!value) {
    return 'Pending'
  }
  return new Intl.DateTimeFormat('en', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit'
  }).format(new Date(value))
}

export function formatArtifactStatus(status: ArtifactRecord['status']): string {
  if (status === 'publish_ready') {
    return 'Publish ready'
  }
  if (status === 'needs_review') {
    return 'Needs review'
  }
  return status.charAt(0).toUpperCase() + status.slice(1)
}
