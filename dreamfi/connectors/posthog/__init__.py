"""PostHog connector (C2c)."""

from dreamfi.connectors.posthog.client import PostHogClient
from dreamfi.connectors.posthog.models import PostHogFeatureFlag, PostHogResult

__all__ = ["PostHogClient", "PostHogFeatureFlag", "PostHogResult"]
