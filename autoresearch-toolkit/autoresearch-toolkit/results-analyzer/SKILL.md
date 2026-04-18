---
name: autoresearch-results-analyzer
description: Analyze autoresearch experiment logs (results.log files) to extract patterns, transferable learnings, and actionable summaries. Use when users have completed an autoresearch run and want to understand what worked, what failed, and what patterns transfer to other skills. Triggers on phrases like "analyze my results," "what did the loop learn," "summarize my experiment log," "what patterns transferred," or any reference to reading/understanding autoresearch results.log files.
---

# Autoresearch Results Analyzer

Reads any autoresearch results.log file and produces structured analysis. Turns 50 rounds of raw experiment data into transferable knowledge.

## What This Does

Takes a results.log file (the output of an autoresearch run) and produces:

1. **Performance Summary** — Baseline vs final score, improvement trajectory, convergence point
2. **Criterion Analysis** — Which criteria improved most, which are still weak, which hit ceilings
3. **Change Effectiveness** — What types of changes worked vs didn't, sorted by impact
4. **Reversion Analysis** — What was tried and reverted, and what each reversion teaches
5. **Transferable Learnings** — Patterns that apply to other skills, prompts, and templates
6. **Recommendations** — What to try next, whether to keep running, and where to focus

## Workflow

### Step 1: Parse the Log

Read the results.log file. Extract structured data:

For each round, capture:
- Round number
- Score (passes/total = percentage)
- Outcome (KEPT or REVERTED)
- Change description
- Per-criterion breakdown (C1, C2, ... with pass counts and percentages)

For the baseline, capture:
- Total score
- Per-criterion breakdown
- Weakest criterion at start

### Step 2: Generate Performance Summary

```
## Performance Summary

Baseline: [X]% → Final: [Y]% (+[Z] percentage points)
Rounds run: [N]
Changes kept: [K] / [N] ([%] acceptance rate)
Changes reverted: [R]
Convergence: [Score first hit 90%+ at round N / Did not converge]

Improvement trajectory:
  Baseline → Round [first kept]: +[X]pp (biggest single jump)
  Round [X] → Round [Y]: +[X]pp
  ...
  
Cost estimate: ~$[X] ([N] rounds × ~$0.02-0.05/round)
```

### Step 3: Criterion Deep Dive

For each criterion, track its journey:

```
## Criterion Analysis

C1: [Name]
  Baseline: [X]% → Final: [Y]%
  Improvement: +[Z]pp
  Rounds that targeted this: [list]
  Current status: [Strong (>90%) / Moderate (70-90%) / Weak (<70%)]
  
  What fixed it: [description of the change(s) that moved this criterion]
  
C2: [Name]
  ...
```

Identify:
- Which criterion improved most (in percentage points)
- Which criterion is still the weakest
- Whether any criteria degraded while others improved (tradeoff detection)

### Step 4: Change Effectiveness Analysis

Categorize every change by type:

```
## Change Effectiveness

### Changes That Worked (sorted by impact)
1. [Change type]: [description] — +[X]pp (Round [N])
2. ...

### Changes That Failed (sorted by severity)
1. [Change type]: [description] — -[X]pp (Round [N], reverted)
2. ...

### Change Type Success Rates
- Adding specific instructions: [X]/[Y] kept ([%])
- Adding worked examples: [X]/[Y] kept ([%])
- Adding banned word lists: [X]/[Y] kept ([%])
- Restructuring/reordering: [X]/[Y] kept ([%])
- Removing instructions: [X]/[Y] kept ([%])
- Tightening constraints: [X]/[Y] kept ([%])
```

### Step 5: Reversion Analysis

Reversions are where the real learning lives. Each reversion is a hypothesis that was tested and disproved.

```
## What Didn't Work (and Why It Matters)

Round [N]: Tried [description]. Score dropped from [X]% to [Y]%.
  Why it failed: [analysis]
  Lesson: [transferable insight]
  
Round [N]: Tried [description]. Score dropped from [X]% to [Y]%.
  Why it failed: [analysis]  
  Lesson: [transferable insight]
```

Common patterns to look for:
- Tightening one constraint hurts another (word count limits hurt CTA quality)
- Adding too many rules creates confusion (shorter prompts sometimes outperform longer ones)
- Format restrictions hurt content quality
- Instructions that overlap or contradict each other

### Step 6: Transferable Learnings

Extract patterns that would apply to ANY skill, prompt, or template:

```
## Transferable Learnings

These patterns apply beyond [target name]:

1. [Pattern]: [explanation]
   Applies to: [list of other skill/prompt types]
   Evidence: Round [N] showed [what happened]

2. [Pattern]: [explanation]
   ...
```

Common transferable patterns:
- "Headlines with specific numbers outperform vague headlines" → applies to email subject lines, LinkedIn hooks, newsletter titles, YouTube thumbnails
- "Banned word lists are more effective than 'avoid jargon' instructions" → applies to any writing skill
- "Worked examples teach better than abstract rules" → applies to all skills
- "Shorter instructions often outperform longer ones" → applies to system prompts, agent prompts

### Step 7: Generate learnings.md

Create a standalone file the user can drop into other skills:

```markdown
# Learnings from [Target Name] Autoresearch Run
# Generated: [date]
# Baseline: [X]% → Final: [Y]% over [N] rounds

## Rules That Worked
- [Rule from the improved skill that drove improvement, with the score delta]
- ...

## Rules That Hurt
- [Rule that was tried and reverted, with explanation]
- ...

## Patterns for Other Skills
- [Transferable pattern with evidence]
- ...

## Recommended Next Steps
- [What to try if running another loop on this skill]
- [What to try on related skills]
```

### Step 8: Recommendations

```
## What to Do Next

### If you want to keep improving this skill:
- Focus on: [weakest criterion] at [X]%
- Try: [specific change hypothesis based on pattern analysis]
- Estimated ceiling: [X]% (based on convergence trajectory)

### If you want to apply these learnings elsewhere:
- Start with: [skill/prompt type that would benefit most from these patterns]
- Port these rules directly: [list of rules from the improved skill]
- Use learnings.md as a reference when writing eval criteria for the new skill

### If you want to share results:
- Key stat: [the most impressive single number from the run]
- Story: [one-sentence narrative of the run]
```

## Output Files

The analyzer produces:

1. **analysis.md** — Full structured analysis (Steps 2-8 above)
2. **learnings.md** — Portable learnings file for other skills
3. Terminal summary — Key stats printed for quick reference

## Edge Cases

- If the log has fewer than 3 rounds, note that the sample is too small for pattern analysis and focus on the criterion breakdown instead
- If all rounds were kept (no reversions), note this is unusual and check whether the eval criteria are too easy
- If all rounds were reverted, the eval criteria may be contradictory or the baseline skill may already be near-optimal for those criteria
- If the log format doesn't match the expected structure, ask the user to confirm the format before parsing
