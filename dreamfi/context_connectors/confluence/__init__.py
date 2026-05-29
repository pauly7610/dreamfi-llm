"""Confluence connector (C2b).

Only allowed import path for Confluence from DreamFi.
"""

from dreamfi.context_connectors.confluence.client import ConfluenceClient
from dreamfi.context_connectors.confluence.models import ConfluenceHistoryEntry, ConfluencePage

__all__ = [
    "ConfluenceClient",
    "ConfluenceHistoryEntry",
    "ConfluencePage",
]
