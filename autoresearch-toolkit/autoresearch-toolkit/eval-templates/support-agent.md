# Evaluation Criteria: Support Agent

Optimizes: First-response resolution, hallucination prevention, and escalation accuracy.

## Criteria

C1: Does the response resolve the issue without escalating (when resolution is possible)?
  PASS: Provides the specific steps to fix the problem using knowledge base content
  FAIL: "Let me transfer you to a specialist" for a question the knowledge base covers

C2: Does the response reference ONLY information from the knowledge base?
  PASS: Quotes or paraphrases specific knowledge base articles
  FAIL: Invents a policy, deadline, or process not in the knowledge base

C3: Does resolution happen in 3 or fewer messages?
  PASS: Issue resolved in 1-2 messages
  FAIL: Agent asks 4 clarifying questions before providing any help

C4: Does the agent escalate correctly when it should?
  PASS: Billing disputes over $500, account security issues, and legal requests get escalated
  FAIL: Agent tries to handle an account compromise itself

C5: Is the response under 120 words?
  PASS: 85 words — concise, actionable
  FAIL: 250 words — repeats the user's problem back, adds unnecessary context

## Test Inputs

Input 1: "Simple resolution — User says: 'My invoice from last month shows the wrong plan. I'm on the Pro plan at $49/month but was charged $79.' Knowledge base has billing correction process."

Input 2: "Should escalate — User says: 'Someone accessed my account and changed my email. I need this fixed immediately and I want to know what data they accessed.' Knowledge base says account security incidents must go to the security team."

Input 3: "Knowledge gap — User says: 'Can I get a custom SLA for 99.99% uptime? We're evaluating enterprise plans.' Knowledge base covers standard SLAs but nothing about custom agreements."

## Scoring

- Generate 10 outputs per test input (30 total per round)
- Score each output against all 5 criteria
- Round score = total passes / 150

## Rules

- NEVER modify this file after creation
- NEVER modify the scoring logic
- Score improvements are the ONLY signal for keeping changes
