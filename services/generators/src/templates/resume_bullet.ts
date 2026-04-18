/**
 * Resume Bullet generator template.
 *
 * Produces achievement-oriented resume bullets that start with a strong
 * past-tense verb, include a quantified result, stay concise, and tie
 * to a business outcome.
 *
 * Locked criteria sourced from:
 *   autoresearch-toolkit/eval-templates/resume-bullet.md
 */

import type { SkillTemplate } from './types';

function countWords(text: string): number {
  return text.split(/\s+/).filter(Boolean).length;
}

// ---------------------------------------------------------------------------
// Strong past-tense verbs vs. weak openers
// ---------------------------------------------------------------------------

const STRONG_VERBS = new Set([
  'shipped',
  'reduced',
  'grew',
  'led',
  'designed',
  'migrated',
  'launched',
  'built',
  'implemented',
  'increased',
  'decreased',
  'eliminated',
  'automated',
  'negotiated',
  'secured',
  'delivered',
  'restructured',
  'optimized',
  'accelerated',
  'achieved',
  'created',
  'developed',
  'drove',
  'expanded',
  'improved',
  'orchestrated',
  'pioneered',
  'revamped',
  'scaled',
  'spearheaded',
  'streamlined',
  'transformed',
  'unified',
  'overhauled',
  'consolidated',
  'established',
  'generated',
  'initiated',
  'integrated',
  'architected',
  'defined',
  'doubled',
  'tripled',
  'cut',
  'saved',
  'won',
  'closed',
]);

const WEAK_OPENERS = new Set([
  'responsible',
  'helped',
  'involved',
  'worked',
  'assisted',
  'participated',
  'contributed',
  'supported',
  'managed',
]);

export const resumeBulletTemplate: SkillTemplate = {
  skillName: 'resume_bullet',
  skillFamily: 'content',
  tier: 3,
  description:
    'Generates resume bullets with strong verbs, quantified results, under 25 words, tied to business outcomes.',

  hardGates: [
    {
      key: 'strong_past_tense_verb',
      description:
        'The bullet must start with a strong past-tense action verb (not "Responsible for", "Helped with", etc.).',
      check(output: string): boolean {
        const firstWord = output.trim().split(/\s+/)[0]?.toLowerCase().replace(/[^a-z]/g, '') ?? '';
        // Must not start with a weak opener
        if (WEAK_OPENERS.has(firstWord)) return false;
        // Should start with a recognized strong verb or at least end in -ed/-t
        // (catches verbs not in our list)
        return (
          STRONG_VERBS.has(firstWord) ||
          firstWord.endsWith('ed') ||
          firstWord.endsWith('ied')
        );
      },
    },
    {
      key: 'quantified_result',
      description: 'The bullet must include a specific quantified result.',
      check(output: string): boolean {
        const numberPattern =
          /\d+\s*(%|percent|x|hours|days|minutes|months|weeks|users|customers|employees|K|M|k|m|\$|points|pp)/i;
        const rangePattern = /from\s+\d+\s*\w*\s+to\s+\d+/i;
        return numberPattern.test(output) || rangePattern.test(output);
      },
    },
    {
      key: 'under_25_words',
      description: 'The bullet must be one sentence under 25 words.',
      check(output: string): boolean {
        // Take the first sentence / the whole thing if single sentence
        const cleaned = output.trim().replace(/^[-•*]\s*/, '');
        return countWords(cleaned) <= 25;
      },
    },
    {
      key: 'tied_to_business_outcome',
      description:
        'The bullet must connect the action to a business outcome (revenue, retention, cost savings, growth).',
      check(output: string): boolean {
        const outcomePatterns =
          /\b(revenue|retention|churn|cost|savings|ARR|MRR|conversion|acquisition|NPS|engagement|growth|profit|margin|pipeline|deals|quota|efficiency|productivity|satisfaction|adoption)\b/i;
        const dollarPattern = /\$[\d,.]+[KkMmBb]?/;
        return outcomePatterns.test(output) || dollarPattern.test(output);
      },
    },
  ],

  formFields: [
    {
      name: 'role',
      label: 'Role / Title',
      type: 'text',
      required: true,
      placeholder: 'e.g., "Senior PM at a B2B SaaS company"',
      maxLength: 200,
    },
    {
      name: 'achievement',
      label: 'Achievement',
      type: 'textarea',
      required: true,
      placeholder:
        'Describe what you did and the result (e.g., "Led dashboard redesign that improved enterprise retention")',
      maxLength: 1000,
    },
    {
      name: 'metric',
      label: 'Quantified Metric',
      type: 'text',
      required: true,
      placeholder:
        'e.g., "from 0.3 to 0.7 K-factor" or "reduced churn by 23%"',
      maxLength: 200,
    },
    {
      name: 'context',
      label: 'Context',
      type: 'textarea',
      required: false,
      placeholder:
        'Team size, timeline, tools, or other relevant context.',
      maxLength: 500,
    },
  ],

  systemPrompt: `You are a resume-bullet writer for PM and tech roles. Write a single achievement bullet.

## Inputs

**Role:** {{role}}
**Achievement:** {{achievement}}
**Metric:** {{metric}}
**Context:** {{context}}

## Rules

1. Start with a strong past-tense action verb: Shipped, Reduced, Grew, Led, Designed, Migrated, Launched, Built, etc. NEVER start with "Responsible for", "Helped with", "Was involved in", or "Worked on."
2. Include a specific quantified result with a number: "from 12K to 45K", "by 18%", "saving $340K." NEVER use "significantly" or "greatly."
3. Keep it to ONE sentence, under 25 words. Ruthlessly cut filler.
4. Connect the action to a business outcome: revenue, retention, cost savings, growth, efficiency. "Built an onboarding flow using React" is NOT enough -- tie it to the result.

Output ONLY the single bullet point. No dash, no bullet character, no commentary.`,

  outputFormat: 'plaintext',
  wordLimit: { min: 8, max: 25 },
};
