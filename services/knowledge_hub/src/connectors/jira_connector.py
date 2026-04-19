"""
Jira connector for DreamFi - syncs Jira issues to knowledge hub.

Implements:
- Email + API token authentication
- JQL-based filtering for issues
- Watermark-based incremental sync
- Freshness scoring (7-day half-life)
"""

import os
import requests
from typing import Dict, List, Any, AsyncGenerator, Optional
from datetime import datetime, timedelta, timezone
import hashlib
import json


class NormalizedEntity:
    """Normalized representation of a synced entity."""
    
    def __init__(self, **kwargs):
        self.source_system = kwargs.get('source_system', 'jira')
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


class JiraConnector:
    """
    Connector for Jira API v3.
    
    Fetches issues, normalizes to canonical schema, tracks freshness.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.email = os.getenv('JIRA_EMAIL', '')
        self.api_token = os.getenv('JIRA_API_TOKEN', '')
        self.base_url = os.getenv('JIRA_BASE_URL', 'https://jira.example.com')
        self.connected = False
        
    async def connect(self):
        """Establish connection (verify credentials)."""
        if not self.email or not self.api_token:
            raise ValueError("JIRA_EMAIL and JIRA_API_TOKEN required")
        self.connected = True
        
    async def disconnect(self):
        """Close connection."""
        self.connected = False
        
    async def fetchRaw(self, watermark: Optional[str] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Fetch issues via JQL, sorted by updated date descending.
        Yields raw Jira API payloads.
        """
        if not self.connected:
            await self.connect()
            
        # JQL: Get non-closed issues (Epic, Story, Bug types)
        jql = 'issuetype in (Epic, Story, Bug) AND status != Closed'
        
        # If watermark provided, fetch only updated-since
        if watermark:
            jql += f' AND updated >= "{watermark}"'
        
        jql += ' ORDER BY updated DESC'
        
        url = f'{self.base_url}/rest/api/3/search'
        auth = (self.email, self.api_token)
        start_at = 0
        page_size = 100
        
        while True:
            params = {
                'jql': jql,
                'startAt': start_at,
                'maxResults': page_size,
                'expand': 'changelog'
            }
            
            response = requests.get(url, params=params, auth=auth, timeout=10)
            if response.status_code != 200:
                raise Exception(f"Jira API error: {response.status_code}")
            
            data = response.json()
            
            for issue in data.get('issues', []):
                yield issue
            
            if start_at + page_size >= data.get('total', 0):
                break
                
            start_at += page_size
    
    def normalize(self, raw_payload: Dict[str, Any]) -> NormalizedEntity:
        """
        Normalize Jira issue → NormalizedEntity.
        Maps fields, computes freshness, infers skill families.
        """
        fields = raw_payload.get('fields', {})
        
        # Extract issue key and URL
        issue_key = raw_payload.get('key', '')
        source_url = f'{self.base_url}/browse/{issue_key}'
        
        # Extract owner (assignee)
        assignee = fields.get('assignee')
        owner = assignee.get('displayName') if assignee else 'unassigned'
        
        # Extract updated timestamp and compute freshness
        updated_str = fields.get('updated', datetime.utcnow().isoformat())
        updated = datetime.fromisoformat(updated_str.replace('Z', '+00:00'))
        age_days = (datetime.utcnow(timezone.utc) - updated).days if hasattr(updated, 'tzinfo') else (datetime.utcnow() - updated).days
        
        # Freshness: 2^(-age_days / 7) [7-day half-life]
        freshness_score = 2 ** (-max(0, age_days) / 7.0)
        
        # Infer skill families from labels and issue type
        labels = fields.get('labels', [])
        issue_type = fields.get('issuetype', {}).get('name', '').lower()
        
        skill_families = []
        label_keywords = ' '.join(labels).lower()
        
        if 'support' in label_keywords or 'bug' in issue_type:
            skill_families.append('agent')
        if 'copy' in label_keywords or 'marketing' in label_keywords:
            skill_families.append('copywriting')
        if 'kb' in label_keywords or 'knowledge' in label_keywords:
            skill_families.append('agent')
        
        # Default to agent if no matches
        if not skill_families:
            skill_families = ['agent']
        
        return NormalizedEntity(
            source_system='jira',
            source_object_id=issue_key,
            entity_type='jira_issue',
            name=fields.get('summary', ''),
            description=fields.get('description', {}).get('content', [{}])[0].get('text', '') if isinstance(fields.get('description'), dict) else '',
            owner=owner,
            status=fields.get('status', {}).get('name', 'unknown').lower(),
            source_url=source_url,
            last_synced_at=datetime.utcnow().isoformat(),
            freshness_score=freshness_score,
            eligible_skill_families_json=skill_families
        )
    
    async def sync(self, watermark: Optional[str] = None) -> Dict[str, Any]:
        """
        Sync issues: fetch → normalize → return.
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
                'connector': 'jira',
                'syncedAt': datetime.utcnow().isoformat()
            }
        }
