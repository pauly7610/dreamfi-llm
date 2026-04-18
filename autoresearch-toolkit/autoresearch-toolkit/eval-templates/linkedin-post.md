# Evaluation Criteria: LinkedIn Post

Optimizes: Hook strength, readability, and engagement for LinkedIn text posts.

## Criteria

C1: Does the first line create a specific curiosity gap or make a surprising claim?
  PASS: "I analyzed 500 PM job postings. 73% ask for a skill that didn't exist 2 years ago."
  FAIL: "I've been thinking a lot about product management lately."

C2: Is every sentence under 20 words?
  PASS: "The best PMs I know don't write PRDs anymore. They write eval criteria."
  FAIL: "The most successful product managers I've had the pleasure of working with over the past decade have shifted their approach to documentation in ways that would surprise most people." (35 words)

C3: Does the post have line breaks after every 1-2 sentences?
  PASS: Short paragraphs with whitespace between them
  FAIL: A wall of text with no line breaks for 5+ sentences

C4: Does the post end with a question, a bold prediction, or a one-line takeaway?
  PASS: "The PMs who learn to write evals will ship 10x faster than those still writing PRDs. Which one are you?"
  FAIL: "Hope this helps! Let me know your thoughts in the comments below."

C5: Is the post between 150 and 300 words?
  PASS: 210 words
  FAIL: 80 words (too thin for LinkedIn) / 450 words (too long, gets truncated)

## Test Inputs

Input 1: "Topic: Why autoresearch matters for PMs. Angle: The skill optimization loop. Audience: Product managers and tech leaders on LinkedIn."

Input 2: "Topic: The gap between PM job descriptions and what PMs actually do. Angle: Data from analyzing 200+ job postings. Audience: PMs looking for jobs and hiring managers."

Input 3: "Topic: How one prompt change improved a support agent's resolution rate from 62% to 89%. Angle: Practical AI product management. Audience: PMs building AI features."

## Scoring

- Generate 10 outputs per test input (30 total per round)
- Score each output against all 5 criteria
- Round score = total passes / 150

## Rules

- NEVER modify this file after creation
- NEVER modify the scoring logic
- Score improvements are the ONLY signal for keeping changes
