"""Google Analytics 4 integration — uses the google-analytics-data library."""

from __future__ import annotations

import logging
from typing import Any

from config import config as _cfg
from config import GoogleAnalyticsConfig
from integrations.errors import DreamFiIntegrationError

log = logging.getLogger(__name__)


class GAClient:
    """Client for the Google Analytics Data API (GA4).

    Requires the ``google-analytics-data`` package and a service-account
    credentials JSON file referenced by ``GA_CREDENTIALS_PATH``.
    """

    def __init__(self, cfg: GoogleAnalyticsConfig | None = None):
        c = cfg or _cfg.google_analytics
        self._property_id = c.property_id
        try:
            from google.analytics.data_v1beta import BetaAnalyticsDataClient
            self._client = BetaAnalyticsDataClient.from_service_account_json(c.credentials_path)
        except Exception as exc:
            raise DreamFiIntegrationError("google_analytics", "Failed to initialise GA client") from exc

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @property
    def _property(self) -> str:
        return f"properties/{self._property_id}"

    @staticmethod
    def _parse_response(response) -> list[dict[str, Any]]:
        """Convert a GA RunReportResponse into a list of row dicts."""
        headers = [h.name for h in response.dimension_headers] + [h.name for h in response.metric_headers]
        rows: list[dict[str, Any]] = []
        for row in response.rows:
            values = [dv.value for dv in row.dimension_values] + [mv.value for mv in row.metric_values]
            rows.append(dict(zip(headers, values)))
        return rows

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_report(
        self,
        date_range: dict[str, str],
        metrics: list[str],
        dimensions: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Run a GA4 report and return parsed rows.

        Args:
            date_range: ``{"start_date": "2024-01-01", "end_date": "2024-01-31"}``
            metrics: e.g. ``["sessions", "activeUsers"]``
            dimensions: e.g. ``["date", "country"]``
        """
        try:
            from google.analytics.data_v1beta.types import (
                DateRange,
                Dimension,
                Metric,
                RunReportRequest,
            )

            request = RunReportRequest(
                property=self._property,
                date_ranges=[DateRange(**date_range)],
                metrics=[Metric(name=m) for m in metrics],
                dimensions=[Dimension(name=d) for d in (dimensions or [])],
            )
            response = self._client.run_report(request)
            rows = self._parse_response(response)
            log.info("GA report returned %d rows", len(rows))
            return rows
        except DreamFiIntegrationError:
            raise
        except Exception as exc:
            raise DreamFiIntegrationError("google_analytics", "Report request failed") from exc

    def get_realtime(self) -> list[dict[str, Any]]:
        """Fetch real-time active-user data."""
        try:
            from google.analytics.data_v1beta.types import (
                Metric,
                RunRealtimeReportRequest,
            )

            request = RunRealtimeReportRequest(
                property=self._property,
                metrics=[Metric(name="activeUsers")],
            )
            response = self._client.run_realtime_report(request)
            return self._parse_response(response)
        except DreamFiIntegrationError:
            raise
        except Exception as exc:
            raise DreamFiIntegrationError("google_analytics", "Realtime report failed") from exc

    def get_funnel(self, date_range: dict[str, str]) -> list[dict[str, Any]]:
        """Return a conversion-funnel report for the date range.

        Uses the standard GA4 report with ``eventName`` as the dimension and
        ``eventCount`` + ``conversions`` as metrics so callers can compute
        step-over-step conversion.
        """
        return self.get_report(
            date_range=date_range,
            metrics=["eventCount", "conversions"],
            dimensions=["eventName"],
        )
