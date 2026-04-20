"""OnyxClient exceptions."""
from __future__ import annotations


class OnyxError(Exception):
    """Base Onyx client error."""


class OnyxAuthError(OnyxError):
    """Authentication with Onyx failed."""


class OnyxNotFoundError(OnyxError):
    """Resource not found in Onyx."""


class OnyxServerError(OnyxError):
    """Onyx returned a 5xx response."""


class OnyxTimeoutError(OnyxError):
    """Request to Onyx timed out."""
