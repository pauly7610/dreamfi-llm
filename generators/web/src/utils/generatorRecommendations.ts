import { topicById } from '../content/productTopics'
import type { ConsoleIntegration } from '../types/console'
import { generatorSlugFromIdentifier, generatorTitleFromSlug } from './consoleRoutes'

type GeneratorRecommendationOptions = {
  source?: ConsoleIntegration | null
  topicId?: string | null
}

export function recommendedGeneratorSlugForContext({ source, topicId }: GeneratorRecommendationOptions): string {
  const topic = topicById(topicId ?? null)
  if (topic?.defaultGeneratorSlug) {
    return topic.defaultGeneratorSlug
  }

  if (source?.used_for.length) {
    return generatorSlugFromIdentifier(source.used_for[0])
  }

  return 'weekly-brief'
}

export function recommendedGeneratorTitleForContext(options: GeneratorRecommendationOptions): string {
  return generatorTitleFromSlug(recommendedGeneratorSlugForContext(options))
}
