import pytest
from unittest.mock import Mock, patch, MagicMock
from services.generators.engine import GeneratorEngine
from services.generators.forms import (
    TechnicalPRDForm,
    BusinessPRDForm,
    RiskAssessmentForm,
    SponsorBankForm,
    DiscoveryForm,
    EpicBuilderForm,
)
from services.generators.templates import TemplateEngine
from services.generators.confluence_output import ConfluencePublisher
from services.generators.jira_helper import JiraHelper


@pytest.fixture
def engine():
    return GeneratorEngine()


@pytest.fixture
def template_engine():
    return TemplateEngine()


@pytest.fixture
def confluence_publisher():
    return ConfluencePublisher()


@pytest.fixture
def jira_helper():
    return JiraHelper()


class TestGeneratorEngine:
    def test_generate_technical_prd(self, engine):
        form_data = {
            "title": "API Redesign",
            "problem_statement": "Current API is slow",
            "proposed_approach": "Implement caching",
            "target_users": "Backend teams",
            "success_metrics": ["P99 latency < 100ms", "Cache hit rate > 80%"],
            "technical_constraints": "Must be backward compatible",
            "data_model_changes": "Add cache table",
            "api_changes": "New cache headers",
        }

        with patch.object(engine, "_call_llm") as mock_llm:
            mock_llm.return_value = """
## Problem Statement
Current API is too slow for downstream services.

## Hypothesis
Adding caching will improve performance.

## Proposed Approach
Implement Redis cache layer.

## System Components
- API Gateway
- Redis Cache
- Database

## API Changes
Add X-Cache-Control header.

## Data Model Changes
Add cache_metadata table.

## Edge Cases
Handle cache invalidation correctly.

## Success Metrics
- P99 latency < 100ms
- Cache hit rate > 80%

## Risks
Cache coherence issues.
"""
            result = engine.generate_doc("technical_prd", form_data)

        assert result["generator_type"] == "technical_prd"
        assert result["title"] == "API Redesign"
        assert "Problem Statement" in result["sections"]
        assert result["valid"] is True

    def test_generate_business_prd(self, engine):
        form_data = {
            "title": "Expand to EU",
            "business_context": "Growing demand in EU market",
            "market_opportunity": "€50M TAM in EU",
            "target_users": "EU financial institutions",
            "revenue_impact_description": "€5M ARR potential",
            "proposed_solution": "Open EU subsidiary",
            "success_metrics": ["Launch by Q3", "€1M ARR by year-end"],
            "key_stakeholders": ["CEO", "CFO", "Legal"],
            "timeline_estimate_weeks": 16,
        }

        with patch.object(engine, "_call_llm") as mock_llm:
            mock_llm.return_value = """
## Hypothesis
EU market is ready for our solution.

## Business Context
Strong demand signals from prospects.

## Market Opportunity
€50M TAM, 10% penetration = €5M.

## Target Users
Mid-market financial institutions.

## Revenue Impact
€5M ARR potential within 18 months.

## Proposed Solution
Establish EU subsidiary in Dublin.

## Success Metrics
- Launch by Q3 2024
- €1M ARR by year-end

## Stakeholders
CEO (sponsor), CFO (budget), Legal (compliance).

## Timeline
16 weeks to launch.

## Risks
Regulatory delays in specific countries.
"""
            result = engine.generate_doc("business_prd", form_data)

        assert result["generator_type"] == "business_prd"
        assert result["title"] == "Expand to EU"
        assert "Market Opportunity" in result["sections"]

    def test_generate_risk_assessment(self, engine):
        form_data = {
            "vendor_name": "Cloud Storage Inc",
            "service_type": "Document Storage",
            "data_categories": ["PII", "Financial Records"],
            "regulatory_frameworks": ["SOC2", "GDPR"],
            "security_requirements": "AES-256 encryption, SSO",
            "integration_approach": "API integration",
            "data_retention_days": 365,
            "exit_strategy_description": "Data export in 30 days",
            "monitoring_approach": "Monthly audits",
        }

        with patch.object(engine, "_call_llm") as mock_llm:
            mock_llm.return_value = """
## Vendor Overview
Established vendor with 10+ years in market.

## Service Type & Data Categories
Document storage service handling PII and financial records.

## Regulatory Frameworks
Compliant with SOC2 Type II and GDPR.

## Security Controls
AES-256 encryption, SSO, IP whitelisting.

## Risk Assessment
Low risk given vendor maturity.

## Monitoring Approach
Monthly SOC2 audits, quarterly penetration tests.

## Data Retention
Data retained for 365 days, then deleted.

## Exit Strategy
Full data export available within 30 days.
"""
            result = engine.generate_doc("risk_assessment", form_data)

        assert result["generator_type"] == "risk_assessment"
        assert result["valid"] is True
        assert "Vendor Overview" in result["sections"]

    def test_generate_sponsor_bank(self, engine):
        form_data = {
            "bank_name": "Chase Bank",
            "bank_routing_number": "021000021",
            "integration_scope": "ACH and wire transfers",
            "regulatory_requirements": ["AML", "KYC", "BSA"],
            "transaction_types": ["ACH Credit", "ACH Debit", "Wire Transfer"],
            "settlement_window_hours": 24,
            "daily_volume_limit_cents": 100000000,
            "sla_uptime_percentage": 99.99,
            "incident_response_sla_minutes": 30,
            "compliance_contacts": ["compliance@chase.com"],
        }

        with patch.object(engine, "_call_llm") as mock_llm:
            mock_llm.return_value = """
## Bank Overview
Chase Bank - largest US bank by assets.

## Integration Scope
ACH and wire transfers via dedicated API.

## Regulatory Requirements
Full AML, KYC, and BSA compliance required.

## Transaction Types
ACH Credit, ACH Debit, and wire transfers supported.

## Settlement Approach
T+1 settlement for ACH, same-day for wires.

## Compliance Controls
Real-time monitoring, daily reconciliation.

## SLA Requirements
99.99% uptime, 30-minute incident response.

## Reporting Requirements
Daily settlement reports, monthly reconciliation.

## Incident Response
Critical: <15 min, Major: <30 min, Minor: <4 hours.
"""
            result = engine.generate_doc("sponsor_bank", form_data)

        assert result["generator_type"] == "sponsor_bank"
        assert "Settlement Approach" in result["sections"]

    def test_generate_discovery(self, engine):
        form_data = {
            "problem_area": "User onboarding friction",
            "research_questions": ["Why do users drop off?", "Where's the biggest friction?"],
            "user_segments": ["SMB", "Enterprise"],
            "data_sources": ["User interviews", "Analytics", "Support tickets"],
            "hypotheses": ["KYC process too complex", "Documentation unclear"],
            "evidence_summary": "70% of dropoffs occur at KYC step",
            "opportunity_size_description": "Reducing dropoff by 10% = $1M ARR",
            "recommendation": "Simplify KYC flow",
        }

        with patch.object(engine, "_call_llm") as mock_llm:
            mock_llm.return_value = """
## Problem Area
New users drop off during onboarding, especially at KYC step.

## Research Questions
1. Why do users abandon during onboarding?
2. Where is the biggest friction point?
3. What would reduce dropoff most?

## User Segments
SMB (1-100 users) and Enterprise (>100 users).

## Hypotheses
- KYC process too complex for users
- Documentation lacks clarity
- Mobile experience inferior to desktop

## Evidence Summary
Analyzed 500 user sessions: 70% dropped at KYC.

## Opportunity Size
Reducing dropoff by 10% = $1M additional ARR.

## Recommendation
Simplify KYC flow via multi-step progressive profiling.

## Next Steps
A/B test simplified flow with 10% of traffic.
"""
            result = engine.generate_doc("discovery", form_data)

        assert result["generator_type"] == "discovery"
        assert result["valid"] is True

    def test_generate_epic_builder(self, engine):
        form_data = {
            "epic_key": "PROJ-123",
            "epic_summary": "Implement payment reconciliation",
            "epic_description": "Build automated reconciliation system",
            "acceptance_criteria": ["Daily reconciliation runs", "99% accuracy"],
            "story_count_estimate": 8,
            "story_point_estimate": 55,
            "priority": "high",
            "team": "Platform",
            "dependencies": ["PROJ-100"],
            "success_metrics": ["Daily reconciliation automated"],
        }

        with patch.object(engine, "_call_llm") as mock_llm:
            mock_llm.return_value = """
## Epic Summary
Implement payment reconciliation system for automated daily settlement.

## Epic Description
Build end-to-end reconciliation pipeline handling ACH and wire transfers.

## Success Criteria
- Daily reconciliation runs without manual intervention
- 99% reconciliation accuracy achieved
- All discrepancies flagged within 1 hour

## User Stories
1. As a Platform engineer, I want to ingest settlement files
2. As a QA analyst, I want to validate reconciliation results
3. As an Ops user, I want to see reconciliation dashboard

## Dependencies
PROJ-100 (Payment routing system setup)

## Risks
Large data volumes may impact performance.
"""
            result = engine.generate_doc("epic_builder", form_data)

        assert result["generator_type"] == "epic_builder"
        assert "Epic Summary" in result["sections"]

    def test_template_validation_pass(self, template_engine):
        output = {
            "Problem Statement": "Test problem",
            "Hypothesis": "Test hypothesis",
            "Proposed Approach": "Test approach",
            "System Components": "Test components",
            "API Changes": "Test API",
            "Data Model Changes": "Test model",
            "Edge Cases": "Test edges",
            "Success Metrics": "Test metrics",
            "Dependencies": "Test deps",
            "Risks": "Test risks",
        }

        valid, errors = template_engine.validate_output(output, "technical_prd")
        assert valid is True
        assert len(errors) == 0

    def test_template_validation_missing_sections(self, template_engine):
        output = {"Problem Statement": "Test"}

        valid, errors = template_engine.validate_output(output, "technical_prd")
        assert valid is False
        assert len(errors) > 0

    def test_confluence_publisher_build_body(self, confluence_publisher):
        doc_dict = {
            "title": "Test Document",
            "generator_type": "technical_prd",
            "sections": {
                "Problem": "We have a problem",
                "Solution": "We have a solution",
            }
        }

        body = confluence_publisher._build_confluence_body(doc_dict)
        assert "technical_prd" in body or "Test Document" in body
        assert "Problem" in body
        assert "Solution" in body

    def test_jira_helper_format_story(self, jira_helper):
        story_data = {
            "title": "Add user authentication",
            "description": "Implement JWT-based auth",
            "acceptance_criteria": [
                "Users can login",
                "Tokens expire after 1 hour",
            ]
        }

        formatted = jira_helper.format_as_jira_story(story_data)
        assert "Add user authentication" in formatted
        assert "Users can login" in formatted
        assert "Tokens expire after 1 hour" in formatted

    def test_jira_helper_template(self, jira_helper):
        template = jira_helper.get_story_template()
        assert "As a" in template
        assert "I want" in template
        assert "So that" in template
        assert "Acceptance Criteria" in template

    @patch("services.generators.engine.httpx.Client.get")
    def test_retrieve_knowledge_context(self, mock_get, engine):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "documents": [
                {"title": "Doc1", "summary": "Summary1"},
                {"title": "Doc2", "summary": "Summary2"},
            ]
        }
        mock_get.return_value = mock_response

        context = engine._retrieve_knowledge_context("test query")
        assert context is not None
        assert "documents" in context
        assert len(context["documents"]) == 2

    def test_retrieve_knowledge_context_failure(self, engine):
        with patch("services.generators.engine.httpx.Client.get") as mock_get:
            mock_get.side_effect = Exception("Connection error")
            context = engine._retrieve_knowledge_context("test query")
            assert context is None

    def test_pydantic_form_validation_technical_prd(self):
        form = TechnicalPRDForm(
            title="Test",
            problem_statement="This is a problem",
            proposed_approach="This is an approach",
            target_users="Engineers",
            success_metrics=["Metric 1"],
        )
        assert form.title == "Test"
        assert len(form.success_metrics) == 1

    def test_pydantic_form_validation_business_prd(self):
        form = BusinessPRDForm(
            title="Test",
            business_context="Market context",
            market_opportunity="Market opportunity",
            target_users="Users",
            revenue_impact_description="Revenue impact",
            proposed_solution="Solution",
            success_metrics=["Metric"],
            key_stakeholders=["CEO"],
            timeline_estimate_weeks=8,
        )
        assert form.timeline_estimate_weeks == 8

    def test_pydantic_form_validation_invalid_timeline(self):
        with pytest.raises(Exception):
            BusinessPRDForm(
                title="Test",
                business_context="Context",
                market_opportunity="Opportunity",
                target_users="Users",
                revenue_impact_description="Impact",
                proposed_solution="Solution",
                success_metrics=["Metric"],
                key_stakeholders=["CEO"],
                timeline_estimate_weeks=0,
            )

    def test_generate_multiple_documents(self, engine):
        configs = [
            {
                "type": "technical_prd",
                "form_data": {
                    "title": "PRD 1",
                    "problem_statement": "Problem",
                    "proposed_approach": "Approach",
                    "target_users": "Users",
                    "success_metrics": ["Metric"],
                }
            },
        ]

        with patch.object(engine, "generate_doc") as mock_gen:
            mock_gen.return_value = {
                "generator_type": "technical_prd",
                "valid": True,
                "sections": {},
            }
            results = engine.generate_multiple(configs)

        assert len(results) == 1
        assert results[0]["valid"] is True
