"""
Retrieval engine for knowledge hub context queries.

Implements:
- Database search for matching entities
- Ranking by freshness + relevance
- Citation aggregation
- Result limits (max 100)
"""

import os
import sqlite3
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
import time


class RetrievalEngine:
    """Queries canonical entities and returns ranked context."""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.getenv('KNOWLEDGE_HUB_DB', ':memory:')
        self.connection = None
        self.max_results = int(os.getenv('RETRIEVAL_MAX_RESULTS', '100'))
        self.freshness_weight = float(os.getenv('RETRIEVAL_FRESHNESS_WEIGHT', '0.3'))
        self.citation_weight = float(os.getenv('RETRIEVAL_CITATION_WEIGHT', '0.4'))
        self.relevance_weight = float(os.getenv('RETRIEVAL_RELEVANCE_WEIGHT', '0.3'))
    
    def connect(self):
        """Connect to database."""
        if not self.connection:
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row
    
    def disconnect(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None
    
    def _compute_relevance(self, query: str, entity: Dict[str, Any]) -> float:
        """
        Compute relevance score (0-1) between query and entity.
        Simple keyword matching for now.
        """
        query_lower = query.lower()
        entity_text = f"{entity['name']} {entity['description']}".lower()
        
        # Count matching keywords
        query_terms = query_lower.split()
        matches = sum(1 for term in query_terms if term in entity_text)
        
        if not query_terms:
            return 0.0
        
        relevance = min(1.0, matches / len(query_terms))
        return relevance
    
    def _get_citations_for_entity(self, entity_id: str) -> List[Dict[str, Any]]:
        """Retrieve citations for an entity."""
        if not self.connection:
            return []
        
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
                SELECT source_id, type, snippet, source_url, created_at
                FROM citations
                WHERE entity_id = ?
                ORDER BY created_at DESC
                LIMIT 5
            ''', (entity_id,))
            
            citations = []
            for row in cursor.fetchall():
                citations.append({
                    'source': row['source_id'],
                    'type': row['type'],
                    'snippet': row['snippet'],
                    'url': row['source_url'],
                    'timestamp': row['created_at'],
                    'relevance': 0.95  # Default high relevance for direct citations
                })
            
            return citations if citations else [{
                'source': 'Core entity',
                'url': '',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'relevance': 0.90
            }]
        except:
            return [{
                'source': 'Core entity',
                'url': '',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'relevance': 0.90
            }]
    
    def retrieve(
        self,
        query: str,
        skill_family: Optional[str] = None,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Query knowledge hub for relevant entities.
        
        Returns:
        {
            'entities': [
                {
                    'id': str,
                    'source_system': str,
                    'source_object_id': str,
                    'entity_type': str,
                    'name': str,
                    'description': str,
                    'owner': str,
                    'status': str,
                    'source_url': str,
                    'freshness_score': float (0-1),
                    'eligible_skill_families_json': [str],
                    'citations': [
                        {
                            'source': str,
                            'url': str,
                            'timestamp': str (ISO),
                            'relevance': float (0-1)
                        }
                    ]
                }
            ],
            'total_count': int,
            'returned_count': int,
            'query': str,
            'execution_time_ms': float
        }
        """
        start_time = time.time()
        limit = limit or self.max_results
        limit = min(limit, self.max_results)
        
        if not self.connection:
            self.connect()
        
        try:
            cursor = self.connection.cursor()
            
            # Build query: match on name/description + skill family filter
            base_query = '''
                SELECT
                    id,
                    source_system,
                    source_object_id,
                    entity_type,
                    name,
                    description,
                    owner,
                    status,
                    source_url,
                    freshness_score,
                    eligible_skill_families_json
                FROM core_entities
                WHERE status = 'active'
            '''
            
            params = []
            
            # Skill family filter
            if skill_family:
                base_query += ' AND eligible_skill_families_json LIKE ?'
                params.append(f'%{skill_family}%')
            
            base_query += ' ORDER BY freshness_score DESC LIMIT ?'
            params.append(limit * 2)  # Fetch more for ranking
            
            cursor.execute(base_query, params)
            db_entities = cursor.fetchall()
            
            # Rank by relevance * freshness
            ranked_entities = []
            for row in db_entities:
                entity = dict(row)
                relevance = self._compute_relevance(query, entity)
                freshness = entity['freshness_score']
                
                # Combined score
                score = (relevance * self.relevance_weight + 
                        freshness * self.freshness_weight)
                
                ranked_entities.append((score, relevance, entity))
            
            # Sort by score, take top limit
            ranked_entities.sort(key=lambda x: x[0], reverse=True)
            top_entities = ranked_entities[:limit]
            
            # Convert to output format
            result_entities = []
            for score, relevance, entity in top_entities:
                citations = self._get_citations_for_entity(entity['id'])
                
                result_entities.append({
                    'id': entity['id'],
                    'source_system': entity['source_system'],
                    'source_object_id': entity['source_object_id'],
                    'entity_type': entity['entity_type'],
                    'name': entity['name'],
                    'description': entity['description'],
                    'owner': entity['owner'],
                    'status': entity['status'],
                    'source_url': entity['source_url'],
                    'freshness_score': float(entity['freshness_score']),
                    'eligible_skill_families_json': self._parse_skill_families(
                        entity['eligible_skill_families_json']
                    ),
                    'citations': citations
                })
            
            execution_time_ms = (time.time() - start_time) * 1000
            
            return {
                'entities': result_entities,
                'total_count': len(db_entities),
                'returned_count': len(result_entities),
                'query': query,
                'execution_time_ms': execution_time_ms
            }
        
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            return {
                'entities': [],
                'total_count': 0,
                'returned_count': 0,
                'query': query,
                'execution_time_ms': execution_time_ms,
                'error': str(e)
            }
    
    def _parse_skill_families(self, json_str: str) -> List[str]:
        """Parse skill families JSON."""
        import json
        try:
            if isinstance(json_str, str):
                return json.loads(json_str)
            elif isinstance(json_str, list):
                return json_str
            else:
                return []
        except:
            return []


# Global singleton
_engine: Optional[RetrievalEngine] = None


def get_retrieval_engine(db_path: Optional[str] = None) -> RetrievalEngine:
    """Get or create global retrieval engine."""
    global _engine
    if _engine is None:
        _engine = RetrievalEngine(db_path)
    return _engine


def retrieve_context(
    query: str,
    skill_family: Optional[str] = None,
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience function: retrieve context for a query.
    """
    engine = get_retrieval_engine(db_path)
    if not engine.connection:
        engine.connect()
    return engine.retrieve(query, skill_family)
