"""Slack connector (C2e). Read-only for now."""

from dreamfi.connectors.slack.client import SlackClient
from dreamfi.connectors.slack.models import SlackChannel, SlackMessage

__all__ = ["SlackChannel", "SlackClient", "SlackMessage"]
