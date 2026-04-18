"""
Confluence connector for DreamFi - syncs Confluence pages/blogs to knowledge hub.

Implements:
- Email + API token authentication
- CQL-based filtering for pages and blogposts
- Watermark-based incremental sync
- Freshness scoring (14-day half-life)
- HTML to plaintext extraction
"""

import os
import requests
from typing import Dict, List, Any, AsyncGenerator, Optional
from datetime import datetime, timedelta, timezone
import hashlib
from html.parser import HTMLParser


class HTMLToTextParser(HTMLParser):
    """Convert HTML to plaintext."""
    
    def __init__(self):
        super().__init__()
        self.text = []
        
    def handle_data(self, data: str):
        self.text.append(data.strip())
        
    def get_text(self) -> str:
        return ' '.join(self.text)


class NormalizedEntity:
    """Normalized representation of a synced entity."""
    
    def __init__(self, **kwargs):
        self.source_system = kwargs.get('source_system', 'confluence')
        self.source_object_id = kwargs.get('source_object_id')
        self.entity_type = kwargs.get('entity_type')
        self.name = kwargs.get('name')
        self.description = kwargs.get('description', '')
        self.owner = kwargs.get('owner')
        self.status = kwargs.get('status', 'active')
        self.source_url = kwargs.get('source_url')
        self.last_synced_at = kwargs.get('last_synced_at')
        self.freshness_score = kwargs.get('freshness_score', 1.0)
        self.eligible_skill_families_json = kwargs.get('eligible_skill_families_json', [])


class ConfluenceConnector:
    """
    Connector for Confluence REST API v1.
    
    Fetches pages and blogposts via CQL, normalizes to canonical schema.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.email = os.getenv('CONFLUENCE_EMAIL', '')
        self.api_token = os.getenv('CONFLUENCE_API_TOKEN', '')
        self.base_url = os.getenv('CONFLUENCE_BASE_URL', 'https://confluence.example.com')
        self.connected = False
    
    async def connect(self):
        """Establish connection (verify credentials)."""
        if not self.email or not self.api_token:
            raise ValueError("CONFLUENCE_EMAIL and CONFLUENCE_API_TOKEN required")
        self.connected = True
        
    async def disconnect(self):
        """Close connection."""
        self.connected = False
        
    async def fetchRaw(self, watermark: Optional[str] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Fetch pages and blogposts via CQL, sorted by modified descending.
        Yields raw Confluence API payloads.
        """
        if not self.connected:
            await self.connect()
        
        # CQL: Get published pages and blogposts
        cql = 'type in (page, blogpost) AND status = current'
        
        # If watermark provided, fetch only updated-after
        if watermark:
            cql += f' AND lastModified >= "{watermark}"'
        
        cql += ' ORDER BY lastModified DESC'
        
        url = f'{self.base_url}/rest/api/content'
        auth = (self.email, self.api_token)
        start = 0
        limit = 50
        
        while True:
            params = {
                'cql': cql,
                'start': start,
                'limit': limit,
                'expand': 'body.storage,version,metadata.labels'
            }
            
            response = requests.get(url, params=params, auth=auth, timeout=10)
            if response.status_code != 200:
                raise Exception(f"Confluence API error: {response.status_code}")
            
            data = response.json()
            
            for page in data.get('results', []):
                yield page
            
            if start + limit >= data.get('size', 0):
                break
                
            start += limit
    
    def _html_to_text(self, html: str) -> str:
        """Convert HTML to plaintext."""
        parser = HTMLToTextParser()
        try:
            parser.feed(html)
            return parser.get_text()
        except:
            return html
    
    def normalize(self, raw_payload: Dict[str, Any]) -> NormalizedEntity:
        """
        Normalize Confluence page/blogpost → NormalizedEntity.
        Extracts content, computes freshness, infers skill families.
        """
        page_id = raw_payload.get('id', '')
        page_type = raw_payload.get('type', '')  # 'page' or 'blogpost'
        
        # Extract metadata
        title = raw_payload.get('title', '')
        version_info = raw_payload.get('version', {})
        last_modified = version_info.get('when', datetime.utcnow().isoformat())
        author = version_info.get('by', {}).get('displayName', 'unknown')
        
        # Extract URL
        links = raw_payload.get('_links', {})
        webui = links.get('webui', '')
        source_url = f'{self.base_url}{webui}' if webui else f'{self.base_url}/pages/viewpage.action?pageId={page_id}'
        
        # Extract body (HTML)
        body = raw_payload.get('body', {}).get('storage', {}).get('value', '')
        description = self._html_to_text(body)[:500]  # Truncate to 500 chars
        
        # Compute freshness (14-day half-life for Confluence)
        try:
            modified = datetime.fromisoformat(last_modified.replace('Z', '+00:00'))
            age_days = (datetime.now(timezone.utc) - modified).days if hasattr(modified, 'tzinfo') else (datetime.utcnow() - modified).days
        except:
            age_days = 0
        
        freshness_score = 2 ** (-max(0, age_days) / 14.0)
        
        # Infer skill families from labels
        labels = raw_payload.get('metadata', {}).get('labels', [])
        label_names = [l.get('name', '').lower() for l in labels]
        label_str = ' '.join(label_names)
        
        skill_families = []
        
        if 'kb' in label_str or 'support' in label_str:
            skill_families.append('agent')
        if 'marketing' in label_str or 'copy' in label_str or 'brand' in label_str:
            skill_families.append('copywriting')
        if page_type == 'blogpost':
            skill_families.append('copywriting')
        
        # Default to agent if no matches
        if not skill_families:
            skill_families = ['agent']
        
        return NormalizedEntity(
            source_system='confluence',
            source_object_id=f'page-{page_id}',
            entity_type=f'confluence_{page_type}',
            name=title,
            description=description,
            owner=author,
            status='published',
            source_url=source_url,
            last_synced_at=datetime.utcnow().isoformat(),
            freshness_score=freshness_score,
            eligible_skill_families_json=skill_families
        )
    
    async def sync(self, watermark: Optional[str] = None) -> Dict[str, Any]:
        """
        Sync pages: fetch → normalize → return.
        """
        await self.connect()
        entities = []
        
        async for raw in self.fetchRaw(watermark):
            entity = self.normalize(raw)
            entities.append(entity)
        
        await self.disconnect()
        
        return {
            'entities': entities,
            'result': {
                'entitiesSynced': len(entities),
                'connector': 'confluence',
                'syncedAt': datetime.utcnow().isoformat()
            }
        }
