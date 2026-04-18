/**
 * Agent System Prompt generator template.
 *
 * Produces system prompts for AI agents that are accurate, grounded,
 * concise, and correctly handle out-of-scope requests.
 *
 * Locked criteria sourced from:
 *   autoresearch-toolkit/eval-templates/agent-system-prompt.md
 */

import type { SkillTemplate } from './types';

// ---------------------------------------------------------------------------
// Word-count helpers
// ---------------------------------------------------------------------------

function countWords(text: string): number {
  return text.split(/\s+/).filter(Boolean).length;
}

// ---------------------------------------------------------------------------
// Template
// ---------------------------------------------------------------------------

export const agentSystemPromptTemplate: SkillTemplate = {
  skillName: 'agent_system_prompt',
  skillFamily: 'internal',
  tier: 1,
  description:
    'Generates system prompts for AI agents that correctly identify intent, avoid hallucination, and provide actionable next steps.',

  hardGates: [
    {
      key: 'correct_intent_first_response',
      description:
        'The agent must correctly identify the user intent on the first response without unnecessary clarifying questions.',
      check(output: string): boolean {
        // Gate passes when the output does NOT begin with a clarifying question
        // pattern while the input contains a clear, specific request.
        // Heuristic: output should contain an imperative/instructional sentence
        // and should not open with "What", "Which", "Could you clarify".
        const firstLine = output.split('\n').filter(Boolean)[0] ?? '';
        const clarifyPatterns =
          /^(what|which|could you clarify|can you clarify|do you mean)/i;
        return !clarifyPatterns.test(firstLine.trim());
      },
    },
    {
      key: 'no_unsupported_claims',
      description:
        'The response must not fabricate information that is not present in the provided context.',
      check(output: string): boolean {
        // Heuristic: passes when the output contains hedging/grounding
        // language OR does not contain absolute assertions about policies,
        // prices, or deadlines without a citation marker.
        const fabricationSignals =
          /\b(our (policy|guarantee) (is|states|requires))\b/i;
        const groundingSignals =
          /\b(based on|according to|per the|from the knowledge base|I don't have)\b/i;
        // If output makes policy claims, it must also show grounding
        if (fabricationSignals.test(output)) {
          return groundingSignals.test(output);
        }
        return true;
      },
    },
    {
      key: 'specific_next_action',
      description:
        'The response must include a specific, actionable next step for the user.',
      check(output: string): boolean {
        const actionPatterns =
          /\b(click|go to|navigate|open|select|tap|visit|call|email|send|submit|contact|check|review|follow)\b/i;
        return actionPatterns.test(output);
      },
    },
    {
      key: 'under_80_words',
      description: 'The response must be 80 words or fewer.',
      check(output: string): boolean {
        return countWords(output) <= 80;
      },
    },
    {
      key: 'clear_refusal_on_impossible',
      description:
        'For impossible or out-of-scope requests the agent must refuse clearly rather than guessing.',
      check(output: string): boolean {
        // Heuristic: if the output references transferring/escalating/not
        // having info, it should do so explicitly rather than attempting
        // a guess. We check for the presence of clear refusal language
        // when limitation indicators are present.
        const limitationIndicators =
          /\b(don't have|cannot|unable to|not available|outside|beyond)\b/i;
        const guessIndicators =
          /\b(I think|maybe|perhaps|I'm not sure but)\b.*\b(try|might work)\b/i;
        if (guessIndicators.test(output)) {
          return false;
        }
        // If there are limitation signals, they should be accompanied by
        // redirect language
        if (limitationIndicators.test(output)) {
          const redirectSignals =
            /\b(transfer|connect|escalate|reach out|contact|refer)\b/i;
          return redirectSignals.test(output);
        }
        return true;
      },
    },
  ],

  formFields: [
    {
      name: 'systemContext',
      label: 'System Context',
      type: 'textarea',
      required: true,
      placeholder:
        'Describe the system the agent operates in (product, domain, constraints).',
      maxLength: 2000,
    },
    {
      name: 'intendedUsers',
      label: 'Intended Users',
      type: 'text',
      required: true,
      placeholder: 'e.g., "Customer support callers for a SaaS billing product"',
      maxLength: 500,
    },
    {
      name: 'capabilityScope',
      label: 'Capability Scope',
      type: 'textarea',
      required: true,
      placeholder:
        'List what the agent CAN do (e.g., reset passwords, look up invoices).',
      maxLength: 2000,
    },
    {
      name: 'toneGuidelines',
      label: 'Tone Guidelines',
      type: 'textarea',
      required: false,
      placeholder:
        'Describe the desired voice (friendly, formal, concise, etc.).',
      maxLength: 1000,
    },
    {
      name: 'knownLimitations',
      label: 'Known Limitations',
      type: 'textarea',
      required: true,
      placeholder:
        'List what the agent CANNOT do and how it should handle those requests.',
      maxLength: 2000,
    },
  ],

  systemPrompt: `You are a system-prompt generator for AI agents.

Given the following inputs, produce a production-ready system prompt that the agent will use at runtime.

## Inputs

**System Context:**
{{systemContext}}

**Intended Users:**
{{intendedUsers}}

**Capability Scope:**
{{capabilityScope}}

**Tone Guidelines:**
{{toneGuidelines}}

**Known Limitations:**
{{knownLimitations}}

## Requirements

1. The system prompt MUST instruct the agent to identify the user's intent on the very first response -- no unnecessary clarifying questions.
2. The agent MUST only reference information present in its provided context. Include an explicit instruction to refuse rather than fabricate.
3. Every response the agent produces MUST end with a specific, concrete next action for the user (a link, a button, a step).
4. The system prompt itself MUST be under 80 words. Be ruthlessly concise.
5. Include a clear instruction for how the agent should handle requests outside its capability scope -- it must refuse clearly and redirect to the right team.

Output ONLY the system prompt text. No commentary, no preamble.`,

  outputFormat: 'markdown',
  wordLimit: { min: 20, max: 80 },
};
