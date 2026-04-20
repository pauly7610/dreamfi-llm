"""Metabase connector (C2d)."""

from dreamfi.connectors.metabase.client import MetabaseClient
from dreamfi.connectors.metabase.models import MetabaseCardResult, MetabaseDatasetResult

__all__ = ["MetabaseCardResult", "MetabaseClient", "MetabaseDatasetResult"]
