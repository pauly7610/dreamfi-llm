"""Slack connector (C2e). Read-only for now."""

from dreamfi.context_connectors.slack.client import SlackClient
from dreamfi.context_connectors.slack.models import SlackChannel, SlackMessage

__all__ = ["SlackChannel", "SlackClient", "SlackMessage"]
