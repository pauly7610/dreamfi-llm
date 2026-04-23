"""C3: ContextBuilder behavior with mocked connectors + FakeModelRouter."""
from __future__ import annotations

import re
from pathlib import Path

import httpx
import pytest
import respx
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from dreamfi.connectors.confluence import ConfluenceClient
from dreamfi.connectors.jira import JiraClient
from dreamfi.context.builder import (
    ClaimDistillation,
    ClaimDraft,
    ConnectorRegistry,
    ContextBuilder,
    OpenQuestionDraft,
)
from dreamfi.context.model_router import ContextStructuringError, FakeModelRouter
from dreamfi.context.topics import TopicHint
from dreamfi.db.models import Base, TopicRelationRow, TopicRow

JIRA_URL = "https://acme.atlassian.net"
CONF_URL = "https://acme.atlassian.net"


def _jira() -> JiraClient:
    return JiraClient(base_url=JIRA_URL, email="p", api_token="t")


def _conf() -> ConfluenceClient:
    return ConfluenceClient(base_url=CONF_URL, email="p", api_token="t")


def _mock_jira_epic_children(epic_key: str, issue_keys: list[str]) -> None:
    respx.get(f"{JIRA_URL}/rest/api/3/search").mock(
        return_value=httpx.Response(
            200,
            json={
                "issues": [
                    {
                        "key": k,
                        "fields": {
                            "summary": f"summary for {k}",
                            "status": {"name": "In Progress"},
                            "issuetype": {"name": "Task"},
                            "parent": {"key": epic_key},
                        },
                    }
                    for k in issue_keys
                ],
                "total": len(issue_keys),
            },
        )
    )
    respx.get(re.compile(f"{JIRA_URL}/rest/api/3/issue/.*/changelog")).mock(
        return_value=httpx.Response(200, json={"values": []})
    )


def _mock_confluence_search(pages: list[dict[str, str]]) -> None:
    respx.get(f"{CONF_URL}/wiki/rest/api/search").mock(
        return_value=httpx.Response(
            200,
            json={
                "results": [
                    {"content": {"id": p["id"], "type": "page", "title": p["title"]}}
                    for p in pages
                ]
            },
        )
    )


@respx.mock
def test_builder_with_epic_hint_uses_jira_and_skips_confluence() -> None:
    _mock_jira_epic_children("ACT-321", ["ACT-410", "ACT-411"])
    conf_route = respx.get(f"{CONF_URL}/wiki/rest/api/search").mock(
        return_value=httpx.Response(200, json={"results": []})
    )

    llm = FakeModelRouter(
        responses={
            "ACT-410": ClaimDistillation(
                claims=[
                    ClaimDraft(
                        statement="ACT-410 is in progress",
                        source_refs=["jira:ACT-410"],
                        confidence=0.8,
                    )
                ]
            )
        }
    )
    builder = ContextBuilder(
        connectors=ConnectorRegistry(jira=_jira(), confluence=_conf()),
        llm=llm,
    )

    bundle = builder.build(
        workspace_id="w1",
        topic="onboarding redesign",
        topic_hint=TopicHint(epic_key="ACT-321"),
    )

    # Jira fan-out ran, Confluence did not.
    assert conf_route.call_count == 0
    assert {s.source_type for s in bundle.sources} == {"jira"}
    assert {s.source_id for s in bundle.sources} == {"ACT-410", "ACT-411"}
    # Entities are deduplicated at (type, entity_id).
    entity_keys = {(e.entity_type, e.entity_id) for e in bundle.entities}
    assert entity_keys == {("issue", "ACT-410"), ("issue", "ACT-411")}
    assert bundle.claims[0].citation_ids == ["jira:ACT-410"]
    assert bundle.coverage_score > 0.0


@respx.mock
def test_builder_without_hint_runs_confluence_too() -> None:
    respx.get(f"{JIRA_URL}/rest/api/3/search").mock(
        return_value=httpx.Response(200, json={"issues": [], "total": 0})
    )
    _mock_confluence_search([{"id": "18432", "title": "Onboarding v3"}])

    llm = FakeModelRouter(
        responses={
            "Onboarding v3": ClaimDistillation(
                claims=[
                    ClaimDraft(
                        statement="Onboarding v3 is the current design doc",
                        source_refs=["confluence:18432"],
                        confidence=0.7,
                    )
                ]
            )
        }
    )
    builder = ContextBuilder(
        connectors=ConnectorRegistry(jira=_jira(), confluence=_conf()),
        llm=llm,
    )
    bundle = builder.build(workspace_id="w1", topic="onboarding")
    source_types = {s.source_type for s in bundle.sources}
    assert "confluence" in source_types


@respx.mock
def test_builder_raises_structuring_error_on_bad_llm() -> None:
    _mock_jira_epic_children("ACT-1", ["ACT-100"])
    # Empty responses -> FakeModelRouter raises ContextStructuringError.
    builder = ContextBuilder(
        connectors=ConnectorRegistry(jira=_jira()),
        llm=FakeModelRouter(responses={}),
    )
    with pytest.raises(ContextStructuringError):
        builder.build(
            workspace_id="w1",
            topic="x",
            topic_hint=TopicHint(epic_key="ACT-1"),
        )


@respx.mock
def test_builder_dedups_entities_across_sources() -> None:
    # Same entity surfaced twice; builder dedups to one node.
    respx.get(f"{JIRA_URL}/rest/api/3/search").mock(
        return_value=httpx.Response(
            200,
            json={
                "issues": [
                    {
                        "key": "ACT-1",
                        "fields": {
                            "summary": "s",
                            "status": {"name": "To Do"},
                            "issuetype": {"name": "Task"},
                            "issuelinks": [
                                {
                                    "type": {"name": "Blocks"},
                                    "outwardIssue": {"key": "ACT-2"},
                                }
                            ],
                        },
                    },
                    {
                        "key": "ACT-1",  # duplicate
                        "fields": {
                            "summary": "s",
                            "status": {"name": "To Do"},
                            "issuetype": {"name": "Task"},
                        },
                    },
                ],
                "total": 2,
            },
        )
    )
    respx.get(re.compile(f"{JIRA_URL}/rest/api/3/issue/.*/changelog")).mock(
        return_value=httpx.Response(200, json={"values": []})
    )

    llm = FakeModelRouter(
        responses={
            "ACT-1": ClaimDistillation(
                claims=[ClaimDraft(statement="x", source_refs=["jira:ACT-1"])]
            )
        }
    )
    builder = ContextBuilder(
        connectors=ConnectorRegistry(jira=_jira()),
        llm=llm,
    )
    bundle = builder.build(
        workspace_id="w1",
        topic="ACT-1",
        topic_hint=TopicHint(epic_key="ACT-1"),
    )
    entity_ids = [e.entity_id for e in bundle.entities]
    assert entity_ids.count("ACT-1") == 1


@respx.mock
def test_build_and_link_attaches_entities_to_topic_graph(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path}/dreamfi.db")
    Base.metadata.create_all(engine)
    session = Session(engine)

    _mock_jira_epic_children("ACT-321", ["ACT-410"])

    llm = FakeModelRouter(
        responses={
            "ACT-410": ClaimDistillation(
                claims=[
                    ClaimDraft(statement="x", source_refs=["jira:ACT-410"])
                ],
                open_questions=[
                    OpenQuestionDraft(
                        question="Is EU rollout gated on legal?",
                        why_open="no_source",
                    )
                ],
            )
        }
    )
    builder = ContextBuilder(
        connectors=ConnectorRegistry(jira=_jira()),
        llm=llm,
        session=session,
    )

    _, resolution = builder.build_and_link(
        workspace_id="w1",
        topic="onboarding redesign",
        topic_hint=TopicHint(epic_key="ACT-321"),
    )
    assert resolution.type == "epic"

    topics = list(session.scalars(select(TopicRow).where(TopicRow.workspace_id == "w1")))
    # Source epic + ACT-410 issue node.
    assert len(topics) == 2
    edges = list(session.scalars(select(TopicRelationRow)))
    assert len(edges) == 1
    assert edges[0].from_id == resolution.topic_id
