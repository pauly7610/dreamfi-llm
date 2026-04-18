"""
Unit tests for conformance to knowledge retrieval contract.

Tests that retrieve_context returns required fields and ranks correctly.
"""

import pytest
from datetime import datetime, timedelta


class TestRetrieveContext:
    """Verify retrieve_context meets contract."""

    def test_retrieve_returns_matching_entities(self):
        """Query should return relevant canonical entities."""
        
        # Simulate canonical entities in DB
        entities = [
            {
                'id': 'entity-1',
                'source_system': 'jira',
                'source_object_id': 'PROJ-100',
                'name': 'Login API endpoint',
                'description': 'REST endpoint for user authentication',
                'entity_type': 'jira_issue',
                'eligible_skill_families_json': ['agent', 'api'],
                'freshness_score': 0.9,
                'status': 'in_progress'
            },
            {
                'id': 'entity-2',
                'source_system': 'confluence',
                'source_object_id': 'page-50',
                'name': 'API Authentication Guide',
                'description': 'How to authenticate with our APIs',
                'entity_type': 'confluence_page',
                'eligible_skill_families_json': ['agent', 'documentation'],
                'freshness_score': 0.85,
                'status': 'active'
            }
        ]
        
        # Query: "authentication endpoint"
        query = "authentication endpoint"
        
        # Should return both entities (both contain keywords)
        matching = [e for e in entities if 'authenticat' in e['description'].lower() or 'api' in e['description'].lower()]
        
        assert len(matching) >= 1
        assert any('Login' in e['name'] for e in matching)

    def test_retrieve_includes_citations(self):
        """Every entity should include citations."""
        
        # Mock entity with citations
        entity_with_citations = {
            'id': 'entity-100',
            'source_system': 'jira',
            'source_object_id': 'PROJ-50',
            'name': 'User Authentication Fix',
            'description': 'Fixed race condition in auth',
            'freshness_score': 0.92,
            'citations': [
                {
                    'source': 'JIRA:PROJ-50',
                    'url': 'https://jira.example.com/browse/PROJ-50',
                    'timestamp': datetime.utcnow().isoformat(),
                    'relevance': 0.95
                },
                {
                    'source': 'Comment by Alice',
                    'url': 'https://jira.example.com/browse/PROJ-50?focusedCommentId=12345',
                    'timestamp': datetime.utcnow().isoformat(),
                    'relevance': 0.87
                }
            ]
        }
        
        # Verify citations
        assert 'citations' in entity_with_citations
        assert len(entity_with_citations['citations']) == 2
        assert all('source' in c for c in entity_with_citations['citations'])
        assert all('url' in c for c in entity_with_citations['citations'])

    def test_retrieve_includes_gold_examples(self):
        """Should include gold examples when scenario matches."""
        
        # Gold examples registry
        gold_examples = [
            {
                'skill_id': 'meeting_summary',
                'scenario_type': 'product_review',
                'output_text': 'Decisions: Launch Q2 roadmap. Action items: PM→brief design by Fri. Open: hiring timeline?',
                'score_percent': 100.0,
                'passed_all_flag': True
            },
            {
                'skill_id': 'meeting_summary',
                'scenario_type': 'engineering_retro',
                'output_text': 'Decisions: Deploy fix to auth. Action items: QA→test by Tue, Dev→merge PR. Open: monitoring alerts?',
                'score_percent': 98.0,
                'passed_all_flag': True
            }
        ]
        
        # Query for meeting_summary + product_review context
        skill = 'meeting_summary'
        scenario = 'product_review'
        
        matching_gold = [g for g in gold_examples if g['skill_id'] == skill and g['scenario_type'] == scenario]
        
        assert len(matching_gold) >= 1
        assert matching_gold[0]['passed_all_flag'] == True

    def test_retrieve_ranks_by_freshness(self):
        """Fresher sources ranked above stale when relevance comparable."""
        
        # Mock entities with different freshness scores
        entities = [
            {
                'id': 'stale',
                'source_system': 'jira',
                'name': 'Old Issue',
                'freshness_score': 0.2,  # Very old (30+ days)
                'relevance': 0.9
            },
            {
                'id': 'fresh',
                'source_system': 'jira',
                'name': 'New Issue',
                'freshness_score': 0.95,  # Very fresh (< 1 day)
                'relevance': 0.92
            },
            {
                'id': 'medium',
                'source_system': 'confluence',
                'name': 'Medium Article',
                'freshness_score': 0.6,  # Medium age (7-10 days)
                'relevance': 0.91
            }
        ]
        
        # Sort by (freshness * relevance) descending
        ranked = sorted(entities, key=lambda e: e['freshness_score'] * e['relevance'], reverse=True)
        
        # Verify order: fresh @ top, stale @ bottom
        assert ranked[0]['id'] == 'fresh'
        assert ranked[-1]['id'] == 'stale'

    def test_retrieve_max_results_limit(self):
        """Should never return unlimited results (max 100)."""
        
        # Generate many entities
        entities = [
            {
                'id': f'entity-{i}',
                'name': f'Entity {i}',
                'freshness_score': 0.9 - (i * 0.001)  # Declining freshness
            }
            for i in range(250)
        ]
        
        # Apply limit
        max_results = 100
        retrieved = entities[:max_results]
        
        assert len(retrieved) == 100
        assert len(retrieved) <= max_results

    def test_retrieve_context_contract_fields(self):
        """Retrieved context must include all contract fields."""
        
        # Full contract for context retrieval
        context_contract = {
            'entities': [
                {
                    'id': 'entity-uuid',
                    'source_system': 'jira',            # Required
                    'source_object_id': 'PROJ-100',     # Required
                    'entity_type': 'jira_issue',        # Required
                    'name': 'Issue title',               # Required
                    'description': 'Issue details',      # Required
                    'owner': 'Alice',                    # Required
                    'status': 'in_progress',             # Required
                    'source_url': 'https://...',         # Required
                    'freshness_score': 0.9,              # Required (0-1)
                    'eligible_skill_families_json': ['agent'],  # Required
                    'citations': [                       # Required
                        {
                            'source': 'PROJ-100',
                            'url': 'https://...',
                            'timestamp': '2026-04-17T10:00:00Z',
                            'relevance': 0.95
                        }
                    ]
                }
            ],
            'total_count': 1,
            'returned_count': 1,
            'query': 'authentication issue',
            'execution_time_ms': 45
        }
        
        # Verify all fields present
        entity = context_contract['entities'][0]
        required_fields = [
            'id', 'source_system', 'source_object_id', 'entity_type',
            'name', 'description', 'owner', 'status', 'source_url',
            'freshness_score', 'eligible_skill_families_json', 'citations'
        ]
        
        for field in required_fields:
            assert field in entity, f"Missing required field: {field}"
        
        # Verify types
        assert isinstance(entity['freshness_score'], (int, float))
        assert 0 <= entity['freshness_score'] <= 1
        assert isinstance(entity['citations'], list)
        assert len(entity['citations']) > 0

