import type { ProductTopic } from '../content/productTopics'
import { topicById } from '../content/productTopics'
import type { ConsoleIntegration } from '../types/console'
import { generatorSlugFromIdentifier, generatorTitleFromSlug } from './consoleRoutes'

type GeneratorRecommendationOptions = {
  question?: string | null
  source?: ConsoleIntegration | null
  topic?: ProductTopic | null
  topicId?: string | null
}

function fallbackGeneratorSlugForQuestion(question: string | null | undefined): string {
  const normalizedQuestion = question?.trim().toLowerCase() ?? ''

  if (!normalizedQuestion) {
    return 'weekly-brief'
  }

  if (/(risk|fraud|kyc|identity|policy|review)/.test(normalizedQuestion)) {
    return 'risk-brd'
  }

  if (/(brief|weekly|summary|update|what changed)/.test(normalizedQuestion)) {
    return 'weekly-brief'
  }

  if (/(campaign|lifecycle|messaging|growth|business|market)/.test(normalizedQuestion)) {
    return 'business-prd'
  }

  if (/(launch|delivery|technical|flow|onboarding|funding|integration)/.test(normalizedQuestion)) {
    return 'technical-prd'
  }

  return 'weekly-brief'
}

export function recommendedGeneratorSlugForContext({ question, source, topic, topicId }: GeneratorRecommendationOptions): string {
  const scopedTopic = topic ?? topicById(topicId ?? null)
  if (scopedTopic?.defaultGeneratorSlug) {
    return scopedTopic.defaultGeneratorSlug
  }

  if (source?.used_for.length) {
    return generatorSlugFromIdentifier(source.used_for[0])
  }

  if (source) {
    if (source.category === 'risk' || source.category === 'identity') {
      return 'risk-brd'
    }

    if (source.category === 'marketing' || source.category === 'marketing_analytics') {
      return 'business-prd'
    }

    if (source.category === 'planning' || source.category === 'payments' || source.category === 'product_analytics') {
      return 'technical-prd'
    }
  }

  return fallbackGeneratorSlugForQuestion(question)
}

export function recommendedGeneratorTitleForContext(options: GeneratorRecommendationOptions): string {
  return generatorTitleFromSlug(recommendedGeneratorSlugForContext(options))
}
