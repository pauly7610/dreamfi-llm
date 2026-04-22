import type { ConsoleIntegration } from '../types/console'
import type { SourceDataPreview } from './sourcePreviewTypes'

export function defaultSourcePreview(source: ConsoleIntegration): SourceDataPreview {
  return {
    headline: `${source.name} source data preview`,
    description: source.purpose,
    freshness: 'Available in the development source room',
    primaryDataset: `${source.name} workspace`,
    rows: [
      {
        label: 'Connected context',
        value: source.status === 'connected' ? 'Live' : 'Ready',
        detail: 'DreamFi can use this source when gathering evidence for product work.',
      },
      {
        label: 'Artifact coverage',
        value: String(source.used_for.length),
        detail: 'Number of generator workflows that can cite this connector.',
      },
      {
        label: 'Review path',
        value: 'Cited answers',
        detail: 'Answers should show where this source was used before publishing.',
      },
    ],
    inspect: [
      {
        title: 'What this source is good for',
        detail: source.purpose,
      },
      {
        title: 'What DreamFi should verify',
        detail: 'Connector-specific answers should stay grounded in receipts, freshness, and explicit caveats.',
      },
      {
        title: 'How Product should use it',
        detail: 'Use this source to support product questions, then promote the best answers into generated artifacts.',
      },
    ],
    workflows: [
      {
        title: `Ask about ${source.name}`,
        detail: 'Start with a grounded question using this connector as the primary scope.',
        href: `/console/knowledge/ask?source=${source.id}&q=${encodeURIComponent(`What should Product know from ${source.name}?`)}`,
      },
    ],
    views: ['Connector overview', 'Evidence coverage', 'Generator usage'],
    questions: [
      `What should Product know from ${source.name}?`,
      `Which generated artifacts use ${source.name}?`,
      `Where should ${source.name} evidence appear in a brief?`,
    ],
  }
}
