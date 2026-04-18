/**
 * Newsletter Headline generator template.
 *
 * Produces email subject lines and preview text optimized for open rate:
 * includes a number, stays under 50 chars, creates a knowledge gap
 * without clickbait, and adds new info in the preview.
 *
 * Locked criteria sourced from:
 *   autoresearch-toolkit/eval-templates/newsletter-headline.md
 */

import type { SkillTemplate } from './types';

export const newsletterHeadlineTemplate: SkillTemplate = {
  skillName: 'newsletter_headline',
  skillFamily: 'content',
  tier: 2,
  description:
    'Generates newsletter subject lines and preview text optimized for open rate with number, curiosity gap, and additive preview.',

  hardGates: [
    {
      key: 'subject_includes_number',
      description: 'The subject line must include a specific number.',
      check(output: string): boolean {
        const subject = extractSubjectLine(output);
        if (!subject) return false;
        return /\d+/.test(subject);
      },
    },
    {
      key: 'under_50_chars',
      description: 'The subject line must be under 50 characters.',
      check(output: string): boolean {
        const subject = extractSubjectLine(output);
        if (!subject) return false;
        return subject.length < 50;
      },
    },
    {
      key: 'knowledge_gap_without_clickbait',
      description:
        'The subject must create a knowledge gap without being clickbait.',
      check(output: string): boolean {
        const subject = extractSubjectLine(output);
        if (!subject) return false;
        // Clickbait indicators
        const clickbaitPatterns =
          /\b(you won't believe|shocking|mind-blowing|jaw-dropping|insane|unbelievable|must see|this will|OMG|WOW|!!)\b/i;
        // Curiosity indicators: numbers, results, before/after, specific claims
        const curiosityPatterns =
          /\b(\d+%|\d+ to \d+|how|why|what|the \w+ that|secret|mistake|lesson)\b/i;
        // Must NOT have clickbait
        if (clickbaitPatterns.test(subject)) return false;
        // Should have at least some curiosity signal
        return curiosityPatterns.test(subject) || /\d/.test(subject);
      },
    },
    {
      key: 'preview_adds_new_info',
      description:
        'The preview text must add new information not present in the subject line.',
      check(output: string): boolean {
        const subject = extractSubjectLine(output);
        const preview = extractPreviewText(output);
        if (!subject || !preview) return false;
        // Extract significant words (4+ chars) from each
        const subjectWords = new Set(
          subject
            .toLowerCase()
            .split(/\W+/)
            .filter((w) => w.length >= 4),
        );
        const previewWords = preview
          .toLowerCase()
          .split(/\W+/)
          .filter((w) => w.length >= 4);
        // Preview should have at least 2 significant words not in the subject
        const newWords = previewWords.filter((w) => !subjectWords.has(w));
        return newWords.length >= 2;
      },
    },
  ],

  formFields: [
    {
      name: 'topic',
      label: 'Article Topic',
      type: 'textarea',
      required: true,
      placeholder:
        'Describe the article or newsletter content in 2-3 sentences.',
      maxLength: 1000,
    },
    {
      name: 'keyInsight',
      label: 'Key Insight',
      type: 'text',
      required: true,
      placeholder:
        'The single most compelling takeaway (e.g., "41% to 92% in 4 rounds")',
      maxLength: 300,
    },
    {
      name: 'targetNumber',
      label: 'Target Number',
      type: 'text',
      required: true,
      placeholder:
        'The specific number to include in the subject (e.g., "6", "41%", "$1B")',
      maxLength: 100,
    },
    {
      name: 'audienceContext',
      label: 'Audience Context',
      type: 'text',
      required: false,
      placeholder:
        'Who reads this newsletter? (e.g., "PMs and founders")',
      maxLength: 300,
    },
  ],

  systemPrompt: `You are a newsletter headline writer. Produce a subject line and preview text that maximize open rate.

## Content

**Topic:** {{topic}}
**Key Insight:** {{keyInsight}}
**Target Number:** {{targetNumber}}
**Audience:** {{audienceContext}}

## Rules

1. The subject line MUST include a specific number. "6 PM Use Cases for Autoresearch" not "How to Use Autoresearch."
2. The subject line MUST be under 50 characters total. Count carefully.
3. Create a knowledge gap that makes the reader curious WITHOUT clickbait. No "You won't BELIEVE..." or "SHOCKING..." language.
4. The preview text MUST add new, substantive information that is NOT in the subject line. Not a rephrasing -- genuinely new context.

Output format:
Subject: [your subject line]
Preview: [your preview text]

No other commentary.`,

  outputFormat: 'plaintext',
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Extracts the subject line from structured output. */
function extractSubjectLine(text: string): string | null {
  const match = text.match(/^subject:\s*(.+)$/im);
  if (match) return match[1].trim();
  // Fallback: first non-empty line
  const firstLine = text.split('\n').filter((l) => l.trim().length > 0)[0];
  return firstLine?.trim() ?? null;
}

/** Extracts the preview text from structured output. */
function extractPreviewText(text: string): string | null {
  const match = text.match(/^preview:\s*(.+)$/im);
  if (match) return match[1].trim();
  // Fallback: second non-empty line
  const lines = text.split('\n').filter((l) => l.trim().length > 0);
  return lines.length >= 2 ? lines[1].trim() : null;
}
