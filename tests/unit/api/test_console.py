from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from dreamfi.api.app import create_app
from dreamfi.api.deps import get_db_session
from dreamfi.db.models import Base, ConsoleTopic, EvalOutput, EvalRound, PromptVersion, PublishLog, Skill
from dreamfi.skills.registry import seed_registry

REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def session(tmp_path: Path) -> Session:
    engine = create_engine(f"sqlite:///{tmp_path}/dreamfi.db")
    Base.metadata.create_all(engine)
    session = Session(engine)
    seed_registry(session, repo_root=REPO_ROOT)
    session.add(
        PromptVersion(
            skill_id="meeting_summary",
            version=1,
            template="meeting_summary.jinja",
            system_prompt="You write meeting summaries.",
            is_active=True,
        )
    )
    session.commit()
    return session


@pytest.fixture
def client(session: Session) -> TestClient:
    app = create_app()

    def _session_override():
        yield session

    app.dependency_overrides[get_db_session] = _session_override
    return TestClient(app)


def test_console_api_returns_live_summary(client: TestClient, session: Session) -> None:
    now = datetime.now(timezone.utc)
    prompt_version = session.query(PromptVersion).filter_by(skill_id="meeting_summary").one()
    skill = session.get(Skill, "meeting_summary")
    assert skill is not None

    round_row = EvalRound(
        skill_id="meeting_summary",
        prompt_version_id=prompt_version.prompt_version_id,
        n_inputs=3,
        n_outputs_per_input=2,
        total_outputs=6,
        total_passes=5,
        score=Decimal("0.8800"),
        previous_score=Decimal("0.8400"),
        improvement=Decimal("0.0400"),
        started_at=now,
        completed_at=now,
        artifacts_path="evals/results/meeting-summary/rounds/demo-round",
    )
    session.add(round_row)
    session.flush()

    output = EvalOutput(
        round_id=round_row.round_id,
        test_input_label="weekly-eng-standup",
        attempt=1,
        generated_text="Grounded output",
        criteria_json={"decisions_present": True},
        pass_fail="pass",
        confidence=Decimal("0.910"),
        export_readiness=Decimal("0.870"),
    )
    session.add(output)
    session.flush()

    blocked_output = EvalOutput(
        round_id=round_row.round_id,
        test_input_label="missing-owner-followup",
        attempt=1,
        generated_text="Ungrounded output",
        criteria_json={"decisions_present": False},
        pass_fail="fail",
        confidence=Decimal("0.420"),
        export_readiness=Decimal("0.250"),
    )
    session.add(blocked_output)
    session.flush()

    session.add(
        PublishLog(
            skill_id="meeting_summary",
            prompt_version_id=prompt_version.prompt_version_id,
            output_id=output.output_id,
            destination="confluence",
            destination_ref="exec-review",
            decision="published",
            reason=None,
        )
    )
    session.add(
        ConsoleTopic(
            topic_id="card-disputes",
            title="Card disputes",
            summary="Track dispute spikes across support and fraud evidence.",
            question="Where do card disputes create the most support load?",
            source_ids_json=["jira", "sardine"],
            default_generator_slug="risk-brd",
        )
    )
    session.commit()

    response = client.get('/api/console')

    assert response.status_code == 200
    body = response.json()
    assert body['headline'] == 'Trust, measured.'
    assert body['summary']['skill_count'] >= 1
    assert body['summary']['active_prompt_count'] == 1
    assert body['summary']['average_latest_score'] == 0.88
    assert body['summary']['average_confidence'] == 0.665
    assert body['summary']['average_export_readiness'] == 0.56
    assert body['summary']['publish_success_rate'] == 1.0
    assert body['summary']['hard_gate_pass_rate'] == 0.5
    assert body['summary']['blocked_artifact_count'] == 1
    assert body['summary']['publish_ready_count'] == 0
    assert body['summary']['published_artifact_count'] == 1
    assert body['summary']['needs_review_count'] == 0
    meeting_summary = next(item for item in body['skills'] if item['skill_id'] == 'meeting_summary')
    assert meeting_summary['display_name'] == skill.display_name
    assert meeting_summary['active_prompt_version'] == 1
    assert meeting_summary['latest_round']['round_id'] == round_row.round_id
    assert len(body['artifact_queue']) == 2
    published_artifact = next(item for item in body['artifact_queue'] if item['status'] == 'published')
    blocked_artifact = next(item for item in body['artifact_queue'] if item['status'] == 'blocked')
    assert published_artifact['latest_publish']['decision'] == 'published'
    assert blocked_artifact['latest_publish'] is None
    assert blocked_artifact['policy_checks']['checks'][0]['name'] == 'hard_gate'
    assert blocked_artifact['policy_checks']['checks'][0]['passed'] is False
    assert len(body['alerts']) == 1
    assert body['alerts'][0]['id'] == 'blocked-artifacts'
    assert len(body['quick_actions']) == 6
    assert body['quick_actions'][0]['id'] == 'weekly-brief'
    assert len(body['domain_health']) == 4
    assert {item['domain'] for item in body['domain_health']} == {'planning', 'metrics', 'generation', 'publish'}
    integration_ids = {item['id'] for item in body['integrations']}
    assert {
        'jira',
        'dragonboat',
        'confluence',
        'metabase',
        'posthog',
        'ga',
        'klaviyo',
        'netxd',
        'sardine',
        'socure',
    } <= integration_ids
    jira = next(item for item in body['integrations'] if item['id'] == 'jira')
    assert jira['category'] == 'planning'
    assert 'technical-prd' in jira['used_for']
    assert body['publish_activity'][0]['decision'] == 'published'
    assert len(body['custom_topics']) == 1
    assert body['custom_topics'][0]['id'] == 'card-disputes'
    assert body['custom_topics'][0]['default_generator_slug'] == 'risk-brd'
    assert body['custom_topics'][0]['owner'] == 'unassigned'
    assert body['custom_topics'][0]['status'] == 'discovery'
    assert body['historical_metrics']['7d']['output_count'] == 2
    assert len(body['confidence_calibration']) == 5
    assert body['failure_clusters'][0]['count'] == 1
    assert body['slo_status']['all_met'] is False
    assert len(body['scenario_packs']) == 2


def test_console_topic_create_persists_and_returns_saved_topic(client: TestClient, session: Session) -> None:
    response = client.post(
        '/api/console/topics',
        json={
            'title': 'Card disputes',
            'summary': 'Track dispute spikes across support and fraud evidence.',
            'question': 'Where do card disputes create the most support load',
            'source_ids': ['jira', 'sardine'],
            'default_generator_slug': 'risk-brd',
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body['id'] == 'card-disputes'
    assert body['question'] == 'Where do card disputes create the most support load?'
    assert body['source_ids'] == ['jira', 'sardine']
    assert body['owner'] == 'unassigned'
    assert body['status'] == 'discovery'
    saved_topic = session.get(ConsoleTopic, 'card-disputes')
    assert saved_topic is not None
    assert saved_topic.default_generator_slug == 'risk-brd'


def test_console_metrics_and_simulator_endpoints(client: TestClient) -> None:
    metrics = client.get('/api/console/metrics')
    simulator = client.get('/api/console/simulator')

    assert metrics.status_code == 200
    assert simulator.status_code == 200
    assert 'historical_metrics' in metrics.json()
    assert 'slo_status' in metrics.json()
    assert 'scenarios' in simulator.json()


def test_console_topic_patch_updates_lifecycle_fields(client: TestClient, session: Session) -> None:
    topic = ConsoleTopic(
        topic_id='kyc-conversion',
        title='KYC conversion',
        summary='Investigate KYC conversion.',
        question='What is blocking KYC conversion?',
        source_ids_json=['jira'],
    )
    session.add(topic)
    session.commit()

    response = client.patch(
        '/api/console/topics/kyc-conversion',
        json={
            'owner': 'Product Ops',
            'status': 'in_review',
            'target_decision_at': '2026-05-15T00:00:00Z',
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body['owner'] == 'Product Ops'
    assert body['status'] == 'in_review'
    assert body['target_decision_at'] == '2026-05-15T00:00:00+00:00'


def test_console_favicon_is_served(client: TestClient) -> None:
    response = client.get('/console/favicon.svg')

    assert response.status_code == 200
    assert response.headers['content-type'].startswith('image/svg+xml')
    assert b'<svg' in response.content
    assert b'DreamFi favicon' in response.content


def test_llms_txt_is_served(client: TestClient) -> None:
    response = client.get('/llms.txt')

    assert response.status_code == 200
    assert response.headers['content-type'].startswith('text/plain')
    assert '# DreamFi' in response.text
    assert 'dreamfi.onyx.client.OnyxClient' in response.text
