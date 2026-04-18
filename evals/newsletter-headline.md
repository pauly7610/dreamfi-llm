# Evaluation Criteria: Newsletter Headline

Optimizes: Email subject lines and preview text for open rate.

## Criteria

C1: Does the subject line include a specific number?
PASS: "6 PM Use Cases for Karpathy's Autoresearch"
FAIL: "How to Use Autoresearch as a PM"

C2: Is the subject line under 50 characters?
PASS: "41% to 92% overnight" (22 chars)
FAIL: "The Complete Product Manager's Guide to Using Karpathy's Autoresearch System" (76 chars)

C3: Does the subject line create a knowledge gap without being clickbait?
PASS: "The AI system that took my skill from 41% to 92%"
FAIL: "You won't BELIEVE what this AI did" (clickbait)
FAIL: "Autoresearch guide" (no curiosity)

C4: Does the preview text add new information not in the subject line?
PASS: Subject: "41% to 92% overnight" / Preview: "Karpathy's 42K-star repo works on anything you can score."
FAIL: Subject: "AI skill optimization" / Preview: "Learn how to optimize your AI skills"

## Test Inputs

Input 1: "Article about Karpathy's autoresearch applied to PM workflows. Key stat: 41% to 92% in 4 rounds. 42K GitHub stars. Works on skills, prompts, agents, email."

Input 2: "Article about how PMs should evaluate AI features using binary scoring instead of vibes. Key stat: teams using structured evals ship 3x faster. Includes 5 eval templates."

Input 3: "Article interviewing Pendo's CPO about the product-led growth playbook. Key stat: Pendo went from $0 to $1B ARR. Covers 4 stages of PLG maturity."

## Scoring

- Generate 10 outputs per test input (30 total per round)
- Score each output against all 4 criteria
- Round score = total passes / 120

## Rules

- NEVER modify this file after creation
- NEVER modify the scoring logic
- Score improvements are the ONLY signal for keeping changes
