/**
 * Support Agent generator template.
 *
 * Produces customer-support agent responses optimized for first-response
 * resolution, knowledge-base grounding, and correct escalation.
 *
 * Locked criteria sourced from:
 *   autoresearch-toolkit/eval-templates/support-agent.md
 */

import type { SkillTemplate } from './types';

function countWords(text: string): number {
  return text.split(/\s+/).filter(Boolean).length;
}

export const supportAgentTemplate: SkillTemplate = {
  skillName: 'support_agent',
  skillFamily: 'internal',
  tier: 1,
  description:
    'Generates support-agent responses that resolve issues using only KB content, escalate correctly, and stay concise.',

  hardGates: [
    {
      key: 'resolve_when_possible',
      description:
        'The response must resolve the issue directly when resolution is possible from the knowledge base.',
      check(output: string): boolean {
        // Fail if the response escalates when it contains resolution steps
        const escalatePattern =
          /\b(transfer|escalate|connect you with|specialist|another team)\b/i;
        const resolutionPattern =
          /\b(step \d|here's how|to fix this|you can|follow these)\b/i;
        // If both are present, the resolution content indicates the agent
        // could have resolved without escalating -- still a pass since
        // escalation may be additive. Only fail if ONLY escalation with no
        // resolution steps when resolution language is expected.
        if (escalatePattern.test(output) && !resolutionPattern.test(output)) {
          // Might be a correct escalation -- check for escalation-worthy signals
          const escalationTopics =
            /\b(security|compromise|legal|over \$500|account breach)\b/i;
          return escalationTopics.test(output);
        }
        return true;
      },
    },
    {
      key: 'only_kb_information',
      description:
        'The response must only reference information from the knowledge base, never fabricate policies or processes.',
      check(output: string): boolean {
        const fabricationSignals =
          /\b(I believe|I think|typically|usually|in most cases|probably)\b/i;
        const groundingSignals =
          /\b(per our|according to|our records show|based on|knowledge base|your account)\b/i;
        if (fabricationSignals.test(output) && !groundingSignals.test(output)) {
          return false;
        }
        return true;
      },
    },
    {
      key: 'three_or_fewer_messages',
      description:
        'Resolution must happen in 3 or fewer messages -- no excessive clarifying questions.',
      check(output: string): boolean {
        // Count question marks as a proxy for clarifying questions
        const questionCount = (output.match(/\?/g) || []).length;
        // More than 3 questions suggests the agent is over-clarifying
        return questionCount <= 3;
      },
    },
    {
      key: 'escalate_correctly',
      description:
        'The agent must escalate billing disputes over $500, account security issues, and legal requests.',
      check(output: string): boolean {
        const securityTopic =
          /\b(accessed my account|changed my email|compromised|unauthorized|breach|hacked)\b/i;
        const escalationPresent =
          /\b(escalat|transfer|security team|specialist|dedicated team)\b/i;
        // If input contains a security topic, output should escalate
        if (securityTopic.test(output)) {
          return escalationPresent.test(output);
        }
        return true;
      },
    },
    {
      key: 'under_120_words',
      description: 'The response must be 120 words or fewer.',
      check(output: string): boolean {
        return countWords(output) <= 120;
      },
    },
  ],

  formFields: [
    {
      name: 'customerIssue',
      label: 'Customer Issue',
      type: 'textarea',
      required: true,
      placeholder:
        'Paste the customer message or describe the issue they reported.',
      maxLength: 3000,
    },
    {
      name: 'productArea',
      label: 'Product Area',
      type: 'select',
      required: true,
      placeholder: 'Select the product area',
      options: [
        'Billing',
        'Account Management',
        'Technical Support',
        'Onboarding',
        'Feature Requests',
        'Security',
        'Other',
      ],
    },
    {
      name: 'kbContext',
      label: 'Knowledge Base Context',
      type: 'textarea',
      required: true,
      placeholder:
        'Paste relevant knowledge base articles or sections the agent should reference.',
      maxLength: 5000,
    },
    {
      name: 'escalationRules',
      label: 'Escalation Rules',
      type: 'textarea',
      required: true,
      placeholder:
        'Define when the agent should escalate instead of resolving (e.g., billing disputes over $500, security incidents).',
      maxLength: 2000,
    },
    {
      name: 'previousInteractions',
      label: 'Previous Interactions',
      type: 'textarea',
      required: false,
      placeholder:
        'Paste any prior messages in this conversation thread for context.',
      maxLength: 5000,
    },
  ],

  systemPrompt: `You are a customer support agent. Respond to the customer issue below using ONLY the provided knowledge base context.

## Customer Issue
{{customerIssue}}

## Product Area
{{productArea}}

## Knowledge Base Context
{{kbContext}}

## Escalation Rules
{{escalationRules}}

## Previous Interactions
{{previousInteractions}}

## Rules

1. RESOLVE the issue directly when the knowledge base contains the answer. Provide specific steps, not vague advice.
2. ONLY use information from the knowledge base context above. Do not invent policies, processes, deadlines, or prices.
3. Keep your response to 3 or fewer exchanges. Do not ask unnecessary clarifying questions when the issue is clear.
4. ESCALATE when the issue matches an escalation rule. State the reason and the team the customer will be connected to.
5. Stay under 120 words. Be concise and actionable.

Output ONLY the support response. No metadata, no internal notes.`,

  outputFormat: 'markdown',
  wordLimit: { min: 20, max: 120 },
};
