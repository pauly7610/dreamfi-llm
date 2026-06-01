"""Metabase connector (C2d)."""

from dreamfi.context_connectors.metabase.client import MetabaseClient
from dreamfi.context_connectors.metabase.models import MetabaseCardResult, MetabaseDatasetResult

__all__ = ["MetabaseCardResult", "MetabaseClient", "MetabaseDatasetResult"]
