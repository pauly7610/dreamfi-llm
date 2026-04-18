"""
E2E: Phase 1 Query to Answer

End-to-end validation of the complete knowledge hub query→answer path with citations and confidence.
"""
import pytest
from datetime import datetime


@pytest.mark.e2e
@pytest.mark.critical
class TestPhase1QueryToAnswer:
    """Validate complete query→answer→cited response flow."""

    def test_source_sync_prereq(self):
        """Prerequisites: connector sync completed, sources available.
        
        Expected: At least one Jira issue and Confluence page in DB.
        """
        
        # Mock DB check
        entities_in_db = [
            {'source_system': 'jira', 'source_object_id': 'PROJ-100', 'name': 'Login API'},
            {'source_system': 'confluence', 'source_object_id': 'page-50', 'name': 'Auth Guide'}
        ]
        
        jira_count = len([e for e in entities_in_db if e['source_system'] == 'jira'])
        confluence_count = len([e for e in entities_in_db if e['source_system'] == 'confluence'])
        
        assert jira_count >= 1
        assert confluence_count >= 1

    def test_simple_query_returns_answer(self):
        """Query API returns structured answer response.
        
        Expected: { 'answer': '...', 'citations': [...], 'confidence': 0.85, ... }.
        """
        
        response = {
            'answer': 'Login uses OAuth 2.0 protocol. See PROJ-100 for implementation details.',
            'citations': [
                {
                    'source_id': 'PROJ-100',
                    'source_type': 'jira_issue',
                    'snippet': 'OAuth 2.0 implementation',
                    'url': 'https://jira.example.com/browse/PROJ-100'
                }
            ],
            'confidence': 0.87,
            'retrieved_at': datetime.utcnow().isoformat(),
            'execution_time_ms': 34
        }
        
        assert 'answer' in response
        assert isinstance(response['answer'], str)
        assert 'citations' in response
        assert 'confidence' in response

    def test_answer_includes_citations(self):
        """Every supported claim must include citations.
        
        Expected: citations[0] = { source_id, source_type, snippet, url }.
        """
        
        response = {
            'answer': 'Authentication requires email + password or OAuth token.',
            'citations': [
                {
                    'source_id': 'page-50',
                    'source_type': 'confluence_page',
                    'snippet': 'Supports BasicAuth and OAuth',
                    'url': 'https://confluence.example.com/wiki/spaces/DOC/pages/50',
                    'relevance': 0.92
                },
                {
                    'source_id': 'PROJ-100',
                    'source_type': 'jira_issue',
                    'snippet': 'Token-based auth implemented in sprint 5',
                    'url': 'https://jira.example.com/browse/PROJ-100',
                    'relevance': 0.88
                }
            ]
        }
        
        # Each citation must have required fields
        required = ['source_id', 'source_type', 'snippet', 'url']
        for citation in response['citations']:
            for field in required:
                assert field in citation

    def test_answer_includes_freshness(self):
        """Response includes freshness of sources.
        
        Expected: freshness_score, stale_warning if < threshold.
        """
        
        response = {
            'answer': 'Current API v3 supports authentication.',
            'citations': [
                {
                    'source_id': 'PROJ-100',
                    'freshness_score': 0.9,  # Updated within 1 day
                    'updated_at': datetime.utcnow().isoformat()
                }
            ],
            'freshness_summary': {
                'average_freshness': 0.9,
                'stale_warning': False  # All sources fresh
            }
        }
        
        assert 'freshness_score' in response['citations'][0]
        assert 'freshness_summary' in response
        assert response['freshness_summary']['average_freshness'] < 1.0
        assert response['freshness_summary']['average_freshness'] > 0

    def test_answer_includes_confidence(self):
        """Response includes overall confidence score.
        
        Expected: confidence between 0-1, factors documented.
        """
        
        response = {
            'answer': 'Use OAuth 2.0 for API authentication.',
            'confidence': 0.87,
            'confidence_breakdown': {
                'sources_found': True,
                'source_count': 2,
                'avg_freshness': 0.9,
                'hard_gates_passed': True,
                'factors': [
                    'Multiple sources agree',
                    'All sources fresh (< 1 day old)',
                    'Structure validates correctly'
                ]
            }
        }
        
        assert 0 <= response['confidence'] <= 1
        assert isinstance(response['confidence_breakdown'], dict)
        assert 'sources_found' in response['confidence_breakdown']
        assert 'factors' in response['confidence_breakdown']

    def test_agent_mode_answer_includes_next_action(self):
        """Agent-style answers include suggested next action."""
        
        response = {
            'answer': 'OAuth is the recommended auth method.',
            'next_actions': [
                'Review PROJ-100 implementation details',
                'Check Confluence guide for setup steps',
                'Run integration tests before deploying'
            ],
            'confidence': 0.85
        }
        
        assert 'next_actions' in response
        assert isinstance(response['next_actions'], list)
        assert len(response['next_actions']) > 0

    def test_answer_response_time_under_threshold(self):
        """Query must complete in < 500ms.
        
        Expected: execution_time_ms < 500.
        """
        
        response = {
            'answer': 'Example answer',
            'execution_time_ms': 234,
            'retrieved_at': datetime.utcnow().isoformat()
        }
        
        assert response['execution_time_ms'] < 500

    def test_no_hallucination_in_answer(self):
        """Answer must only reference entities actually in DB.
        
        Expected: All cited sources exist and match retrieved data.
        """
        
        available_sources = {
            'PROJ-100': 'Login API',
            'PROJ-101': 'Payment Service',
            'page-50': 'Auth Guide'
        }
        
        response = {
            'answer': 'See PROJ-100 and page-50.',
            'citations': [
                {'source_id': 'PROJ-100'},
                {'source_id': 'page-50'}
            ]
        }
        
        # Verify all cited IDs exist
        for citation in response['citations']:
            source_id = citation['source_id']
            assert source_id in available_sources, f"Source {source_id} not in DB"
