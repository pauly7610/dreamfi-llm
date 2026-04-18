"""Custom exception for all DreamFi integration failures."""


class DreamFiIntegrationError(Exception):
    """Raised when an external API call fails.

    Attributes:
        service: Name of the integration that failed (e.g. "jira", "metabase").
        status_code: HTTP status code, if applicable.
        detail: Raw error body / message from the upstream service.
    """

    def __init__(self, service: str, message: str, status_code: int | None = None, detail: str | None = None):
        self.service = service
        self.status_code = status_code
        self.detail = detail
        full = f"[{service}] {message}"
        if status_code:
            full += f" (HTTP {status_code})"
        if detail:
            full += f" — {detail}"
        super().__init__(full)
