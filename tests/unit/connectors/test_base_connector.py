"""
Unit tests for connector implementations.

NOTE: These are template/example tests showing the patterns. Actual connector tests
will be in the TypeScript/Node.js test suite since connectors are implemented in TypeScript.
This file demonstrates the expected testing patterns for reference.
"""

import pytest
from typing import Any, Dict, List
from dataclasses import dataclass
from datetime import datetime


@dataclass
class NormalizedEntity:
    """Mock NormalizedEntity for testing patterns."""
    entity_id: str
    entity_type: str
    source_system: str
    source_object_id: str
    freshness_score: float
    name: str
    description: str = ""
    owner: str = None
    status: str = "active"
    source_url: str = None
    last_synced_at: str = None
    eligible_skill_families_json: List[str] = None


class MockConnector:
    """
    Mock connector for testing base connector interface.
    This shows the expected behavior that all connectors should implement.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.connected = False
    
    async def connect(self):
        self.connected = True
    
    async def disconnect(self):
        self.connected = False
    
    async def fetchRaw(self, watermark: str):
        """Yield mock payload objects."""
        # Mock: yield 3 sample payloads
        for i in range(3):
            yield {
                'id': f'obj-{i}',
                'name': f'Object {i}',
                'updated': '2026-04-17T10:00:00Z'
            }
    
    def normalize(self, raw_payload):
        return NormalizedEntity(
            entity_id=raw_payload['id'],
            source_system='test_connector',
            source_object_id=raw_payload['id'],
            entity_type='test_object',
            name=raw_payload['name'],
            description=None,
            owner=None,
            status='active',
            source_url=None,
            last_synced_at='2026-04-17T10:00:00Z',
            freshness_score=1.0,
            eligible_skill_families_json=['test'],
        )
    
    async def sync(self, watermark: str):
        """Sync and return normalized entities."""
        await self.connect()
        entities = []
        async for raw in self.fetchRaw(watermark):
            entities.append(self.normalize(raw))
        await self.disconnect()
        return {
            'entities': entities,
            'result': {'entitiesSynced': len(entities)}
        }


class TestBaseConnector:
    """Test base connector interface."""
    
    @pytest.mark.asyncio
    async def test_connector_connection(self):
        """Should connect and disconnect safely."""
        config = {
            'name': 'Test Connector',
            'sourceSystem': 'test',
            'baseUrl': 'http://test.local',
            'auth': {}
        }
        
        connector = MockConnector(config)
        assert not connector.connected
        
        await connector.connect()
        assert connector.connected
        
        await connector.disconnect()
        assert not connector.connected
    
    @pytest.mark.asyncio
    async def test_sync_returns_entities(self):
        """Sync should return normalized entities."""
        config = {
            'name': 'Test Connector',
            'sourceSystem': 'test',
            'baseUrl': 'http://test.local',
            'auth': {}
        }
        
        connector = MockConnector(config)
        await connector.connect()
        
        result = await connector.sync(None)
        
        assert 'entities' in result
        assert 'result' in result
        assert len(result['entities']) == 3
        assert result['result']['entitiesSynced'] == 3


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
