# Evaluation Criteria: Landing Page Copy

Optimizes: Headlines, subheadlines, body copy, and CTAs for conversion.

## Criteria

C1: Does the headline include a specific number or measurable result?
PASS: "Save 10 Hours Per Week on Status Updates"
FAIL: "Transform Your Business With Our Solution"

C2: Is the copy completely free of buzzwords?
Banned list: revolutionary, cutting-edge, synergy, next-level, game-changing, leverage, unlock, transform, streamline, empower, innovative, seamless, robust, scalable, holistic
PASS: "Your team writes status updates nobody reads. This tool writes them in 30 seconds."
FAIL: "Our innovative platform empowers teams to streamline their workflows."

C3: Does the CTA use a specific action verb tied to the product outcome?
PASS: "Start Saving 10 Hours This Week"
FAIL: "Learn More" / "Get Started" / "Sign Up"

C4: Does the first sentence after the headline name a specific pain point the reader experiences?
PASS: "Your team spends 10 hours every week writing updates nobody reads."
FAIL: "In today's fast-paced world, teams need better tools."

C5: Is the total copy between 80 and 150 words?
PASS: 95 words
FAIL: 47 words (too thin) / 220 words (too long)

## Test Inputs

Input 1: "AI Productivity Tool — An AI tool that automates weekly status updates for engineering teams. Integrates with Jira and Linear. Saves managers 10+ hours per week. $29/seat/month."

Input 2: "B2B CRM — A CRM specifically for marketing agencies with 10-50 employees. Tracks client relationships, project timelines, and revenue per client. Replaces spreadsheets most agencies use. $99/month flat."

Input 3: "Personal Finance App — A mobile app that rounds up purchases and invests the spare change. Targets 22-35 year olds who want to invest but don't know where to start. Free tier with $3/month premium."

## Scoring

- Generate 10 outputs per test input (30 total per round)
- Score each output against all 5 criteria
- Round score = total passes / 150

## Rules

- NEVER modify this file after creation
- NEVER modify the scoring logic
- Score improvements are the ONLY signal for keeping changes
