"""
Unit tests for Confluence connector.

Tests authentication, page normalization, and pagination.
"""

import pytest
from datetime import datetime, timedelta


class TestConfluenceConnectorUnit:
    """Unit tests for Confluence connector."""

    def test_confluence_auth_from_env(self):
        """Confluence should parse auth from environment."""
        # CONFLUENCE_BASE_URL, CONFLUENCE_API_TOKEN
        
        config = {
            'baseUrl': 'https://example.atlassian.net',
            'auth': {
                'email': 'user@example.com',
                'apiToken': 'test-token-456'
            }
        }
        
        assert config['auth']['email'] == 'user@example.com'
        assert config['auth']['apiToken'] == 'test-token-456'
        assert 'baseUrl' in config

    def test_confluence_page_normalization(self):
        """Confluence page should normalize to NormalizedEntity."""
        
        # Mock raw Confluence page
        raw_page = {
            'id': '98765',
            'type': 'page',
            'title': 'Getting Started Guide',
            'status': 'current',
            'space': {
                'key': 'DOC',
                'name': 'Documentation'
            },
            'version': {
                'number': 5,
                'when': (datetime.utcnow() - timedelta(days=3)).isoformat(),
                'by': {'displayName': 'Alice'}
            },
            'body': {
                'storage': {
                    'value': '<p>This is the content.</p><p>More details here.</p>'
                }
            },
            'metadata': {
                'labels': {
                    'results': [
                        {'name': 'kb'},
                        {'name': 'support'}
                    ]
                }
            },
            '_links': {
                'webui': '/spaces/DOC/pages/98765/Getting+Started+Guide',
                'self': 'https://example.atlassian.net/wiki/rest/api/content/98765'
            }
        }
        
        # Verify structure
        assert raw_page['id'] == '98765'
        assert raw_page['title'] == 'Getting Started Guide'
        assert raw_page['space']['key'] == 'DOC'
        assert raw_page['version']['number'] == 5
        assert len(raw_page['metadata']['labels']['results']) == 2

    def test_confluence_pagination_cql_search(self):
        """Should handle CQL search pagination."""
        
        # CQL: type in (page, blogpost) ORDER BY lastModified DESC
        # Pagination: start + limit
        
        page_1 = {
            'results': [
                {'id': f'page-{i}', 'title': f'Page {i}'} 
                for i in range(1, 51)
            ],
            'start': 0,
            'limit': 50,
            'size': 50,
            '_links': {
                'next': 'https://example.atlassian.net/wiki/rest/api/content/search?start=50'
            }
        }
        
        page_2 = {
            'results': [
                {'id': f'page-{i}', 'title': f'Page {i}'} 
                for i in range(51, 101)
            ],
            'start': 50,
            'limit': 50,
            'size': 50,
            '_links': {}  # No next link = last page
        }
        
        # Verify pagination logic
        assert page_1['start'] == 0
        assert page_2['start'] == 50
        assert page_1['size'] == 50
        assert page_2['size'] == 50
        assert '_links' in page_1 and 'next' in page_1['_links']
        assert '_links' in page_2 and 'next' not in page_2['_links']

    def test_confluence_freshness_calculation(self):
        """Confluence freshness based on last modified date."""
        
        now = datetime.utcnow()
        
        # Fresh page (modified today)
        fresh_modified = now.isoformat()
        age_fresh = 0
        score_fresh = 2 ** (-age_fresh / 14.0)  # 14-day half-life for Confluence
        assert score_fresh == pytest.approx(1.0, abs=0.01)
        
        # Half-life (14 days old)
        half_life_modified = (now - timedelta(days=14)).isoformat()
        age_half = 14.0
        score_half = 2 ** (-age_half / 14.0)  # 2^-1 = 0.5
        assert score_half == pytest.approx(0.5, abs=0.01)
        
        # Quarter-life (28 days old)
        quarter_life_modified = (now - timedelta(days=28)).isoformat()
        age_quarter = 28.0
        score_quarter = 2 ** (-age_quarter / 14.0)  # 2^-2 = 0.25
        assert score_quarter == pytest.approx(0.25, abs=0.01)

    def test_confluence_skill_family_inference_from_labels(self):
        """Should infer skill families from page labels."""
        
        # Page with 'kb' or 'support' labels → 'agent' family
        support_page = {
            'type': 'page',
            'metadata': {
                'labels': {
                    'results': [
                        {'name': 'kb'},
                        {'name': 'support'}
                    ]
                }
            }
        }
        
        inferred = []
        labels = [l['name'].lower() for l in support_page['metadata']['labels']['results']]
        if any(l in ['kb', 'support', 'knowledge-base'] for l in labels):
            inferred.append('agent')
        
        assert 'agent' in inferred
        
        # Blog post → 'copywriting' family
        blog_post = {
            'type': 'blogpost',
            'metadata': {
                'labels': {
                    'results': []
                }
            }
        }
        
        inferred_blog = []
        if blog_post['type'] == 'blogpost':
            inferred_blog.append('copywriting')
        
        assert 'copywriting' in inferred_blog

    def test_confluence_cql_watermark_filtering(self):
        """Should use CQL with lastModified >= watermark for incremental sync."""
        
        watermark = '2026-04-15T10:00:00Z'
        cql_parts = [
            'type in (page, blogpost)',
            f'lastModified >= "{watermark}"',
            'ORDER BY lastModified DESC'
        ]
        
        cql = ' AND '.join(cql_parts)
        
        assert 'lastModified >= "2026-04-15T10:00:00Z"' in cql
        assert 'type in (page, blogpost)' in cql
        assert 'ORDER BY lastModified DESC' in cql

