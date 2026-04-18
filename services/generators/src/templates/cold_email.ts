/**
 * Cold Email generator template.
 *
 * Produces outreach emails optimized for reply rate: short, specific,
 * ending with a concrete question, and opening with a number or result.
 *
 * Locked criteria sourced from:
 *   autoresearch-toolkit/eval-templates/cold-email.md
 */

import type { SkillTemplate } from './types';

function countWords(text: string): number {
  return text.split(/\s+/).filter(Boolean).length;
}

export const coldEmailTemplate: SkillTemplate = {
  skillName: 'cold_email',
  skillFamily: 'outreach',
  tier: 2,
  description:
    'Generates cold outreach emails that are 75 words or fewer, reference the prospect specifically, and end with a concrete question.',

  hardGates: [
    {
      key: '75_words_or_fewer',
      description: 'The email must be 75 words or fewer.',
      check(output: string): boolean {
        return countWords(output) <= 75;
      },
    },
    {
      key: 'specific_role_company_reference',
      description:
        "The email must reference the prospect's specific role, company type, or industry.",
      check(output: string): boolean {
        // Check for capitalized proper nouns (company/person names) or
        // role-specific language beyond generic "busy professional"
        const genericPatterns =
          /\b(busy professional|your company|your team|your organization)\b/i;
        const specificPatterns =
          /\b(VP|Director|Head of|CTO|CEO|CPO|CMO|Manager|Lead|Series [A-Z]|startup|enterprise|e-commerce|fintech|SaaS|DTC|B2B|B2C)\b/i;
        const hasProperNoun = /[A-Z][a-z]+(?:\s[A-Z][a-z]+)+/.test(output);
        return (specificPatterns.test(output) || hasProperNoun) &&
          !onlyGeneric(output);
      },
    },
    {
      key: 'ends_with_concrete_question',
      description:
        'The email must end with a concrete question that invites a one-line reply.',
      check(output: string): boolean {
        const trimmed = output.trim();
        const lines = trimmed.split('\n').filter((l) => l.trim().length > 0);
        const lastLine = lines[lines.length - 1] ?? '';
        // Must end with a question mark
        if (!lastLine.trim().endsWith('?')) return false;
        // Must be concrete (contains a time, day, or specific action)
        const concretePattern =
          /\b(monday|tuesday|wednesday|thursday|friday|next week|this week|15.?min|30.?min|\d+.?minute|call|walkthrough|demo|chat|quick|brief|tuesday|tomorrow)\b/i;
        return concretePattern.test(lastLine);
      },
    },
    {
      key: 'first_two_sentences_include_number',
      description:
        'The first two sentences must include a specific number or quantified result.',
      check(output: string): boolean {
        // Extract first two sentences
        const sentences = output
          .replace(/\n/g, ' ')
          .split(/(?<=[.!?])\s+/)
          .filter(Boolean);
        const firstTwo = sentences.slice(0, 2).join(' ');
        // Must contain a digit or a number word
        const numberPattern = /\d+|hundred|thousand|million|billion|dozen/i;
        return numberPattern.test(firstTwo);
      },
    },
  ],

  formFields: [
    {
      name: 'prospectName',
      label: 'Prospect Name',
      type: 'text',
      required: true,
      placeholder: 'e.g., "Sarah Chen"',
      maxLength: 200,
    },
    {
      name: 'prospectRole',
      label: 'Prospect Role',
      type: 'text',
      required: true,
      placeholder: 'e.g., "VP Product"',
      maxLength: 200,
    },
    {
      name: 'prospectCompany',
      label: 'Prospect Company',
      type: 'text',
      required: true,
      placeholder: 'e.g., "Series B fintech startup (80 employees)"',
      maxLength: 300,
    },
    {
      name: 'industryContext',
      label: 'Industry Context',
      type: 'textarea',
      required: false,
      placeholder:
        'Any industry-specific context that makes the email more relevant.',
      maxLength: 1000,
    },
    {
      name: 'valueProposition',
      label: 'Value Proposition',
      type: 'textarea',
      required: true,
      placeholder:
        'What does your product do for this prospect? One sentence.',
      maxLength: 500,
    },
    {
      name: 'relevantMetric',
      label: 'Relevant Metric',
      type: 'text',
      required: true,
      placeholder:
        'e.g., "Cut onboarding from 14 days to 3" or "Saved $120K/year"',
      maxLength: 300,
    },
  ],

  systemPrompt: `You are a cold-email copywriter. Write a short outreach email to the prospect below.

## Prospect

**Name:** {{prospectName}}
**Role:** {{prospectRole}}
**Company:** {{prospectCompany}}
**Industry Context:** {{industryContext}}

## Your Offer

**Value Proposition:** {{valueProposition}}
**Relevant Metric:** {{relevantMetric}}

## Rules

1. Keep the email to 75 words or fewer. Every word must earn its place.
2. Reference the prospect's specific role, company, or industry in a way that shows you researched them. Never use generic language like "busy professional."
3. End the email with a concrete question that invites a one-line reply (e.g., "Would a 15-minute walkthrough next Tuesday work?"). Do NOT end with "Let me know if you're interested."
4. The first two sentences MUST include a specific number or quantified result. Do NOT use vague language like "significantly improved."

Output ONLY the email body. No subject line, no signature, no commentary.`,

  outputFormat: 'plaintext',
  wordLimit: { min: 30, max: 75 },
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Returns true when the output only contains generic prospect references
 * and no specific ones.
 */
function onlyGeneric(text: string): boolean {
  const genericOnly =
    /\b(busy professional|your company|your team|your organization)\b/i;
  const specificAny =
    /\b(VP|Director|Head of|CTO|CEO|CPO|CMO|Manager|Lead|Series [A-Z]|startup|enterprise|e-commerce|fintech|SaaS|DTC|B2B|B2C)\b/i;
  return genericOnly.test(text) && !specificAny.test(text);
}
