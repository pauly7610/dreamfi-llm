"""
DreamFi Integrations — shared API client layer.
Import any client directly:
    from integrations import JiraClient, MetabaseClient, ...
"""

from integrations.jira_client import JiraClient
from integrations.confluence_client import ConfluenceClient
from integrations.dragonboat_client import DragonboatClient
from integrations.metabase_client import MetabaseClient
from integrations.posthog_client import PostHogClient
from integrations.google_analytics_client import GAClient
from integrations.klaviyo_client import KlaviyoClient
from integrations.sardine_client import SardineClient
from integrations.socure_client import SocureClient
from integrations.ledger_netxd_client import NetXDClient
from integrations.errors import DreamFiIntegrationError

__all__ = [
    "JiraClient",
    "ConfluenceClient",
    "DragonboatClient",
    "MetabaseClient",
    "PostHogClient",
    "GAClient",
    "KlaviyoClient",
    "SardineClient",
    "SocureClient",
    "NetXDClient",
    "DreamFiIntegrationError",
]
