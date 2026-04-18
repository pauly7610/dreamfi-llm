/**
 * Short-Form Script generator template.
 *
 * Produces video scripts (TikTok, Reels, Shorts) optimized for retention:
 * curiosity-gap opener, surprising claim, single narrative thread,
 * controlled read time, and next-content hook.
 *
 * Locked criteria sourced from:
 *   autoresearch-toolkit/eval-templates/short-form-script.md
 */

import type { SkillTemplate } from './types';

function countWords(text: string): number {
  return text.split(/\s+/).filter(Boolean).length;
}

/** Approximate read time in seconds at ~150 words per minute. */
function readTimeSeconds(text: string): number {
  return (countWords(text) / 150) * 60;
}

export const shortFormScriptTemplate: SkillTemplate = {
  skillName: 'short_form_script',
  skillFamily: 'content',
  tier: 3,
  description:
    'Generates short-form video scripts with a curiosity-gap opener, single narrative thread, and next-content hook.',

  hardGates: [
    {
      key: 'curiosity_gap_first_5_words',
      description:
        'The opening line must create a specific curiosity gap within the first 5 words.',
      check(output: string): boolean {
        const firstLine = output.split('\n').filter((l) => l.trim().length > 0)[0] ?? '';
        const firstFiveWords = firstLine.trim().split(/\s+/).slice(0, 5).join(' ');
        // Fail patterns: generic greetings
        const genericOpeners =
          /^(hey guys|hi everyone|so today|welcome back|what's up|hello|in this video)/i;
        if (genericOpeners.test(firstFiveWords)) return false;
        // Curiosity indicators: numbers, money, surprising claims, "this"
        const curiositySignals =
          /\b(this \$?\d|the \w+ that|I \w+ my|nobody|everyone|most|worst|best|\$\d|one \w+ changed|stop)\b/i;
        return curiositySignals.test(firstFiveWords) || /\d/.test(firstFiveWords);
      },
    },
    {
      key: 'surprising_claim_early',
      description:
        'There must be a surprising or counterintuitive claim in the first 2 sentences.',
      check(output: string): boolean {
        const sentences = output
          .replace(/\n/g, ' ')
          .split(/(?<=[.!?])\s+/)
          .filter(Boolean);
        const firstTwo = sentences.slice(0, 2).join(' ');
        // Surprising/counterintuitive signals
        const surprisePatterns =
          /\b(worst|best|never|nobody|everyone gets wrong|counterintuitive|surprising|opposite|actually|myth|lie|secret|mistake|replaced|killed|broke|hack)\b/i;
        const contrastPatterns =
          /\b(but|yet|instead|however|not what you think|turns out)\b/i;
        return (
          surprisePatterns.test(firstTwo) || contrastPatterns.test(firstTwo)
        );
      },
    },
    {
      key: 'single_narrative_thread',
      description:
        'The script must follow a single narrative thread from start to finish.',
      check(output: string): boolean {
        // Heuristic: fail if the script has multiple distinct numbered tips
        // or list items that suggest a listicle format
        const tipPattern = /^(tip|step|\d+[.):])\s/im;
        const tipMatches = output.match(
          /^(tip|step|\d+[.):])\s/gim,
        );
        // More than 2 list-style items suggests a listicle, not a narrative
        if (tipMatches && tipMatches.length > 2) return false;
        // Also check for "first... second... third..." pattern
        const transitionCount = (
          output.match(/\b(first|second|third|fourth|next tip|another)\b/gi) || []
        ).length;
        return transitionCount <= 2;
      },
    },
    {
      key: 'under_90_seconds_read_time',
      description:
        'The script must be under 90 seconds when read at natural pace (~150 words/minute).',
      check(output: string): boolean {
        return readTimeSeconds(output) <= 90;
      },
    },
    {
      key: 'ends_with_next_content_hook',
      description:
        'The script must end with a hook that drives to the next piece of content.',
      check(output: string): boolean {
        const lines = output.split('\n').filter((l) => l.trim().length > 0);
        const lastTwo = lines.slice(-2).join(' ');
        // Next-content hooks
        const hookPatterns =
          /\b(part \d|next|tomorrow|follow|link|bio|comment|full (video|episode|guide|breakdown)|deep dive|stay tuned|subscribe|podcast|YouTube|newsletter)\b/i;
        // Anti-patterns: generic sign-offs
        const genericEndings =
          /\b(hope that was helpful|like and subscribe|thanks for watching|see you next time|bye)\b/i;
        if (genericEndings.test(lastTwo)) return false;
        return hookPatterns.test(lastTwo);
      },
    },
  ],

  formFields: [
    {
      name: 'topic',
      label: 'Topic',
      type: 'textarea',
      required: true,
      placeholder:
        'What is the script about? Include the core idea in 1-2 sentences.',
      maxLength: 1000,
    },
    {
      name: 'hook',
      label: 'Opening Hook',
      type: 'text',
      required: true,
      placeholder:
        'The first line the viewer hears (e.g., "This $3 tool replaced my $500/month stack")',
      maxLength: 200,
    },
    {
      name: 'surprisingFact',
      label: 'Surprising Fact',
      type: 'text',
      required: true,
      placeholder:
        'A counterintuitive or surprising claim to anchor the script.',
      maxLength: 300,
    },
    {
      name: 'narrative',
      label: 'Narrative Arc',
      type: 'textarea',
      required: true,
      placeholder:
        'The story structure: setup, tension, resolution. One thread only.',
      maxLength: 2000,
    },
    {
      name: 'callToAction',
      label: 'Call to Action',
      type: 'text',
      required: true,
      placeholder:
        'Where should the viewer go next? (e.g., "Part 2 drops tomorrow", "Full breakdown on YouTube")',
      maxLength: 300,
    },
  ],

  systemPrompt: `You are a short-form video scriptwriter. Write a script for TikTok / Reels / Shorts.

## Inputs

**Topic:** {{topic}}
**Opening Hook:** {{hook}}
**Surprising Fact:** {{surprisingFact}}
**Narrative Arc:** {{narrative}}
**Call to Action:** {{callToAction}}

## Rules

1. The FIRST 5 WORDS must create a specific curiosity gap. Never open with "Hey guys", "So today", or "Welcome back."
2. The first 2 sentences must contain a surprising or counterintuitive claim. "Product management is important" is NOT surprising. "The worst PMs write the best PRDs" IS.
3. Follow ONE narrative thread from start to finish. Do NOT give a list of tips. Build one idea with escalating stakes.
4. Keep the script under 90 seconds at a natural reading pace (~150 words per minute). That means roughly 200-225 words maximum.
5. End with a specific hook to the NEXT piece of content: "Part 2 covers...", "Full breakdown linked in bio", etc. Do NOT end with "Hope that was helpful" or "Like and subscribe."

Output ONLY the script text as the speaker would read it aloud. No stage directions, no timestamps, no commentary.`,

  outputFormat: 'markdown',
  wordLimit: { min: 100, max: 225 },
};
