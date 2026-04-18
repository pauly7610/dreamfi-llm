# Autoresearch Toolkit for PMs

Everything you need to run Karpathy's autoresearch pattern on skills, prompts, agents, and templates.

Companion toolkit for [Autoresearch: The AI System That Took My Skill From 41% to 92% Overnight](https://news.aakashg.com).

Built by [Aakash Gupta](https://twitter.com/aakashg0) · [Product Growth Newsletter](https://news.aakashg.com)

## What's Inside

### 1. `autoresearch-skill-improver/`

A Claude Code skill that runs the full autoresearch loop on any target file. Drop it into your skills folder, point it at your worst skill, and go to sleep.

The skill handles everything: builds the eval harness from your failure descriptions, runs the baseline, enters the loop (one change per round, commit winners, revert losers), and produces the improved file + results.log + changelog when it's done.

### 2. `eval-templates/`

10 ready-made eval criteria for common PM use cases. Each template includes binary eval criteria with PASS/FAIL examples and realistic test inputs.

Templates: landing page copy, cold email, agent system prompt, support agent, LinkedIn post, newsletter headline, product description, short-form script, resume bullet, meeting summary.

### 3. `results-analyzer/`

A Python script and Claude Code skill that reads any results.log and produces structured analysis: which criteria improved most, which changes got reverted and why, and what patterns transfer to other skills.

## Quick Start

```bash
# Copy the skills into your Claude Code skills folder
cp -r autoresearch-skill-improver/ ~/.claude/skills/
cp -r results-analyzer/ ~/.claude/skills/

# Pick an eval template
cp eval-templates/landing-page-copy.md ./eval_criteria.md

# Edit the criteria, then tell Claude Code:
# "Read the autoresearch-skill-improver skill. Optimize [your file]."
```

## Prerequisites

- Claude Code (recommended) or any coding agent that can read files, edit files, and use git
- Git (for the commit/revert loop)
- Python 3.8+ (for the results analyzer script)

## The Pattern

| Karpathy's Version | Your Version |
|---|---|
| `train.py` (model training code) | Your skill, prompt, or template |
| `prepare.py` (locked eval harness) | Your eval criteria + scoring script |
| `program.md` (agent instructions) | The skill improver SKILL.md |
| `val_bpb` (validation loss) | Your pass/fail checklist score |
| `git commit` / `git reset` | Same. Winners stay, losers revert. |

## Cost

About $0.02-0.05 per round. A full 50-round run costs $1-2.50.

## Related

- [Karpathy's autoresearch repo](https://github.com/karpathy/autoresearch)
- [Product Growth Newsletter](https://news.aakashg.com)
- [AI by Aakash](https://aibyaakash.com)
