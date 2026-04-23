"""Confluence connector (C2b).

Only allowed import path for Confluence from DreamFi.
"""

from dreamfi.connectors.confluence.client import ConfluenceClient
from dreamfi.connectors.confluence.models import ConfluenceHistoryEntry, ConfluencePage

__all__ = [
    "ConfluenceClient",
    "ConfluenceHistoryEntry",
    "ConfluencePage",
]
