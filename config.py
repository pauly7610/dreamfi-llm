"""
DreamFi Toolkit — Centralized Configuration
All tool connections configured via environment variables.
"""

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


def _env(key: str, default: str = "") -> str:
    return os.getenv(key, default)


@dataclass
class JiraConfig:
    url: str = field(default_factory=lambda: _env("JIRA_URL"))
    email: str = field(default_factory=lambda: _env("JIRA_EMAIL"))
    api_token: str = field(default_factory=lambda: _env("JIRA_API_TOKEN"))


@dataclass
class ConfluenceConfig:
    url: str = field(default_factory=lambda: _env("CONFLUENCE_URL"))
    email: str = field(default_factory=lambda: _env("CONFLUENCE_EMAIL"))
    api_token: str = field(default_factory=lambda: _env("CONFLUENCE_API_TOKEN"))


@dataclass
class DragonboatConfig:
    api_url: str = field(default_factory=lambda: _env("DRAGONBOAT_API_URL"))
    api_key: str = field(default_factory=lambda: _env("DRAGONBOAT_API_KEY"))


@dataclass
class MetabaseConfig:
    url: str = field(default_factory=lambda: _env("METABASE_URL"))
    username: str = field(default_factory=lambda: _env("METABASE_USERNAME"))
    password: str = field(default_factory=lambda: _env("METABASE_PASSWORD"))
    session_token: str = ""


@dataclass
class PostHogConfig:
    api_key: str = field(default_factory=lambda: _env("POSTHOG_API_KEY"))
    host: str = field(default_factory=lambda: _env("POSTHOG_HOST", "https://app.posthog.com"))
    project_id: str = field(default_factory=lambda: _env("POSTHOG_PROJECT_ID"))


@dataclass
class GoogleAnalyticsConfig:
    property_id: str = field(default_factory=lambda: _env("GA_PROPERTY_ID"))
    credentials_path: str = field(default_factory=lambda: _env("GA_CREDENTIALS_PATH"))


@dataclass
class KlaviyoConfig:
    api_key: str = field(default_factory=lambda: _env("KLAVIYO_API_KEY"))


@dataclass
class SardineConfig:
    api_url: str = field(default_factory=lambda: _env("SARDINE_API_URL"))
    client_id: str = field(default_factory=lambda: _env("SARDINE_CLIENT_ID"))
    secret_key: str = field(default_factory=lambda: _env("SARDINE_SECRET_KEY"))


@dataclass
class SocureConfig:
    api_url: str = field(default_factory=lambda: _env("SOCURE_API_URL"))
    api_key: str = field(default_factory=lambda: _env("SOCURE_API_KEY"))


@dataclass
class NetXDConfig:
    api_url: str = field(default_factory=lambda: _env("NETXD_API_URL"))
    api_key: str = field(default_factory=lambda: _env("NETXD_API_KEY"))
    client_id: str = field(default_factory=lambda: _env("NETXD_CLIENT_ID"))


@dataclass
class AnthropicConfig:
    api_key: str = field(default_factory=lambda: _env("ANTHROPIC_API_KEY"))
    model: str = "claude-sonnet-4-20250514"


@dataclass
class ToolkitConfig:
    """Master config — one import gets every connection."""
    jira: JiraConfig = field(default_factory=JiraConfig)
    confluence: ConfluenceConfig = field(default_factory=ConfluenceConfig)
    dragonboat: DragonboatConfig = field(default_factory=DragonboatConfig)
    metabase: MetabaseConfig = field(default_factory=MetabaseConfig)
    posthog: PostHogConfig = field(default_factory=PostHogConfig)
    google_analytics: GoogleAnalyticsConfig = field(default_factory=GoogleAnalyticsConfig)
    klaviyo: KlaviyoConfig = field(default_factory=KlaviyoConfig)
    sardine: SardineConfig = field(default_factory=SardineConfig)
    socure: SocureConfig = field(default_factory=SocureConfig)
    netxd: NetXDConfig = field(default_factory=NetXDConfig)
    anthropic: AnthropicConfig = field(default_factory=AnthropicConfig)

    # Paths
    wiki_path: str = field(default_factory=lambda: os.path.join(os.path.dirname(__file__), "knowledge_hub", "wiki"))
    sources_path: str = field(default_factory=lambda: os.path.join(os.path.dirname(__file__), "knowledge_hub", "sources"))
    templates_path: str = field(default_factory=lambda: os.path.join(os.path.dirname(__file__), "generators", "templates"))


config = ToolkitConfig()
