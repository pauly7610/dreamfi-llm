# Autoresearch Eval Templates

Ready-made evaluation criteria for common autoresearch use cases. Clone this repo, pick the template closest to your use case, modify 2-3 questions, and start running.

Each template includes:
- 4-6 binary eval criteria with PASS/FAIL examples
- 3 realistic test inputs
- A one-line description of what it optimizes

## Templates

| Template | File | What It Optimizes |
|----------|------|-------------------|
| Landing Page Copy | `landing-page-copy.md` | Headlines, CTAs, and body copy for conversion |
| Cold Email | `cold-email.md` | Outreach emails for reply rate |
| Agent System Prompt | `agent-system-prompt.md` | AI agent accuracy, hallucination, and tone |
| Support Agent | `support-agent.md` | Customer support resolution and escalation |
| LinkedIn Post | `linkedin-post.md` | Hook strength, readability, and engagement |
| Newsletter Headline | `newsletter-headline.md` | Subject lines and preview text for open rate |
| Product Description | `product-description.md` | E-commerce and SaaS product copy |
| Short-Form Script | `short-form-script.md` | Video scripts for retention and watch time |
| Resume Bullet | `resume-bullet.md` | Achievement-oriented resume lines |
| Meeting Summary | `meeting-summary.md` | Action items, decisions, and clarity |

## How to Use

1. Pick the template closest to your use case
2. Copy it into your autoresearch working directory
3. Modify the criteria to match your specific needs (keep 3-6 questions)
4. Swap in your own test inputs
5. Run the autoresearch loop

## Writing Your Own Eval

If none of these fit, describe what goes wrong when your skill fails. Convert each failure into a binary question:

- "Too vague" → "Does the output include at least one specific number?"
- "Wrong tone" → "Would this read naturally in a [channel] from a [role]?"
- "Too long" → "Is the output under [N] words?"
- "Misses the point" → "Does the first sentence address [specific user need]?"

The golden rules:
- Binary only. Pass or fail. Never a scale.
- 3-6 questions. Fewer invites shortcuts. More invites checklist gaming.
- Cover presence AND absence. What should be there, what should not.
- Lock the eval. Never let the agent modify scoring criteria.
