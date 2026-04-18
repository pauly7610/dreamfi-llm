# Evaluation Criteria: Meeting Summary

Optimizes: Clarity, action items, and decision capture from meeting transcripts.

## Criteria

C1: Does every action item include a specific owner name and a deadline?
PASS: "Sarah will send the updated pricing page to design by Friday March 21."
FAIL: "Team to follow up on pricing page."

C2: Are decisions stated as decisions, not as discussion summaries?
PASS: "Decision: Launch the beta to 500 users on April 1, not the full user base."
FAIL: "The team discussed whether to launch the beta to a subset of users or all users."

C3: Is the summary under 300 words regardless of meeting length?
PASS: 220 words covering a 45-minute meeting
FAIL: 800 words that basically retranscribe the meeting

C4: Does the summary separate decisions, action items, and open questions into distinct sections?
PASS: Clear headers for each category
FAIL: Everything mixed into a narrative paragraph

C5: Are open questions stated as questions, not as vague topics?
PASS: "Open: Do we need legal review before launching in the EU?"
FAIL: "Open: EU launch considerations"

## Test Inputs

Input 1: "45-minute product review meeting. 6 attendees. Discussed Q2 roadmap priorities, debated whether to build a mobile app or improve the web experience first. Decided on web. Three action items assigned. One open question about hiring timeline."

Input 2: "30-minute 1:1 between a PM and engineering lead. Discussed tech debt in the payments service, agreed to allocate 20% of next sprint to it. PM needs to write the brief. Open question: should they migrate to Stripe or fix the current integration?"

Input 3: "60-minute cross-functional meeting with 12 people. Marketing, Product, Engineering, Sales. Discussed launch plan for new feature. Multiple disagreements. Two decisions made, four action items, three unresolved questions. Some attendees talked over each other and changed topics frequently."

## Scoring

- Generate 10 outputs per test input (30 total per round)
- Score each output against all 5 criteria
- Round score = total passes / 150

## Rules

- NEVER modify this file after creation
- NEVER modify the scoring logic
- Score improvements are the ONLY signal for keeping changes
