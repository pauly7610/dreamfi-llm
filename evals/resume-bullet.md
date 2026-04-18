# Evaluation Criteria: Resume Bullet

Optimizes: Achievement-oriented resume bullets for PM and tech roles.

## Criteria

C1: Does the bullet start with a strong past-tense action verb?
PASS: "Shipped," "Reduced," "Grew," "Led," "Designed," "Migrated"
FAIL: "Responsible for," "Helped with," "Was involved in," "Worked on"

C2: Does the bullet include a specific quantified result?
PASS: "Grew daily active users from 12K to 45K in 6 months"
FAIL: "Significantly increased user engagement metrics"

C3: Is the bullet one sentence under 25 words?
PASS: "Reduced checkout abandonment by 18% by redesigning the payment flow for mobile users." (14 words)
FAIL: "I was part of a cross-functional team that worked together to identify and implement several improvements to the checkout experience, which led to better conversion rates across multiple platforms." (30 words)

C4: Does the bullet connect the action to a business outcome?
PASS: "Launched in-app onboarding flow that reduced Day-1 churn by 23%, saving $340K in annual acquisition costs."
FAIL: "Built an onboarding flow using React and Firebase."

## Test Inputs

Input 1: "Role: Senior PM at a B2B SaaS company. Achievement: Led the redesign of the dashboard that increased enterprise customer retention. Team size: 8 engineers. Timeline: Q3 2025."

Input 2: "Role: Growth PM at a consumer app. Achievement: Ran experiments on the referral program that increased viral coefficient. Before: 0.3 K-factor. After: 0.7 K-factor. Timeline: 4 months."

Input 3: "Role: PM at an AI startup. Achievement: Shipped the first version of an AI writing assistant that customers actually used. Adoption went from 5% to 40% of active users. Timeline: 2 months from concept to launch."

## Scoring

- Generate 10 outputs per test input (30 total per round)
- Score each output against all 4 criteria
- Round score = total passes / 120

## Rules

- NEVER modify this file after creation
- NEVER modify the scoring logic
- Score improvements are the ONLY signal for keeping changes
