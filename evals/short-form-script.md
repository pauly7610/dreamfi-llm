# Evaluation Criteria: Short-Form Script

Optimizes: Video scripts (TikTok, Reels, Shorts) for retention and watch time.

## Criteria

C1: Does the opening line create a specific curiosity gap within the first 5 words?
PASS: "This $3 tool replaced my $500/month stack."
FAIL: "Hey guys, so today I want to talk about something interesting."

C2: Is there a surprising claim or counterintuitive statement in the first 2 sentences?
PASS: "The worst-performing PMs I know write the best PRDs."
FAIL: "Product management is an important skill in tech."

C3: Does the script follow a single narrative thread from start to finish?
PASS: One idea developed with escalating stakes
FAIL: Three loosely related tips crammed into 60 seconds

C4: Is the script under 90 seconds when read at a natural pace (~150 words/minute)?
PASS: 200 words (~80 seconds)
FAIL: 350 words (~140 seconds)

C5: Does it end with a hook that drives to the next piece of content?
PASS: "Part 2 covers the three mistakes that kill most of these experiments overnight."
FAIL: "Hope that was helpful! Like and subscribe for more."

## Test Inputs

Input 1: "Topic: How Karpathy's autoresearch loop works, explained for non-technical people. Target: PMs and founders on LinkedIn/TikTok. Goal: Drive to newsletter signup."

Input 2: "Topic: Why most AI features fail in production (the demo-to-production gap). Target: Engineers and PMs building AI products. Goal: Drive to a YouTube deep dive."

Input 3: "Topic: One prompt change that improved a support bot's resolution rate by 27 percentage points. Target: Founders building AI customer support. Goal: Drive to a podcast episode."

## Scoring

- Generate 10 outputs per test input (30 total per round)
- Score each output against all 5 criteria
- Round score = total passes / 150

## Rules

- NEVER modify this file after creation
- NEVER modify the scoring logic
- Score improvements are the ONLY signal for keeping changes
