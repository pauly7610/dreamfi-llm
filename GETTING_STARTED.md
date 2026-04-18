# DreamFi Development Quick Start

Welcome to DreamFi! This guide will help you get started with the platform.

---

## 📋 What's Been Completed

✅ **Database Schema** — PostgreSQL schema with 11 tables, all relationships, indices, and seed data  
✅ **Evaluation System** — 9 locked eval templates + immutable Python runners (agent_system_prompt through short_form_script)  
✅ **Architecture** — Full 5-phase system overview with ADRs  
✅ **Connector Specs** — Detailed specifications for all 11 integrations (Jira, Dragonboat, Confluence, etc.)  
✅ **Service Scaffolds** — Directory structure for all 5 services (knowledge-hub, generators, planning-sync, metrics, ui-support)  
✅ **Documentation** — System overview, connector specs, skill registry, 8 ADRs  
✅ **Test Scaffolds** — Unit test examples and integration test framework

---

## 🚀 Getting Started

### Prerequisites

```bash
# Install Node.js 18+
node --version  # should be v18+

# Install Python 3.9+
python --version  # should be 3.9+

# Install PostgreSQL 15+
psql --version  # should be 15+
```

### Setup Database

```bash
# Create database
createdb dreamfi_knowledge_hub

# Apply schema
psql -d dreamfi_knowledge_hub -f services/knowledge-hub/db/schema.sql

# Verify (should show 11 tables + seed data)
psql -d dreamfi_knowledge_hub -c "\dt"
```

### Setup Environment

```bash
# Copy template
cp .env.example .env

# Edit with your credentials
nano .env

# Required variables:
# DATABASE_URL=postgresql://user:pass@localhost/dreamfi_knowledge_hub
# JIRA_BASE_URL=https://company.atlassian.net
# JIRA_EMAIL=your-email@company.com
# JIRA_API_TOKEN=your-token-here
# DRAGONBOAT_BASE_URL=https://dragonboat.company.com
# DRAGONBOAT_TOKEN=your-token-here
# ANTHROPIC_API_KEY=sk-...
```

### Install Dependencies

```bash
# Services
cd services/knowledge-hub && npm install
cd ../generators && npm install

# Tests
cd ../../tests && pip install pytest pytest-asyncio
```

### Run Eval Runners Locally

```bash
# Test an eval runner
python evals/runners/run_agent_system_prompt_eval.py

# Expected output: JSON with score_percent, passes, failures
```

---

## 📚 Key Files to Review

### Architecture & Strategy

1. **Start here:** `STATUS.md` — Project completion summary
2. **System overview:** `docs/architecture/system-overview.md` — How all 5 phases fit together
3. **Decisions made:** `docs/adr/*` — Why we chose PostgreSQL, hard gates, etc.

### Skill Definitions

1. **All skills:** `docs/architecture/skill-registry.md` — Tier 1, 2, 3 breakdown
2. **Eval criteria:** `evals/*.md` — Hard gates for each skill (locked, don't modify)

### Connector Specifications

1. **All connectors:** `docs/architecture/connector-specs.md` — Auth, sync, freshness for each

### Service READMEs

- `services/knowledge-hub/README.md` — Phase 1
- `services/generators/README.md` — Phase 2
- `services/planning-sync/README.md` — Phase 3
- `services/metrics/README.md` — Phase 4
- `services/ui-support/README.md` — Phase 5

---

## 🛠️ Development Roadmap

### Phase 1: Knowledge Hub (Now → Week 2)

- [ ] Implement Jira connector
- [ ] Implement Dragonboat connector
- [ ] Implement Confluence connector
- [ ] Build retrieval API (search, context, citations)
- [ ] Build confidence scoring

### Phase 2: Generators (Week 2 → Week 3)

- [ ] Implement Tier 1 generator workflows (agent_system_prompt, support_agent, meeting_summary)
- [ ] Wire eval runners to generation pipeline
- [ ] Implement hard-gate publishing (fail/pass logic)
- [ ] Setup automation to track prompt versions

### Phase 3: Planning (Week 3 → Week 4)

- [ ] Implement Jira/Dragonboat field mapping
- [ ] Build report_summary skill eval
- [ ] Build report_escalation skill eval
- [ ] Add validation rules (no orphans, etc.)

### Phase 4: Metrics (Week 4+)

- [ ] Implement Metabase adapter
- [ ] Implement PostHog adapter
- [ ] Build snapshot generation
- [ ] Wire narrative skills (internal, exec, external)

### Phase 5: UI Support (Week 4+)

- [ ] Build style constraint checker
- [ ] Implement export-readiness validator
- [ ] Wire artifact→skill mapping
- [ ] Create publishing to Confluence/Jira

---

## 🧪 Testing Philosophy

### Eval Runners Are Locked

The eval runners (`evals/runners/run_*.py`) implement immutable scoring logic. They define ground truth for skill evaluation:

```python
# These runners are LOCKED - do not modify after creation
# Score improvements are the ONLY signal for keeping prompt changes
# Regressions automatically revert to previous prompt
```

### Only Score Improvement Promotes Prompts

```
IF score_new > score_previous + 2.0% THEN
  promote prompt_version to active
ELSE IF score_new < score_previous THEN
  revert to previous version AND log regression
```

### Test Structure

```
tests/
├── unit/               # Fast, isolated tests
│   ├── connectors/     # Connector interface tests
│   ├── knowledge/      # Retrieval, confidence tests
│   ├── generators/     # Skill logic tests (heuristic-based)
│   ├── metrics/        # Metric scoring tests
│   └── ...
├── integration/        # Service-level tests
│   ├── connectors/     # Real connector sync tests
│   ├── evals/          # Eval runner locking tests
│   └── ...
└── e2e/               # Full workflow tests (to be added)
```

---

## 🔄 Development Workflow

### For Connector Implementation

1. Review specs in `docs/architecture/connector-specs.md`
2. Implement methods:
   - `connect()` — Authenticate with external system
   - `disconnect()` — Tear down connection
   - `fetchRaw(watermark)` — Async generator that yields raw payloads
   - `normalize(payload)` — Convert to NormalizedEntity
3. Test locally with mock data
4. Add retry logic (base class provides helpers)
5. Test against real API with limited data

### For Generator Implementation

1. Review skill eval in `evals/{skill}.md`
2. Create initial prompt in `services/generators/src/templates/{skill}.txt`
3. Test prompt locally with Claude API
4. Generate 10 outputs per test input (30 total)
5. Run eval runner: `python evals/runners/run_{skill}_eval.py`
6. If score > previous: promote; if regression: revert

### For Test Writing

1. Create test file in `tests/{unit|integration}/{component}/test_*.py`
2. Use pytest framework
3. Mock external services where needed
4. Run: `pytest tests/{unit|integration}/{component}/test_*.py -v`

---

## 🐛 Common Issues & Solutions

### Database Connection Error

```
Error: "connection refused" or "role 'postgres' does not exist"

Solution:
1. Verify PostgreSQL is running: `psql --version`
2. Check DATABASE_URL in .env
3. Try: `createdb dreamfi_knowledge_hub` (may already exist)
```

### Eval Runner Fails

```
Error: "ImportError: No module named 'evals'"

Solution:
1. Ensure you're in the project root directory
2. Add project root to PYTHONPATH: `export PYTHONPATH="${PYTHONPATH}:$(pwd)"`
3. Run eval from project root: `python evals/runners/run_agent_system_prompt_eval.py`
```

### Connector Auth Fails

```
Error: "401 Unauthorized" when syncing Jira

Solution:
1. Verify JIRA_EMAIL and JIRA_API_TOKEN in .env
2. Test auth locally: `curl -u email@gmail.com:token https://company.atlassian.net/rest/api/3/myself`
3. Check token hasn't expired in Jira console
```

---

## 📞 Getting Help

1. **Architecture questions** → Review `docs/adr/*`
2. **Skill definitions** → See `docs/architecture/skill-registry.md`
3. **Connector specs** → Check `docs/architecture/connector-specs.md`
4. **Test examples** → Look in `tests/{unit|integration}/`
5. **Eval criteria** → Read `evals/{skill}.md`

---

## 🎯 Success Criteria

The platform is successful when:

✅ User can ask product question → get cited answer with confidence score  
✅ Tier 1 generators ship with locked evals  
✅ Score improvements automatically promote prompts  
✅ Regressions automatically revert  
✅ Dashboards show trust scores for all outputs  
✅ All 11 connectors sync fresh data  
✅ Reporting is deterministic (same input → same output)

---

## 📖 Further Reading

- PostgreSQL docs: https://www.postgresql.org/docs/15/
- Anthropic Claude API: https://platform.openai.com/docs/
- TypeScript generics: https://www.typescriptlang.org/docs/handbook/2/generics.html
- Python async/await: https://docs.python.org/3/library/asyncio.html

---

**Last Updated:** 2026-04-17  
**Ready for Development:** YES ✅  
**Next Step:** Begin Phase 1 connector implementation
