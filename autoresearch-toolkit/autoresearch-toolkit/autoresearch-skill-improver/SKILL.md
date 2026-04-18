---
name: autoresearch-skill-improver
description: Automatically improve any Claude skill, system prompt, or template using Karpathy's autoresearch loop. Use when users want to optimize a skill's output quality, run automated evals against a skill, improve prompt reliability, reduce failure rates on existing skills, or run the autoresearch/Karpathy loop on any file. Triggers on phrases like "improve this skill," "run autoresearch," "optimize my prompt," "make this more reliable," "this skill fails too often," "run the loop on this," or any reference to eval-driven skill optimization. Also use when a user describes failure patterns in a skill and wants them fixed automatically.
---

# Autoresearch Skill Improver

Automated skill optimization using the autoresearch pattern. You define what "better" means. The agent runs the experiments. Improvements stack via git. Regressions auto-revert.

Origin: Andrej Karpathy's autoresearch repo (github.com/karpathy/autoresearch). The original trains ML models. This adaptation works on skills, prompts, templates, and any text file where output quality can be scored.

## How It Works

Three components, same as Karpathy's original:

1. **Target file** (the skill, prompt, or template to improve). The agent edits ONLY this file.
2. **Eval harness** (scoring criteria + test inputs). The agent NEVER modifies this after creation. If it could, it would make the test easier instead of making the skill better.
3. **Git loop** (commit winners, revert losers). Every decision is preserved in history.

The loop: read target → hypothesize improvement → edit target → generate outputs → score against eval → keep or revert → repeat.

~12 rounds per hour. 50-100 overnight. A human doing this manually runs maybe 50 per year.

## Workflow

### Phase 0: Understand the Target

Before anything else, read the target file completely. Understand what it does, how it structures instructions, and what its output looks like.

Ask the user (if not already provided):
- What file are we optimizing? (skill .md, system prompt, email template, etc.)
- What goes wrong when it fails? (vague headlines, hallucination, wrong tone, too long, etc.)
- Do you have eval criteria already, or should I generate them from your failure descriptions?
- What are 2-3 realistic test inputs? (different scenarios the skill should handle)

If the user describes failures instead of criteria, convert them:
- "Headlines are too vague" → "Does the headline include a specific number or measurable result?"
- "Too much jargon" → "Is the output free of these words: [list]?"
- "CTAs are weak" → "Does the CTA use a specific action verb tied to the product outcome?"
- "It hallucinates" → "Does the response use ONLY information from the provided context?"
- "Too long" → "Is the output under [N] words?"

### Phase 1: Build the Eval Harness

The eval is the most important part. A bad eval produces a perfectly optimized version of the wrong thing.

**Rules for eval criteria:**
- Every question MUST be binary. Pass or fail. Yes or no. Never a scale of 1-5. Scales introduce subjective drift that compounds across 50 rounds and makes scores meaningless.
- Keep it to 3-6 questions. Fewer than 3: the agent finds shortcuts that technically pass but produce garbage. More than 6: the agent starts gaming the checklist instead of improving the actual output.
- Lock the eval file. The agent cannot modify the evaluation after creating it. Ever. If it could edit the test, it would make the test easier instead of making the output better.
- Cover presence AND absence. Test what should be there (numbers, pain points) AND what should not be there (buzzwords, generic phrases). Both directions matter.

**Eval harness structure:**

Create `eval_criteria.md`:
```
# Evaluation Criteria for [Target Name]

## Criteria
C1: [Binary question] 
  PASS example: [concrete example]
  FAIL example: [concrete example]
C2: [Binary question]
  PASS example: [concrete example]
  FAIL example: [concrete example]
...

## Test Inputs
Input 1: [Realistic scenario with specific details]
Input 2: [Different scenario, different constraints]
Input 3: [Edge case or challenging scenario]

## Scoring
- Generate 10 outputs per test input (30 total per round)
- Score each output against all criteria
- Round score = total passes / total possible (e.g., 90/150 = 60%)

## Rules
- NEVER modify this file after creation
- NEVER modify the scoring logic
- Score improvements are the ONLY signal for keeping changes
```

Create `eval_runner.py` (or `eval_runner.sh`):
The eval script must:
1. Read the current target file
2. For each test input, generate 10 outputs using the target as instructions
3. Score every output against every criterion
4. Print per-criterion pass rates and aggregate score
5. Output results in a parseable format

The eval runner calls the Anthropic API (or uses `claude -p` in Claude Code) to generate outputs, then scores them. For criteria that can be checked programmatically (word count, presence of banned words, format checks), write deterministic checks. For criteria that require judgment (does it name a specific pain point?), use a separate LLM call as the scorer with the criterion and output as input.

**Lock the eval file after creation:**
```bash
chmod 444 eval_criteria.md
chmod 444 eval_runner.py
```

### Phase 2: Run Baseline

Run the eval harness against the current target file without any modifications.

```bash
python eval_runner.py --target [target-file] --round baseline
```

Record the baseline in `results.log`:
```
AUTORESEARCH RESULTS LOG — [Target Name]
==========================================
BASELINE: [X]/[total] = [X]%
  C1 ([name]): [pass]/[total] ([%])
  C2 ([name]): [pass]/[total] ([%])
  ...
```

If baseline is already above 90%, tell the user. The loop has diminishing returns above 90% because remaining failures are often edge cases that conflict with each other. They can still run it, but expectations should be calibrated.

Initialize git:
```bash
git add [target-file] eval_criteria.md eval_runner.py results.log
git commit -m "autoresearch: baseline [X]%"
```

### Phase 3: The Autoresearch Loop

Each round follows this exact sequence:

**3a. Analyze** — Read the per-criterion breakdown. Identify the worst-performing criterion. That's your target for this round. (This is triage logic: fix the biggest failure first, same way a good PM prioritizes.)

**3b. Hypothesize** — Form a specific hypothesis about why that criterion is failing and what change to the target file would fix it. Write the hypothesis in the results log before making the change.

**3c. Edit** — Make ONE change to the target file. One. Not three changes that might each help. One change so you know exactly what caused the score to move. If you make three changes and the score improves, you don't know which one helped. If you make three changes and the score drops, you don't know which one hurt.

Types of changes that work:
- Add a specific instruction ("Headline MUST include a number")
- Add a worked example showing good vs bad output
- Add a banned words list
- Restructure the order of instructions (what comes first gets more attention)
- Remove an instruction that's creating confusion
- Add a decision tree for edge cases
- Replace vague language with specific language

**3d. Evaluate** — Run the full eval harness.
```bash
python eval_runner.py --target [target-file] --round [N]
```

**3e. Decide** — Compare the round score to the previous best score.

If improved:
```bash
git add [target-file]
git commit -m "autoresearch round [N]: [score]% (was [prev]%) - KEPT - [one-line description of change]"
```
Append to results.log:
```
ROUND [N]: [X]/[total] = [X]% — KEPT
  Change: [description]
  Hypothesis: [what you expected]
  C1: [pass]/[total] ([%]) | C2: [pass]/[total] ([%]) | ...
```

If not improved:
```bash
git checkout -- [target-file]
```
Append to results.log:
```
ROUND [N]: [X]/[total] = [X]% — REVERTED (was [prev]%)
  Change: [description]
  Hypothesis: [what you expected]
  Why it failed: [brief analysis]
```

**3f. Repeat** — Start the next round. Continue until:
- Score hits 95%+ for 3 consecutive rounds (convergence)
- 50 rounds completed (budget limit)
- User interrupts

### Phase 4: Wrap Up

When the loop finishes, produce three outputs:

1. **Improved target file** — Already saved and committed. The original is recoverable via `git log`.

2. **results.log** — Complete experiment history with every round's score, change, and outcome.

3. **changelog.md** — Human-readable summary:
```
# Autoresearch Changelog — [Target Name]

## Summary
- Baseline: [X]% → Final: [Y]%
- Rounds: [N] total, [K] kept, [R] reverted
- Biggest single improvement: Round [N] (+[X] percentage points)
- Worst-performing criterion at end: [name] at [X]%

## Changes Kept (in order)
1. Round [N]: [description] — [score before] → [score after]
2. ...

## Changes Reverted (learnings)
1. Round [N]: [description] — dropped to [score]
   Learning: [why it failed, what this teaches]
2. ...

## Transferable Patterns
- [Pattern that would apply to other skills/prompts]
- [Pattern that would apply to other skills/prompts]
```

### What to Do When the Loop Gets Stuck

If the score plateaus for 5+ rounds:

1. Check if the remaining failures are contradictory (fixing one breaks another). If so, tell the user they need to decide which criterion to prioritize.

2. Check if the eval itself has a ceiling. Some criteria conflict at the margin. "Be concise" and "include specific examples" fight each other at extremes.

3. Try a structural change instead of an additive one. Most rounds add instructions. When you're stuck, try removing instructions or reorganizing the target file. Sometimes the skill has accumulated conflicting rules.

4. Try the opposite of what you've been doing. If you've been adding specificity, try simplifying. Contrarian rounds occasionally break plateaus.

## Cost and Time Estimates

Per round: ~$0.02-0.05 (30 API calls for generation + 30 for scoring)
Full run (50 rounds): ~$1-2.50
Overnight run (100 rounds): ~$2-5
Time per round: ~2-5 minutes (depending on output length and API speed)

## Important Constraints

- NEVER modify eval_criteria.md or eval_runner.py after Phase 1
- NEVER make more than one change per round
- ALWAYS commit before moving to the next round (win or lose)
- ALWAYS record the full per-criterion breakdown in results.log
- The user's original file is ALWAYS recoverable via git
- If the user provides a target file, copy it first: `cp [original] [original].backup`

## Quick Start Prompt

If the user just wants to get going fast, they can paste this into Claude Code:

```
Read the autoresearch-skill-improver skill. I want to optimize [FILE PATH].

Here's what goes wrong when it fails:
- [failure 1]
- [failure 2]
- [failure 3]

Test against these inputs:
1. [realistic scenario]
2. [different scenario]
3. [edge case]

Build the eval, run the baseline, then start the loop. Wake me up when it's done.
```
