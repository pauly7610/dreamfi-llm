# Evaluation Criteria: Product Description

Optimizes: E-commerce and SaaS product copy for clarity and conversion.

## Criteria

C1: Does the first sentence name the specific problem the product solves?
PASS: "Engineering teams spend 10 hours a week writing status updates nobody reads."
FAIL: "Introducing the next generation of team productivity software."

C2: Does the description include at least one specific customer result with a number?
PASS: "Lattice reduced onboarding time from 14 days to 3."
FAIL: "Our customers love how much time they save."

C3: Is the description free of competitor comparisons?
PASS: Describes the product on its own merits
FAIL: "Unlike Slack, which is bloated and expensive..."

C4: Does the description address a specific objection in the last paragraph?
PASS: "Setup takes under 5 minutes. No credit card required. Cancel anytime."
FAIL: Ends with generic "Try it today!" without addressing friction

C5: Is the total description between 100 and 200 words?
PASS: 145 words
FAIL: 60 words (too thin) / 350 words (nobody reads product descriptions that long)

## Test Inputs

Input 1: "SaaS product: AI-powered status update tool for engineering teams. Integrates with Jira, Linear, GitHub. Auto-generates weekly summaries. $29/seat/month. Target: engineering managers at 50-500 person companies."

Input 2: "E-commerce product: Noise-canceling earbuds designed for open offices. 8-hour battery, $79, 30-day return policy. Target: remote and hybrid workers who need focus in noisy environments."

Input 3: "Developer tool: API monitoring service that alerts before customers notice. 99.99% uptime SLA, free tier up to 10K requests/day, $49/month for unlimited. Target: solo developers and small startups."

## Scoring

- Generate 10 outputs per test input (30 total per round)
- Score each output against all 5 criteria
- Round score = total passes / 150

## Rules

- NEVER modify this file after creation
- NEVER modify the scoring logic
- Score improvements are the ONLY signal for keeping changes
