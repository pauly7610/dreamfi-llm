# Evaluation Criteria: Cold Email

Optimizes: Outreach emails for reply rate. Shorter, more specific, ending with a question.

## Criteria

C1: Is the email 75 words or fewer?
  PASS: 62 words
  FAIL: 140 words

C2: Does it reference the prospect's specific role, company type, or industry?
  PASS: "Running product at a Series B startup means you're probably drowning in feature requests."
  FAIL: "As a busy professional, you know how hard it is to stay organized."

C3: Does it end with a concrete question that invites a one-line reply?
  PASS: "Would a 15-minute walkthrough next Tuesday work?"
  FAIL: "Let me know if you're interested in learning more."

C4: Do the first two sentences include a specific number or result?
  PASS: "We helped Lattice cut their onboarding time from 14 days to 3."
  FAIL: "We help companies improve their onboarding process significantly."

## Test Inputs

Input 1: "Prospect: Sarah Chen, VP Product at a Series B fintech startup (80 employees). Product: DevCycle, a feature flag platform. Goal: Get a 15-minute demo call."

Input 2: "Prospect: Marcus Johnson, Head of Engineering at a mid-market e-commerce company (200 employees). Product: Datadog competitor focused on cost (40% cheaper). Goal: Get them to try a free pilot."

Input 3: "Prospect: Lisa Park, Director of Marketing at a DTC skincare brand ($15M ARR). Product: AI-powered email copywriting tool. Goal: Get a reply expressing interest."

## Scoring

- Generate 10 outputs per test input (30 total per round)
- Score each output against all 4 criteria
- Round score = total passes / 120

## Rules

- NEVER modify this file after creation
- NEVER modify the scoring logic
- Score improvements are the ONLY signal for keeping changes
