/**
 * Meeting Summary generator template.
 *
 * Produces structured meeting summaries with distinct sections for
 * decisions, action items (with owners and deadlines), and open questions.
 *
 * Locked criteria sourced from:
 *   autoresearch-toolkit/eval-templates/meeting-summary.md
 */

import type { SkillTemplate } from './types';

function countWords(text: string): number {
  return text.split(/\s+/).filter(Boolean).length;
}

export const meetingSummaryTemplate: SkillTemplate = {
  skillName: 'meeting_summary',
  skillFamily: 'internal',
  tier: 1,
  description:
    'Generates concise meeting summaries with labeled decisions, owner+deadline action items, and open questions.',

  hardGates: [
    {
      key: 'action_items_have_owner_and_deadline',
      description:
        'Every action item must include a specific owner name and a deadline.',
      check(output: string): boolean {
        // Find lines that look like action items
        const actionItemPatterns = [
          /action item/i,
          /\b(TODO|task|action)\b/i,
          /^[-*]\s/m,
        ];
        const lines = output.split('\n');
        const actionSection = findSection(output, [
          'action items',
          'actions',
          'next steps',
          'tasks',
        ]);
        if (!actionSection) {
          // No action section at all -- cannot validate. Treat as pass if
          // there truly are no action items to capture.
          return true;
        }
        const sectionLines = actionSection
          .split('\n')
          .filter((l) => l.trim().startsWith('-') || l.trim().startsWith('*'));
        if (sectionLines.length === 0) return true;
        // Each action line must contain a name-like word and a date/day reference
        const ownerPattern = /[A-Z][a-z]+/; // capitalized name
        const deadlinePattern =
          /\b(by|before|due|deadline|monday|tuesday|wednesday|thursday|friday|saturday|sunday|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|\d{1,2}\/\d{1,2}|\d{4}-\d{2}-\d{2}|end of week|end of day|eod|eow|tomorrow|next week)\b/i;
        return sectionLines.every(
          (line) => ownerPattern.test(line) && deadlinePattern.test(line),
        );
      },
    },
    {
      key: 'decisions_labeled',
      description:
        'Decisions must be stated as decisions, not discussion summaries.',
      check(output: string): boolean {
        const decisionSection = findSection(output, ['decision', 'decisions']);
        if (!decisionSection) {
          // If no decision section exists but the summary mentions a decision,
          // that is a structural fail handled by the sections gate.
          return true;
        }
        // Check that items in the section use declarative language
        const discussionPatterns =
          /\b(discussed|talked about|considered|debated)\b/i;
        const decisionPatterns =
          /\b(decided|agreed|approved|confirmed|will|chosen|selected|go with)\b/i;
        const items = decisionSection
          .split('\n')
          .filter((l) => l.trim().length > 0 && !l.trim().startsWith('#'));
        if (items.length === 0) return true;
        // At least one item must use decision language, and none should
        // be purely discussion summaries
        const hasDecisionLanguage = items.some((l) =>
          decisionPatterns.test(l),
        );
        const purelyDiscussion = items.every(
          (l) => discussionPatterns.test(l) && !decisionPatterns.test(l),
        );
        return hasDecisionLanguage && !purelyDiscussion;
      },
    },
    {
      key: 'distinct_sections',
      description:
        'The summary must have distinct sections for decisions, action items, and open questions.',
      check(output: string): boolean {
        const lower = output.toLowerCase();
        const hasDecisions =
          /#{1,3}\s*(decision|decisions)/i.test(output) ||
          lower.includes('**decision');
        const hasActions =
          /#{1,3}\s*(action item|action items|actions|next steps)/i.test(
            output,
          ) || lower.includes('**action');
        const hasQuestions =
          /#{1,3}\s*(open question|open questions|unresolved|open items)/i.test(
            output,
          ) || lower.includes('**open question');
        return hasDecisions && hasActions && hasQuestions;
      },
    },
    {
      key: 'open_questions_as_questions',
      description:
        'Open questions must be stated as actual questions, not vague topic labels.',
      check(output: string): boolean {
        const questionSection = findSection(output, [
          'open question',
          'open questions',
          'unresolved',
          'open items',
        ]);
        if (!questionSection) return true;
        const items = questionSection
          .split('\n')
          .filter(
            (l) =>
              (l.trim().startsWith('-') || l.trim().startsWith('*')) &&
              l.trim().length > 3,
          );
        if (items.length === 0) return true;
        // Every item should contain a question mark
        return items.every((l) => l.includes('?'));
      },
    },
    {
      key: 'under_300_words',
      description: 'The summary must be 300 words or fewer.',
      check(output: string): boolean {
        return countWords(output) <= 300;
      },
    },
  ],

  formFields: [
    {
      name: 'meetingTitle',
      label: 'Meeting Title',
      type: 'text',
      required: true,
      placeholder: 'e.g., "Q2 Roadmap Review"',
      maxLength: 200,
    },
    {
      name: 'attendees',
      label: 'Attendees',
      type: 'textarea',
      required: true,
      placeholder: 'List all attendees (one per line or comma-separated).',
      maxLength: 1000,
    },
    {
      name: 'rawNotes',
      label: 'Raw Meeting Notes',
      type: 'textarea',
      required: true,
      placeholder:
        'Paste the raw transcript, notes, or bullet points from the meeting.',
      maxLength: 10000,
    },
    {
      name: 'meetingType',
      label: 'Meeting Type',
      type: 'select',
      required: true,
      placeholder: 'Select the meeting type',
      options: [
        'Product Review',
        'Sprint Planning',
        'Standup',
        '1:1',
        'Cross-Functional',
        'All Hands',
        'Leadership',
        'Retrospective',
        'Other',
      ],
    },
    {
      name: 'previousActionItems',
      label: 'Previous Action Items',
      type: 'textarea',
      required: false,
      placeholder:
        'Paste action items from the previous meeting to track follow-up.',
      maxLength: 3000,
    },
  ],

  systemPrompt: `You are a meeting-summary generator. Given raw meeting notes, produce a structured summary.

## Meeting Details

**Title:** {{meetingTitle}}
**Type:** {{meetingType}}
**Attendees:** {{attendees}}

## Raw Notes
{{rawNotes}}

## Previous Action Items
{{previousActionItems}}

## Output Requirements

1. Every action item MUST include a specific person's name as the owner AND a concrete deadline (date or day of week). Never write "Team to follow up."
2. State decisions as decisions, not as discussion summaries. Write "Decision: We will launch to 500 users on April 1" not "The team discussed launching to a subset."
3. Organize the summary into three distinct sections with clear headers: **Decisions**, **Action Items**, **Open Questions**.
4. State every open question as an actual question ending with "?" -- never as a vague topic label.
5. Keep the entire summary under 300 words regardless of meeting length.

Output the summary in markdown. No preamble or commentary.`,

  outputFormat: 'markdown',
  wordLimit: { min: 50, max: 300 },
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Extracts the text content of a markdown section identified by any of the
 * given heading keywords. Returns null if no matching section is found.
 */
function findSection(
  text: string,
  headingKeywords: string[],
): string | null {
  const lines = text.split('\n');
  let capturing = false;
  let captured: string[] = [];

  for (const line of lines) {
    const isHeading = /^#{1,3}\s+/.test(line) || /^\*\*[^*]+\*\*/.test(line);
    if (isHeading) {
      const lower = line.toLowerCase();
      if (headingKeywords.some((kw) => lower.includes(kw))) {
        capturing = true;
        captured = [];
        continue;
      } else if (capturing) {
        break; // hit the next section
      }
    }
    if (capturing) {
      captured.push(line);
    }
  }

  return captured.length > 0 ? captured.join('\n') : null;
}
