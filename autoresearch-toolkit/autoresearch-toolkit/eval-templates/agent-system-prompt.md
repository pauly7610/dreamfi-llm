# Evaluation Criteria: Agent System Prompt

Optimizes: AI agent accuracy, hallucination prevention, and response quality.

## Criteria

C1: Does the agent correctly identify the user's intent on the first response?
  PASS: User asks "how do I reset my password" → agent provides password reset steps
  FAIL: User asks "how do I reset my password" → agent asks "what kind of password?"

C2: Does the response avoid making up information not in the provided context?
  PASS: "I don't have information about that specific policy. Let me connect you with someone who does."
  FAIL: "Our refund policy allows returns within 30 days." (when no refund policy was in the context)

C3: Does the response include a specific next action for the user?
  PASS: "Click Settings > Security > Reset Password, then check your email for a confirmation link."
  FAIL: "You should be able to find that in your account settings somewhere."

C4: Is the response under 80 words?
  PASS: 54 words
  FAIL: 150 words

C5: For impossible or ambiguous requests, does the agent say so clearly instead of guessing?
  PASS: "I can help with billing questions, but I'd need to transfer you to our technical team for server configuration."
  FAIL: "Sure, let me try to help with your server configuration." (when the agent has no server knowledge)

## Test Inputs

Input 1: "Clear request with full context — User says: 'I was charged twice for my subscription this month. My account email is jen@example.com and the charges were on March 3 and March 5, both for $29.' Knowledge base includes billing dispute process."

Input 2: "Ambiguous request — User says: 'This isn't working.' No prior conversation. No product specified. Knowledge base covers 3 different products."

Input 3: "Request outside knowledge base — User says: 'Can you help me configure the API rate limits on our enterprise plan?' Knowledge base only covers consumer plan features."

## Scoring

- Generate 10 outputs per test input (30 total per round)
- Score each output against all 5 criteria
- Round score = total passes / 150

## Rules

- NEVER modify this file after creation
- NEVER modify the scoring logic
- Score improvements are the ONLY signal for keeping changes
