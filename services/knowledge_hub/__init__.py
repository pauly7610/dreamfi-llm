"""
Knowledge Hub Core - DreamFi Knowledge Management System

Provides:
- Connectors for syncing from Jira, Confluence, Dragonboat, etc.
- Retrieval engine for context queries
- Evaluation framework for output quality
- Confidence scoring (ADR-005)
- Generation loop with real LLM integration
- Promotion gate for publish decisions
- Gold examples registry for few-shot learning
"""

__version__ = "1.0.0"
__all__ = [
    "connectors",
    "retrieval",
    "confidence",
    "generate_loop",
    "promote",
    "gold_examples",
    "api",
    "db",
]
