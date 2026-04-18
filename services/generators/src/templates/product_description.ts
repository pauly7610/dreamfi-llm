/**
 * Product Description generator template.
 *
 * Produces product descriptions that lead with the problem, include a
 * numeric result, avoid competitor comparisons, address an objection,
 * and stay within word limits.
 *
 * Locked criteria sourced from:
 *   autoresearch-toolkit/eval-templates/product-description.md
 */

import type { SkillTemplate } from './types';

function countWords(text: string): number {
  return text.split(/\s+/).filter(Boolean).length;
}

export const productDescriptionTemplate: SkillTemplate = {
  skillName: 'product_description',
  skillFamily: 'content',
  tier: 2,
  description:
    'Generates product descriptions that open with the problem, include quantified results, and close by addressing an objection.',

  hardGates: [
    {
      key: 'first_sentence_states_problem',
      description:
        'The first sentence must state the specific problem the product solves.',
      check(output: string): boolean {
        const firstSentence =
          output
            .replace(/\n/g, ' ')
            .split(/(?<=[.!?])\s+/)
            .filter(Boolean)[0] ?? '';
        // Problem indicators
        const problemPatterns =
          /\b(spend|waste|lose|struggle|drown|pain|problem|broke|fail|stuck|behind|hours|costly|expensive|frustrat|nobody|can't|don't|hard to|difficult|tedious|manual|repetitive)\b/i;
        // Anti-patterns: product-first openings
        const productFirst =
          /^(introducing|meet|welcome|announcing|presenting|we're excited|we are proud)\b/i;
        return (
          problemPatterns.test(firstSentence) &&
          !productFirst.test(firstSentence.trim())
        );
      },
    },
    {
      key: 'includes_numeric_result',
      description:
        'The description must include at least one specific customer result with a number.',
      check(output: string): boolean {
        // Look for numbers tied to outcomes
        const resultPatterns =
          /\d+\s*(%|percent|hours|days|minutes|x faster|x more|times|reduction|increase|decrease|saved|cut|grew|reduced|from \d+ to \d+)/i;
        return resultPatterns.test(output);
      },
    },
    {
      key: 'no_competitor_comparisons',
      description:
        'The description must not compare to competitors by name.',
      check(output: string): boolean {
        const comparisonPatterns =
          /\b(unlike|compared to|better than|faster than|cheaper than|vs\.?|versus|competitor|alternative to)\b/i;
        // Also check for name-drops that look like competitors
        // (This is a heuristic -- the real check happens at review time)
        return !comparisonPatterns.test(output);
      },
    },
    {
      key: 'final_paragraph_addresses_objection',
      description:
        'The final paragraph must address a specific objection (cost, setup, risk).',
      check(output: string): boolean {
        const paragraphs = output
          .split(/\n\s*\n/)
          .filter((p) => p.trim().length > 0);
        if (paragraphs.length === 0) return false;
        const lastParagraph = paragraphs[paragraphs.length - 1];
        // Objection-handling indicators
        const objectionPatterns =
          /\b(free|no credit card|cancel anytime|money.back|guarantee|setup takes|minutes to|no risk|refund|trial|worry|concern|hesitat|but what if|afraid|skeptic|wonder)\b/i;
        return objectionPatterns.test(lastParagraph);
      },
    },
    {
      key: 'word_count_100_to_200',
      description:
        'The total description must be between 100 and 200 words.',
      check(output: string): boolean {
        const wc = countWords(output);
        return wc >= 100 && wc <= 200;
      },
    },
  ],

  formFields: [
    {
      name: 'productName',
      label: 'Product Name',
      type: 'text',
      required: true,
      placeholder: 'e.g., "FocusBuds Pro"',
      maxLength: 200,
    },
    {
      name: 'problemSolved',
      label: 'Problem Solved',
      type: 'textarea',
      required: true,
      placeholder:
        'The specific problem your product solves for customers.',
      maxLength: 500,
    },
    {
      name: 'targetCustomer',
      label: 'Target Customer',
      type: 'text',
      required: true,
      placeholder:
        'e.g., "Remote workers in noisy home environments"',
      maxLength: 300,
    },
    {
      name: 'keyResult',
      label: 'Key Quantified Result',
      type: 'text',
      required: true,
      placeholder:
        'e.g., "Reduced checkout abandonment by 18%"',
      maxLength: 300,
    },
    {
      name: 'commonObjection',
      label: 'Common Objection',
      type: 'text',
      required: true,
      placeholder:
        'The biggest reason prospects hesitate (e.g., "setup complexity", "price")',
      maxLength: 300,
    },
    {
      name: 'mainFeatures',
      label: 'Main Features',
      type: 'textarea',
      required: true,
      placeholder:
        'List 3-5 key features with brief descriptions.',
      maxLength: 1000,
    },
  ],

  systemPrompt: `You are a product copywriter. Write a product description for the product below.

## Product Details

**Product Name:** {{productName}}
**Problem Solved:** {{problemSolved}}
**Target Customer:** {{targetCustomer}}
**Key Quantified Result:** {{keyResult}}
**Common Objection:** {{commonObjection}}
**Main Features:** {{mainFeatures}}

## Rules

1. The FIRST sentence must state the specific problem the product solves. Do NOT open with "Introducing..." or "Meet..." -- lead with the pain.
2. Include at least one specific customer result with a number (e.g., "Reduced onboarding from 14 days to 3"). No vague claims like "customers love it."
3. Do NOT compare to competitors by name. Describe the product on its own merits.
4. The LAST paragraph must address the most common objection head-on (cost, setup time, risk, etc.).
5. Keep the total description between 100 and 200 words.

Output the description in markdown. No commentary or metadata.`,

  outputFormat: 'markdown',
  wordLimit: { min: 100, max: 200 },
};
