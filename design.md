DreamFi — System Design
Trust, measured.

0. The one-sentence pitch
DreamFi is a trust engine for product work: it turns the messy output of LLMs, connectors, and dashboards into artifacts that can be signed for — evaluated, versioned, gated, and published with a receipt.

It is not a chatbot. It is not "Onyx with a UI." It is the layer that stands between a large language model and the page you are about to put in front of your CEO, and refuses to let that page be wrong in silence.

1. Why this exists
Every product team has the same problem and pretends it doesn't.

The CEO asks why activation is down. A PM asks Claude. Claude reads Confluence, pulls some Jira tickets, hallucinates two metric definitions, and writes a very confident two-page summary. The PM pastes it into Slack. It sounds right. It is partly right. No one knows which part.

This is the quiet failure mode of AI at work: outputs are fluent enough to defeat the reader's instinct to audit, but the system that produced them has no idea what it got wrong. Retrieval is only "grounded" if the grounding is verified. A citation is just a URL if nothing checked whether the claim matches the source. A confidence score is a lie if nothing enforces what it costs to be wrong.

DreamFi is built on a simple wager: trust is a measurable property, and the thing that wins in this decade is the system that measures it the best.

Most of the industry is racing on model quality, context window, and tool use. Those matter, but they all funnel into the same bottleneck — will a human sign their name to this output? If the answer is "not yet," the model might as well not exist. DreamFi is a system designed to make the answer yes, and here's the audit trail.

2. Design principles
Six principles. Every disagreement about this system should be settled by re-reading them.

2.1 Trust is the product. Everything else is plumbing.
Retrieval, generation, routing, tenancy, publishing, UI — none of these are the thing we're selling. They're necessary. They're not sufficient. The thing we're selling is an artifact a human can stake their reputation on, and a paper trail that explains why.

Test: If a feature doesn't raise, surface, or enforce a trust score, it's plumbing. Plumbing ships when trust features need it, not before.

2.2 Binary gates beat fuzzy scores.
"Having binary options forces people to make a decision rather than hiding uncertainty in middle values." — 
Hamel Husain, LLM Evals FAQ

DreamFi's hard gates are pass/fail, never 1-to-5. A meeting summary either contains every decision from the transcript or it doesn't. A metric claim either resolves to a catalog entry or it doesn't. We compose many binary checks into a composite score that a human can actually interpret — "this artifact passes 11 of 12 gates and here is the one it failed."

Graded rubrics exist, but only as LLM-as-judge inputs to binary verdicts. Never as the final word.

2.3 Every claim must be grounded. Every grounding must be checkable.
This is the single hardest discipline in the system and the single most valuable.

Structured output contracts force each generated artifact to emit a claims: list[Claim] where each claim carries either a sot_id (source-of-truth catalog ID), a citation_id (an Onyx document citation), or both. A claim without a source fails the hard gate. No exceptions.

The result: a reviewer opening any DreamFi artifact can click through to the underlying truth for every sentence. If nothing backs a sentence, the artifact never reached them in the first place.

2.4 Evaluation is code. Prompts are code. Gold examples are code.
Prompts have versions. Gold examples have roles. Evals have hashes. All three flow through the same promote → test → revert lifecycle as any other piece of software. A prompt change without a round of evals is not merged. A prompt change that causes any gold-regression example to flip from pass to fail is not merged, even if its main score improves.

This is the spiritual inverse of "prompt engineering is just typing nicely." Prompts are the runtime of an LLM system, and runtimes need CI.

2.5 Separate retrieval, generation, evaluation, and publishing.
Four concerns, four boundaries. Onyx handles retrieval. A model router handles generation. A deterministic evaluator handles judgment. A queued, idempotent adapter handles publishing. They talk through narrow, typed interfaces and they can be swapped independently.

Why this matters: every AI product that gets stuck does so because these four concerns have bled into each other. "Our retrieval is broken" is actually "our eval can't tell if retrieval is broken." "Our model got worse" is actually "we never measured our model." DreamFi refuses to blur them.

2.6 Nothing publishes without a receipt.
Every artifact that leaves DreamFi leaves with:

A hard-gate verdict.

An export-readiness score and its decomposition.

A list of claims with sources.

A list of tool calls made during generation.

The exact prompt version, model version, and retrieval snapshot used.

A reviewer signature (human or policy-based auto-approval).

A destination receipt (Confluence page ID, Jira issue key, etc.).

A rollback handle.

If we can't produce the receipt, the artifact doesn't publish. The database trigger that enforces this is non-negotiable — it is the last line of defense, below the API, below the approval UX, below application logic. A bug in Python cannot bypass it.

3. What DreamFi is (and isn't)
DreamFi is:

A skill registry of PM artifacts with locked, versioned evaluation templates — meeting summaries, cold emails, landing page copy, product descriptions, newsletter headlines, resume bullets, short-form scripts, agent system prompts, support agent replies, planning briefs, metric briefs, handoff packages, requirements captures.

A trust fabric that measures four things continuously: planning trust (is your Jira/Dragonboat data coherent?), metric trust (do your numbers agree across sources?), interpretation trust (is every claim in this artifact grounded?), and artifact trust (is this output ready to export?).

A promotion engine that moves prompts forward on measurable improvement and reverses on measurable regression, with gold regression examples as immune cells.

A publishing substrate with real destinations (Confluence, Notion, Jira, Slack), real OAuth, idempotent queues, and rollback.

A multi-tenant product where two workspaces cannot see each other's rows, at any level — enforced by Postgres Row-Level Security, not hope.

DreamFi is not:

A chatbot. You don't "chat" with DreamFi. You commission an artifact.

A replacement for Onyx. Onyx is the retrieval substrate. Swapping to another retrieval layer is a week of work.

A replacement for Jira, Dragonboat, Metabase, PostHog, or Confluence. DreamFi reads from them, measures them, and publishes back to them. It does not try to host them.

An annotation platform. DreamFi's evaluators are code. Human review is occasional, strategic, and feeds back into code.

A frontier model company. Model versions are pins we control, not research we do.

4. Architecture
4.1 The ten-thousand-foot view
text
┌────────────────────────────────────────────────────────────────────┐
│                         USER / SLACK / API                          │
└──────────────────────────┬──────────────────────────────────────────┘
                           │  Workspace-scoped JWT + API key
                           │
                 ┌─────────▼──────────┐
                 │  DreamFi API       │
                 │  (FastAPI)         │
                 │  tenancy, rate,    │
                 │  audit middleware  │
                 └────┬─────────┬─────┘
                      │         │
         ┌────────────┘         └──────────────────┐
         │                                         │
┌────────▼─────────┐                    ┌──────────▼───────────┐
│ Generation       │                    │  Publisher           │
│ Engine           │                    │  adapters +          │
│  retrieve()      │                    │  OAuth broker +      │
│  complete()      │                    │  idempotent queue    │
│  critic()        │                    └──────────┬───────────┘
│  eval()          │                               │
│  confidence()    │                               │
└──┬───┬───┬───┬───┘                               │
   │   │   │   │                                   │
   │   │   │   └──▶ Trust Fabric ─────────────┐    │
   │   │   │        (planning, metric,        │    │
   │   │   │         interpretation, artifact) │    │
   │   │   │                                   │    │
   │   │   └──────▶ Onyx MCP tools ◀─ ─ ─ ─ ──┤    │
   │   │                                       │    │
   │   └──────────▶ Model Router (LiteLLM) ◀──┤    │
   │                                          │    │
   └─────────────▶ Onyx (retrieval) ◀─ ─ ─ ── ┘    │
                                                   │
       ┌───────────────────────────────────────────┘
       ▼
┌───────────────────────────────────────────────────────────────────┐
│  Postgres (tenant-scoped, RLS enforced)                           │
│   skills · prompt_versions · eval_rounds · eval_outputs ·         │
│   gold_examples · gold_drift_events · publish_log · sot_catalog · │
│   metric_catalog · metric_snapshots · metric_discrepancies ·      │
│   planning_trust_reports · ambiguity_flags · anomalies ·          │
│   artifact_claims · approval_requests · oauth_connections ·       │
│   publish_jobs · workspaces · users · api_keys                    │
│                                                                   │
│  Redis (queue, rate limit, idempotency keys)                      │
│  Object storage (S3/MinIO — transcripts, rendered artifacts)      │
└───────────────────────────────────────────────────────────────────┘
4.2 The anatomy of one generation
The single most important diagram in this document. Read it slowly.

text
 1. Request
    POST /v1/skills/meeting_summary/generate
    X-Workspace-Id: ws_abc
    body: { input_context: { transcript: "..." }, test_input_label: "weekly-eng-standup" }

 2. Tenancy middleware
    SET LOCAL dreamfi.workspace_id = 'ws_abc'
    verify membership, load policy

 3. Retrieval
    OnyxClient.admin_search(
      query=query_from(transcript),
      filters={"workspace_id": "ws_abc"}
    ) → N chunks with (document_id, blurb, score, link, updated_at)

 4. Tool-augmented generation loop    (bounded: 4 calls, 20s wall, 3× budget)
    ModelRouter.complete(
      model=policy.primary("meeting_summary"),
      messages=[system_prompt, few_shot_gold, retrieved_context, user_input],
      output_schema=MeetingSummaryOutput,
      tools=[onyx.search, onyx.fetch_document, jira.get_issue, metric.lookup, sot.search]
    )
    → structured output + tool_trace[] + token_usage + latency_ms

 5. Critic pass                          (cheap model, budget-capped)
    critic_verdict = ModelRouter.complete(
      model=policy.critic("meeting_summary"),
      messages=[critic_prompt(output, rubric)]
    )
    if critic_verdict.suggests_revision and budget_remaining:
        revised_output = ModelRouter.complete(... revision prompt ...)
        output = max_by_eval(output, revised_output)

 6. Evaluation                           (locked runner, immutable)
    eval_result = run_eval(
      skill="meeting_summary",
      output=output,                     # parsed Pydantic, not raw text
      test_input_label="weekly-eng-standup"
    )
    → { pass_fail, failed_criteria[], criteria_matrix }

 7. Gold regression check                (T0 core)
    regression_diffs = run_regression_gold_set("meeting_summary", prompt_version_id)
    for each pass→fail transition: emit gold_drift_event

 8. Claim grounding                      (T3 core)
    for claim in output.claims:
        if claim.sot_id is None and claim.citation_id is None:
            eval_result.fail_with("ungrounded_claim")

 9. Metric grounding                     (T2 core)
    for metric_ref in output.metrics:
        catalog_entry = metric_catalog.lookup(metric_ref.metric_id)
        if catalog_entry is None:
            eval_result.fail_with("uncatalogued_metric")
        discrepancy = metric_discrepancies.latest(metric_ref.metric_id, metric_ref.as_of_date)
        if discrepancy.severity == "block":
            eval_result.fail_with(f"discrepancy_block:{metric_ref.metric_id}")

10. Confidence scoring
    confidence = ConfidenceScorer.score(
      eval_score, freshness, citation_count, hard_gate_passed
    )

11. Export-readiness composite           (T4 core)
    export_readiness = compose(
      hard_gate=eval_result.pass_fail,        # short-circuits to 0 if "fail"
      confidence=confidence,
      gold_regression_pass_rate=...,
      claim_lineage_rate=...,
      metric_freshness=...,
      hygiene_score=planning_trust.current(workspace_id)
    )

12. Persist
    eval_outputs row with ALL of the above, including:
      - onyx_chat_session_id, onyx_message_id, onyx_citations_json
      - model_id, input_tokens, output_tokens, cost_usd, latency_ms
      - tool_trace_json, critic_verdict_json, revision_count
      - claims_json, metric_refs_json
      - export_readiness + export_breakdown_json

13. Respond
    { output_id, pass_fail, export_readiness, claims, ... }

14. [LATER] Publish — only on approval AND DB trigger green
    POST /v1/skills/meeting_summary/publish { output_id, destination: "confluence", config: {...} }
    → approval_requests row → (human or policy auto-approve)
    → publish_jobs queued with idempotency_key
    → adapter.render() → adapter.publish() → receipt
    → DB trigger enforces export_readiness ≥ workspace.threshold or raises
    → publish_log written with receipt
Every step produces data that future steps and humans can audit. Every step is a boundary you can test in isolation. Every step can fail closed.

4.3 The skill
A skill is the atomic unit of trust.

python
class Skill:
    skill_id: str                           # "meeting_summary"
    display_name: str
    eval_template_path: Path                # evals/meeting-summary.md  (locked)
    eval_runner_path: Path                  # evals/runners/...          (locked)
    output_contract: type[BaseModel]        # MeetingSummaryOutput       (versioned)
    prompt_versions: list[PromptVersion]    # with exactly one active
    model_policy: ModelPolicy               # primary, fallbacks, critic, temperature
    tool_policy: ToolPolicy                 # which tools the agent may call
    export_threshold: float                 # workspace-overridable
    gold_examples:
        exemplars: list[GoldExample]        # for few-shot context
        regression: list[GoldExample]       # immune cells — must keep passing
        counter_examples: list[GoldExample] # anti-patterns for the critic
        canaries: list[GoldExample]         # drift alarms (non-blocking)
Adding a new skill means adding an eval template, a runner, a prompt template, a Pydantic output contract, and at least five regression gold examples. The system refuses to register a skill that's missing any of those.

4.4 The eval layer
We split evaluation into three tiers, in order of how often they run:

Tier 1 — Deterministic checks (free, always on). Word counts, required fields, regex patterns, schema validity. These live in the locked runners under evals/runners/. They are pure functions. They are the spine.

Tier 2 — Structural checks (cheap, every generation). Claim grounding, metric catalog hits, taxonomy coverage, gold-regression pass rates, anomaly acknowledgement. These are code that reads structured output and the database. They are what makes DreamFi different from a pure prompt framework.

Tier 3 — LLM-as-judge (expensive, sampled). Where a human-level judgment is unavoidable (tone, persona fit, sophistication), we use an LLM judge — but:

Calibrated against a human-labeled reference set (inter-rater agreement measured, tracked, alerted when it drops).

Runs a different model family than the generator (avoid self-bias).

Produces binary verdicts only.

Prompts are narrowly scoped, one dimension per judge call.

Pairwise comparisons are randomized to kill position bias.

This is the Anthropic-recommended pattern (
Demystifying Evals for AI Agents
) and the Hamel Husain error-analysis pattern (
Lenny's Newsletter
). We don't claim to have invented it. We claim to have built a system where it's the path of least resistance.

4.5 The trust fabric
Four parallel scorers, each a first-class citizen.

Planning trust. Reads Jira + Dragonboat. Emits hygiene_score, taxonomy_coverage, ambiguity_rate. Writes ambiguity_flags rows for missing owners, stale tickets, broken links, RAG/activity mismatch. Every generated planning artifact must list its flags — a brief that pretends everything is fine when it's not fails the gate.

Metric trust. A catalog where every metric has a locked definition, a primary source, secondary sources, and an owner. A snapshot table that records what each source said on each date. A discrepancy detector that flags divergence. A cross-artifact rule: any metric cited without a metric_id from the catalog fails the gate. A discrepancy marked block prevents publish.

Interpretation trust. The sot_catalog lists canonical answers for things like "what is activation?", "who owns growth experiments?", "what is the current pricing tier?" Any artifact claim that can't be traced to a source of truth or an Onyx citation fails the gate. Anomalies the system has detected for the period must be explicitly acknowledged in the artifact.

Artifact trust. The composite export_readiness score, gated at the database level. This is the final arbiter of "is this output allowed out of the system?"

These four scores roll up into workspace dashboards that read less like analytics and more like health vitals. A PM glancing at the console should be able to tell, in three seconds, which skill is on thin ice and why.

4.6 The promotion engine
text
current_active_prompt_version  ←──  eval_round_N(score=0.88)
                                         │
                                         ▼
           new_candidate_prompt  ───▶ eval_round_N+1(score=0.93)
                                         │
                                         │  PromotionGate.decide(
                                         │    new_score=0.93,
                                         │    previous_score=0.88,
                                         │    regression_failures=[],   ← key
                                         │    canary_failures=[c1],     ← non-blocking
                                         │  )
                                         │
                                         ▼
                                    promotable=True
                                         │
                                         ▼
                     deactivate_old + activate_new  (single transaction)
                                         │
                                         ▼
                                   changelog appended
The critical detail: any gold regression failure blocks promotion, even if the main score goes up. The instinct to chase a higher number is the enemy of long-term trust. Regression gold examples are the immune system. They don't get sacrificed for a delta.

Canary failures, by contrast, are alerts — something is shifting in a way worth watching — but don't block. Noise in the immune system is worse than a missed alarm.

4.7 The publishing substrate
Every publish passes through three enforcement layers:

Skill layer (Python): hard-gate eval + export-readiness composite.

Guard layer (Python): PublishGuard.check() in the API route.

Database trigger (SQL): a BEFORE INSERT trigger on publish_log that refuses rows where the cited output's export_readiness is below the workspace threshold.

Application bugs cannot bypass this. A rogue cron job cannot bypass this. A teammate with direct database access would have to explicitly drop the trigger, and that shows up in audit.

Below that, the publish queue is Redis-backed and keyed by (workspace_id, output_id, destination_ref) as an idempotency key enforced by a unique index. Republishing the same output to the same destination is a no-op that returns the existing receipt. Rollback is a first-class operation: every receipt has a rollback() path that the adapter implements.

4.8 Multi-tenancy
Multi-tenancy is not "we added a workspace_id column." It's an invariant enforced at three levels:

Application: every request resolves a workspace_id from auth and sets it on the SQLAlchemy session.

Database: every tenant table has a Row-Level Security policy keyed on the GUC current_setting('dreamfi.workspace_id'). A query run without the GUC set returns zero rows. A query run with the wrong workspace returns zero rows. This is tested.

Onyx: every document DreamFi ingests is tagged with the owning workspace_id. Every search is filtered on that tag, enforced in the OnyxClient wrapper.

The threat model explicitly includes "malicious Python" and "operator mistake." The answer to both is: RLS.

5. Data model, at a glance
Grouped by concern. All tables are tenant-scoped unless otherwise noted.

Core skill + eval lifecycle
skill_types (global) · workspace_skills · prompt_versions · eval_rounds · eval_outputs · gold_examples · gold_drift_events

Trust
sot_catalog · anomalies · artifact_claims · metric_catalog · metric_definition_versions · metric_snapshots · metric_discrepancies · planning_trust_reports · ambiguity_flags

Publishing
oauth_connections · publish_jobs · publish_log · approval_requests

Tenancy + identity
workspaces · users · workspace_members · api_keys

Telemetry (materialized views)
workspace_daily_cost · skill_health_snapshot · trust_rollup

The full schema is too large to paste here but is owned by Alembic migrations under dreamfi/db/migrations/versions/. The invariants are: every tenant table starts with workspace_id, every decision-relevant table is append-only (we don't edit history, we add rows), every receipt is immutable.

6. How DreamFi feels to use
Three vignettes. If we build this right, these happen.

6.1 The PM before the exec review
It's Sunday night. The PM has to produce a weekly product brief for Monday morning. They open Slack in the #product channel, thread up the last week of standups, and type:

text
/dreamfi planning_weekly_brief :thread
DreamFi reads the thread, calls Onyx to pull in linked docs and the last week of Jira motion, runs the hygiene probes, drafts a brief, runs it against the locked eval and the regression gold set, scores it, and posts back into the thread:

Planning Weekly Brief — draft v3 (model: claude-opus-4-7)
Export readiness: 0.82 (threshold 0.80 ✓)
Hard gate: pass (12/12)
Gold regressions: 5/5 ✓
Flags raised: 4 items missing owners, 2 stale > 14d, 1 RAG-green with no activity in 21d

[Approve] [Show alternatives] [Revise] [Why these scores?]

The PM clicks "Why these scores?" and sees every claim traced to either a Confluence page, a Jira issue, or a metric catalog entry. They click "Approve." DreamFi publishes the brief to Confluence as a draft page under the exec review space, with inline Confluence comments on each flag linking back to the responsible owner.

Monday morning, the exec opens the page. Every number is clickable. Every flag is annotated. They don't have to trust the PM's judgment; they can audit it in ten seconds and spend their time on the decisions.

6.2 The founder catching drift
Six months in, the founder opens the console. Normally the planning trust dashboard is 0.91. This week it's 0.74. Three skills have canary warnings. One regression gold example for cold_email flipped from pass to fail this morning.

They click the regression. The diff viewer shows exactly what changed: the old prompt referenced the customer's Jira history; the new prompt produced by an overnight autoresearch loop drifted toward marketing-speak and dropped the personalization. The promotion gate caught it — the new version was blocked, the old one is still active. No customer ever saw the bad version.

They click "Accept regression as new baseline" (requires written justification) or "Retire the candidate" (one click). The system moves on. No firefight.

6.3 The skeptic who audits
The VP of Engineering doesn't trust AI-generated content. Fine. They open any artifact in the console and hit "Audit view." They see:

The exact prompt, model, temperature, and retrieval query used.

The retrieved Onyx chunks, ranked by the score the model saw.

Every tool call made, in order, with args and results.

The critic's verdict and whether a revision happened.

Every criterion in the eval, pass/fail, with the line of output that triggered each verdict.

Every claim, with its source.

The reviewer signature and timestamp.

They look for a reason to distrust it. They don't find one. They send the artifact to their team.

Trust, earned once, compounds.

7. The moat
Why this is hard to copy, even if the idea is obvious.

Locked evals with history. Every competitor that builds this later starts with zero round data. We build compounding ground truth starting the day we ship. The value of an eval is not the eval — it's the thousand rounds of it you've run.

Trust surfaces, not features. "Generate a meeting summary" is a feature anyone can copy. "Refuse to publish a meeting summary that cites a metric with a blocking cross-source discrepancy" is a system property. It requires the catalog, the snapshotter, the discrepancy detector, the structured output contract, and the DB trigger to all exist and interoperate. That is months of work that compounds, not weeks of work that commoditizes.

Gold-regression discipline. A PM team that has built three months of gold regressions for meeting_summary has an asset a competitor cannot replicate by throwing tokens at it. These are judgments, frozen. They are what a team believes "good" means. No amount of scale buys this.

The connector fan-out is rented. We use Onyx. We don't compete on connectors. Our edge is above retrieval — in measurement, gating, and publishing. That's a deliberate, narrow, durable choice.

The database is boring. A lot of AI systems fail because their data model is held together by optimism. Ours is Postgres with triggers, constraints, RLS, and append-only logs. Boring data models outlive exciting ones.

8. What we will refuse to do
These "no"s are load-bearing.

No binary trust scores that aren't decomposable. Every score answers "why?" at one click.

No publish path without an approval record. Even auto-approval is a row with a policy ID.

No prompt change without a round. Even a typo fix runs the regression set.

No single-tenant code paths "for demo." If it ships, it's multi-tenant.

No LLM-as-judge without calibration. If it's not calibrated against humans, it's not a judge, it's a suggestion.

No hidden model version in production. Every output records the exact model identifier. Provider updates are treated as breaking changes that require a re-eval round before they roll out.

No generation path that can skip evaluation. If there's a "quick draft" mode, it still runs the eval; it just doesn't gate publish on it.

No eval runner that imports anything stateful. Runners are pure functions. This protects the most valuable code in the system.

9. Phase map (where we are, where we're going)
This is a roadmap, not a promise. Dates are deliberately absent.

Phase 0: Foundations ✅ merged
Onyx substrate, skill registry, eval runner wrapper, skill engine, promotion gate, publish guard, CLI, operator console. Nine skills registered. 47 tests green.

Phase T0: Gold optimization loop 🔨 in progress
Gold example roles, regression immune system, drift events, export-readiness composite. First trust score visible.

Phase T1: Planning trust
Jira + Dragonboat probes, hygiene score, taxonomy coverage, planning_weekly_brief and hygiene_audit skills.

Phase T2: Metric trust
Catalog, snapshots, cross-source discrepancy detection, weekly_metric_brief skill.

Phase T3: Interpretation trust
Source-of-truth catalog, anomaly detectors, claim-grounding enforcement.

Phase T4: Artifact trust + DB-level export gate
Composite score fully wired, Postgres trigger enforced, breakdown visible on every output.

Phase T5: UI-support trust
requirements_capture, handoff_package, ui_copy_variants.

Phase P8: Multi-tenancy (trust-scoped)
Workspaces, RLS, API keys, workspace-tagged Onyx. Enables the above to be productized.

Phase P10: Structured outputs + critic loop
Pydantic contracts everywhere, cheap-critic revisions, self-consistency for hard skills.

Phase P11: Agentic tool use via Onyx MCP
Bounded tool loops, per-skill tool policies, full traces.

Phase P9: Trust-cost model router
LiteLLM gateway, pinned model versions for trust-critical skills, cost tracking.

Phase P12–P15: Publishing + approvals
Confluence, Notion, Jira, Slack. OAuth broker. Idempotent queue. Diff + rollback UX.

Phase P16: Productization polish
Onboarding, webhooks, rate limits, status page, YAML skill-config import/export.

We'll ship roughly in that order. T0 is the gate to every T that follows. T4 is the gate to every publishing capability that follows. Everything else is parallelizable.

10. How to contribute
If you've read this far, you get it. A few things to know:

TDD or nothing. Every module gets a test first. One happy path, one error path, one edge case. Run make test before every commit.

Locked means locked. evals/ is immutable. Templates and runners don't get "improved." They get new versions with new files.

Mypy strict, ruff clean. No exceptions, no # type: ignore, no noqa without an ADR reference.

Onyx only through dreamfi/onyx/client.py. Anywhere else that imports httpx to talk to Onyx is a bug.

New dependency → new ADR. The ADR answers: what does this replace, what does it cost us, what's the exit plan if it's wrong?

New skill → new locked template, new runner, new contract, five regression examples. No shortcuts.

Read AGENTS.md before your first PR. It's the constitution.

Work happens on feature branches. Each branch ships one phase. Each PR links to the section of this doc that motivates it. If you can't find the section, the feature probably doesn't belong yet.

11. The bet
Language models are commoditizing. Retrieval is commoditizing. Vector stores are commoditizing. The scarce thing in five years will not be model access — it will be systems that know when a model was right.

The teams that win the next decade of AI at work will not be the teams with the best prompts. They'll be the teams with the best measurement of their prompts, their retrievals, their claims, and their decisions — and the discipline to refuse to ship when the measurements say no.

DreamFi is a bet that trust, measured and gated, is the durable surface.

Build accordingly.

Appendix A — Glossary
Skill. A named generator (e.g. meeting_summary) with a locked eval template, runner, output contract, prompt versions, and gold examples.

Hard gate. A binary pass/fail check run on every generated output.

Export readiness. A composite trust score combining hard gate, confidence, gold regression pass rate, claim lineage rate, and freshness. Below threshold = no publish.

Gold example. A curated input/output pair. Roles: exemplar, regression, counter_example, canary.

Drift event. A row emitted when a gold example transitions pass→fail or fail→pass between rounds.

Source of truth (SoT). A canonical reference in the sot_catalog that a generated claim can point to.

Claim. A unit of assertion inside a structured output, carrying either a sot_id, a citation_id, or both.

Metric reference. A structured reference to a metric_catalog entry, with value, as-of-date, and definition version.

Promotion gate. The decision function that moves a prompt version from candidate to active. Refuses on any regression failure.

Publish guard. The enforcement point between approval and adapter. Rechecks eval + export readiness.

Appendix B — Further reading
Demystifying evals for AI agents
 — Anthropic

LLM Evals FAQ
 — Hamel Husain

Error analysis and better prompts
 — Lenny's Newsletter interview with Hamel

Structured Outputs in the API
 — OpenAI

Onyx docs — retrieval substrate

Our own ADR index — the decisions behind the decisions