"""
Query API for knowledge hub - Flask endpoint.

Implements:
- POST /api/query — Query knowledge hub with retrieval + confidence
- GET /api/admin/debug/query/<query_id> — Debug endpoint
"""

from flask import Flask, request, jsonify
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from services.knowledge_hub.src.retrieval.retrieve_context import retrieve_context
from services.knowledge_hub.src.confidence.score_confidence import score_confidence


app = Flask(__name__)


class QueryProcessor:
    """Process queries and return answers with confidence."""
    
    def __init__(self):
        self.queries_log = {}  # In-memory query log for debug endpoint
    
    def process_query(
        self,
        query: str,
        skill_family: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process query and return answer with citations and confidence.
        
        Returns:
        {
            'query_id': str (UUID),
            'query': str,
            'answer': str,
            'citations': [
                {
                    'source': str,
                    'url': str,
                    'snippet': str,
                    'relevance': float
                }
            ],
            'confidence': float (0-1),
            'confidence_breakdown': {...},
            'freshness': float (0-1),
            'responded': bool,
            'next_action': str (optional)
        }
        """
        
        query_id = str(uuid.uuid4())
        
        # Retrieve context
        retrieval_result = retrieve_context(query, skill_family)
        entities = retrieval_result.get('entities', [])
        
        # No entities found - impossible request
        if not entities:
            response = {
                'query_id': query_id,
                'query': query,
                'answer': None,
                'responded': False,
                'reason': 'No matching knowledge found',
                'next_action': f'Please provide more specific details about: {query}',
                'citations': [],
                'confidence': 0.0,
                'freshness': 0.0
            }
            self.queries_log[query_id] = response
            return response
        
        # Rank entities and build answer
        top_entity = entities[0]
        
        # Collect citations
        citations = []
        for entity_citation in top_entity.get('citations', []):
            citations.append({
                'source': entity_citation.get('source', ''),
                'type': entity_citation.get('type', 'entity'),
                'url': entity_citation.get('url', top_entity.get('source_url', '')),
                'snippet': entity_citation.get('snippet', top_entity.get('description', '')),
                'relevance': entity_citation.get('relevance', 0.9)
            })
        
        # Score confidence (mock eval for now - will use real eval later)
        eval_score = 0.85  # Mock: will come from generation + eval
        freshness = top_entity.get('freshness_score', 0.8)
        citation_count = len(citations)
        hard_gate_passed = True  # Mock: will be computed from eval criteria
        
        confidence_result = score_confidence(
            eval_score=eval_score,
            freshness_score=freshness,
            citation_count=citation_count,
            hard_gate_passed=hard_gate_passed
        )
        
        # Build answer
        answer = (
            f"Based on our knowledge base: {top_entity.get('name', 'Unknown')}. "
            f"{top_entity.get('description', '')}"
        )
        
        response = {
            'query_id': query_id,
            'query': query,
            'answer': answer,
            'citations': citations,
            'confidence': confidence_result['confidence'],
            'confidence_breakdown': confidence_result['breakdown'],
            'freshness': freshness,
            'responded': True,
            'retrieved_entity': {
                'source': top_entity.get('source_system', ''),
                'type': top_entity.get('entity_type', ''),
                'url': top_entity.get('source_url', '')
            }
        }
        
        self.queries_log[query_id] = response
        return response
    
    def get_query_debug(self, query_id: str) -> Dict[str, Any]:
        """Retrieve debug info for a query."""
        if query_id not in self.queries_log:
            return {'error': 'Query not found', 'query_id': query_id}
        
        return self.queries_log[query_id]


# Global processor
processor = QueryProcessor()


@app.route('/api/query', methods=['POST'])
def query_endpoint():
    """
    POST /api/query
    
    Request:
    {
        "query": "What is the authentication endpoint?",
        "skill": "agent"  (optional)
    }
    
    Response:
    {
        "query_id": "uuid",
        "query": "...",
        "answer": "...",
        "citations": [...],
        "confidence": 0.85,
        "freshness": 0.9,
        "responded": true
    }
    """
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        skill = data.get('skill')
        
        if not query:
            return jsonify({'error': 'query required'}), 400
        
        result = processor.process_query(query, skill)
        return jsonify(result), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/debug/query/<query_id>', methods=['GET'])
def debug_query_endpoint(query_id: str):
    """
    GET /api/admin/debug/query/<query_id>
    
    Returns full debug info for a query execution.
    """
    try:
        result = processor.get_query_debug(query_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)
