/**
 * Landing Page Copy generator template.
 *
 * Produces conversion-optimized landing page copy: headline with numbers,
 * no buzzwords, outcome-tied CTA, pain-point opening, controlled length.
 *
 * Locked criteria sourced from:
 *   autoresearch-toolkit/eval-templates/landing-page-copy.md
 */

import type { SkillTemplate } from './types';

function countWords(text: string): number {
  return text.split(/\s+/).filter(Boolean).length;
}

// ---------------------------------------------------------------------------
// Banned buzzword list (locked -- never modify)
// ---------------------------------------------------------------------------

export const BANNED_BUZZWORDS: readonly string[] = [
  'revolutionary',
  'game-changing',
  'best-in-class',
  'cutting-edge',
  'world-class',
  'synergy',
  'leverage',
  'disrupt',
  'innovative',
  'next-gen',
  'next-level',
  'transform',
  'streamline',
  'empower',
  'seamless',
  'robust',
  'scalable',
  'holistic',
  'unlock',
] as const;

export const landingPageCopyTemplate: SkillTemplate = {
  skillName: 'landing_page_copy',
  skillFamily: 'content',
  tier: 2,
  description:
    'Generates landing page copy with a number-driven headline, no buzzwords, outcome-tied CTA, and pain-point-first structure.',

  hardGates: [
    {
      key: 'headline_includes_number',
      description:
        'The headline must include a specific number or measurable result.',
      check(output: string): boolean {
        const headline = extractHeadline(output);
        if (!headline) return false;
        return /\d+/.test(headline);
      },
    },
    {
      key: 'no_banned_buzzwords',
      description:
        'The copy must be completely free of banned buzzwords.',
      check(output: string): boolean {
        const lower = output.toLowerCase();
        return !BANNED_BUZZWORDS.some((bw) => {
          // Match whole words only to avoid false positives
          const regex = new RegExp(`\\b${escapeRegex(bw)}\\b`, 'i');
          return regex.test(lower);
        });
      },
    },
    {
      key: 'cta_tied_to_outcome',
      description:
        'The CTA must use a specific action verb tied to the product outcome, not generic "Learn More" or "Get Started".',
      check(output: string): boolean {
        const genericCTAs =
          /\b(learn more|get started|sign up|start now|try it|click here|see more|find out|discover)\b/i;
        const outcomeVerbs =
          /\b(save|cut|reduce|boost|grow|start saving|start cutting|stop|eliminate|automate|ship|launch)\b/i;
        // Find CTA-like elements (buttons, strong calls to action at end)
        const lines = output.split('\n').filter((l) => l.trim().length > 0);
        const lastThird = lines.slice(Math.floor(lines.length * 0.66));
        const ctaArea = lastThird.join(' ');
        if (genericCTAs.test(ctaArea) && !outcomeVerbs.test(ctaArea)) {
          return false;
        }
        return outcomeVerbs.test(ctaArea);
      },
    },
    {
      key: 'first_sentence_states_pain_point',
      description:
        'The first sentence after the headline must name a specific pain point the reader experiences.',
      check(output: string): boolean {
        const body = extractBodyAfterHeadline(output);
        if (!body) return false;
        const firstSentence = body.split(/(?<=[.!?])\s+/)[0] ?? '';
        // Pain point indicators: negative emotion, cost, time waste, frustration
        const painPatterns =
          /\b(spend|waste|lose|struggle|drown|pain|problem|broke|fail|stuck|behind|hours|costly|expensive|frustrat|nobody reads|can't|don't know)\b/i;
        // Anti-pattern: generic "in today's" openers
        const genericOpeners =
          /^in today's|^in the modern|^in a world|^welcome to/i;
        return (
          painPatterns.test(firstSentence) &&
          !genericOpeners.test(firstSentence.trim())
        );
      },
    },
    {
      key: 'word_count_80_to_150',
      description: 'The total copy must be between 80 and 150 words.',
      check(output: string): boolean {
        const wc = countWords(output);
        return wc >= 80 && wc <= 150;
      },
    },
  ],

  formFields: [
    {
      name: 'productName',
      label: 'Product Name',
      type: 'text',
      required: true,
      placeholder: 'e.g., "StatusBot"',
      maxLength: 200,
    },
    {
      name: 'targetAudience',
      label: 'Target Audience',
      type: 'text',
      required: true,
      placeholder:
        'e.g., "Engineering managers at 50-500 person companies"',
      maxLength: 300,
    },
    {
      name: 'mainPainPoint',
      label: 'Main Pain Point',
      type: 'textarea',
      required: true,
      placeholder:
        'The specific problem your audience has that your product solves.',
      maxLength: 500,
    },
    {
      name: 'keyBenefit',
      label: 'Key Benefit',
      type: 'textarea',
      required: true,
      placeholder:
        'The primary benefit -- what changes for the customer?',
      maxLength: 500,
    },
    {
      name: 'quantifiedResult',
      label: 'Quantified Result',
      type: 'text',
      required: true,
      placeholder:
        'e.g., "Saves 10+ hours per week" or "Reduced churn by 23%"',
      maxLength: 200,
    },
    {
      name: 'desiredAction',
      label: 'Desired Action (CTA)',
      type: 'text',
      required: true,
      placeholder:
        'What you want the visitor to do, tied to an outcome (e.g., "Start saving 10 hours")',
      maxLength: 200,
    },
  ],

  systemPrompt: `You are a landing-page copywriter. Write conversion-optimized copy for the product below.

## Product Details

**Product Name:** {{productName}}
**Target Audience:** {{targetAudience}}
**Main Pain Point:** {{mainPainPoint}}
**Key Benefit:** {{keyBenefit}}
**Quantified Result:** {{quantifiedResult}}
**Desired CTA:** {{desiredAction}}

## Rules

1. The headline MUST include a specific number or measurable result. "Save 10 Hours Per Week" not "Transform Your Workflow."
2. Do NOT use any of these banned buzzwords: revolutionary, game-changing, best-in-class, cutting-edge, world-class, synergy, leverage, disrupt, innovative, next-gen, next-level, transform, streamline, empower, seamless, robust, scalable, holistic, unlock.
3. The CTA must use a specific action verb tied to the product outcome. NOT "Learn More" or "Get Started."
4. The first sentence after the headline must name a specific pain point the reader actually experiences. NOT "In today's fast-paced world."
5. Keep total copy between 80 and 150 words.

Output the copy in markdown format: headline as H1, body paragraphs, CTA as a bold call to action. No commentary.`,

  outputFormat: 'markdown',
  wordLimit: { min: 80, max: 150 },
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Extracts the first H1 or the first line as the headline. */
function extractHeadline(text: string): string | null {
  const h1Match = text.match(/^#\s+(.+)$/m);
  if (h1Match) return h1Match[1];
  const firstLine = text.split('\n').filter((l) => l.trim().length > 0)[0];
  return firstLine ?? null;
}

/** Extracts body text after the first headline. */
function extractBodyAfterHeadline(text: string): string | null {
  const lines = text.split('\n');
  let pastHeadline = false;
  const body: string[] = [];
  for (const line of lines) {
    if (!pastHeadline) {
      if (line.startsWith('#') || (body.length === 0 && line.trim().length > 0)) {
        pastHeadline = true;
        continue;
      }
    } else {
      if (line.trim().length > 0) {
        body.push(line);
      }
    }
  }
  return body.length > 0 ? body.join(' ') : null;
}

/** Escapes special regex characters in a string. */
function escapeRegex(str: string): string {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}
