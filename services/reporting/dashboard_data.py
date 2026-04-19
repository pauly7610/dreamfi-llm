import logging
import json
from datetime import datetime, timedelta
from typing import Any, Optional
import psycopg2

from integrations.dragonboat_client import DragonboatClient
from integrations.jira_client import JiraClient
from services.reporting.metrics_aggregator import MetricsAggregator
from config import config as _cfg

log = logging.getLogger(__name__)


class DashboardDataProvider:
    def __init__(self, db_url: Optional[str] = None, cache_ttl_minutes: int = 30):
        self.db_url = db_url or _cfg.__dict__.get("database_url", "postgresql://dreamfi:password@localhost:5432/dreamfi_dev")
        self.dragonboat = DragonboatClient()
        self.jira = JiraClient()
        self.metrics = MetricsAggregator(db_url)
        self.cache_ttl_minutes = cache_ttl_minutes
        self._cache = {}

    def get_initiative_health(self, initiative_id: str) -> dict[str, Any]:
        cache_key = f"initiative_health_{initiative_id}"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        try:
            health_data = self._get_health_score_sync(initiative_id)
            blocked_count = self._get_blocked_count_sync(initiative_id)

            epics = self.jira.get_epics("DMON")
            matching_epic = None
            for epic in epics:
                if initiative_id in epic.get("description", ""):
                    matching_epic = epic
                    break

            percent_complete = 0
            if matching_epic:
                stories = self.jira.get_epic_stories(matching_epic.get("key"))
                done_stories = [s for s in stories if s.get("fields", {}).get("status", {}).get("statusCategory", {}).get("key") == "done"]
                percent_complete = (len(done_stories) / len(stories) * 100) if stories else 0

            result = {
                "initiative_id": initiative_id,
                "status": health_data.get("status", "unknown"),
                "percent_complete": round(percent_complete, 1),
                "health_score": health_data.get("health_score", 0),
                "blockers": blocked_count,
                "on_schedule": health_data.get("on_schedule", 0),
            }

            self._set_cache(cache_key, result, self.cache_ttl_minutes)
            return result

        except Exception as exc:
            log.error(f"Failed to get initiative health for {initiative_id}: {exc}")
            return {"error": str(exc)}

    def get_team_velocity(self) -> dict[str, Any]:
        cache_key = "team_velocity"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        try:
            velocity_data = self._get_velocity_sync()
            sprints = velocity_data.get("sprints", [])

            velocity_trend = []
            for sprint in sprints[-12:]:
                velocity_trend.append({
                    "sprint_name": sprint.get("sprint_name"),
                    "velocity": sprint.get("completed_story_points", 0),
                    "date": sprint.get("sprint_end"),
                })

            avg_velocity = velocity_data.get("average_velocity", 0)
            trend_direction = "stable"
            if len(velocity_trend) >= 2:
                recent_avg = sum(v.get("velocity", 0) for v in velocity_trend[-4:]) / 4
                older_avg = sum(v.get("velocity", 0) for v in velocity_trend[-8:-4]) / 4
                if recent_avg > older_avg * 1.1:
                    trend_direction = "improving"
                elif recent_avg < older_avg * 0.9:
                    trend_direction = "declining"

            result = {
                "average_velocity": round(avg_velocity, 1),
                "trend_direction": trend_direction,
                "sprints_tracked": len(velocity_trend),
                "velocity_trend": velocity_trend,
            }

            self._set_cache(cache_key, result, self.cache_ttl_minutes)
            return result

        except Exception as exc:
            log.error(f"Failed to get team velocity: {exc}")
            return {"error": str(exc)}

    async def get_dependency_graph(self) -> dict[str, Any]:
        cache_key = "dependency_graph"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        try:
            initiatives = await self.dragonboat.async_get_initiatives()

            nodes = []
            links = []

            for initiative in initiatives:
                node_id = initiative.get("id")
                nodes.append({
                    "id": node_id,
                    "name": initiative.get("name"),
                    "status": initiative.get("status"),
                    "health": self._get_health_score_sync(node_id).get("health_score", 0),
                })

                dependencies = initiative.get("dependencies", [])
                for dep in dependencies:
                    links.append({
                        "source": node_id,
                        "target": dep.get("id") if isinstance(dep, dict) else dep,
                        "type": "depends_on",
                    })

            result = {
                "nodes": nodes,
                "links": links,
                "total_initiatives": len(nodes),
                "total_dependencies": len(links),
            }

            self._set_cache(cache_key, result, self.cache_ttl_minutes)
            return result

        except Exception as exc:
            log.error(f"Failed to get dependency graph: {exc}")
            return {"error": str(exc)}

    async def get_alerts(self) -> dict[str, Any]:
        cache_key = "alerts"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("""
            SELECT id, initiative_id, alert_type, severity, message, first_detected_at, status
            FROM reporting_alerts
            WHERE status = 'open'
            ORDER BY severity DESC, first_detected_at DESC
            """)
            rows = cursor.fetchall()

            alerts = []
            for row in rows:
                alert_id, initiative_id, alert_type, severity, message, first_detected_at, status = row
                alerts.append({
                    "id": str(alert_id),
                    "initiative_id": initiative_id,
                    "type": alert_type,
                    "severity": severity,
                    "message": message,
                    "first_detected_at": first_detected_at.isoformat() if first_detected_at else None,
                    "status": status,
                })

            result = {
                "open_alerts": len(alerts),
                "critical_count": len([a for a in alerts if a["severity"] == "critical"]),
                "high_count": len([a for a in alerts if a["severity"] == "high"]),
                "alerts": alerts,
            }

            self._set_cache(cache_key, result, 5)
            return result

        finally:
            cursor.close()
            conn.close()

    def _get_health_score_sync(self, initiative_id: str) -> dict[str, Any]:
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.metrics.get_health_score(initiative_id))
            loop.close()
            return result
        except Exception as exc:
            log.error(f"Failed to get health score: {exc}")
            return {}

    def _get_blocked_count_sync(self, initiative_id: str) -> int:
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.metrics.get_blocked_count(initiative_id))
            loop.close()
            return result
        except Exception as exc:
            log.error(f"Failed to get blocked count: {exc}")
            return 0

    def _get_velocity_sync(self) -> dict[str, Any]:
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.metrics.get_velocity(12))
            loop.close()
            return result
        except Exception as exc:
            log.error(f"Failed to get velocity: {exc}")
            return {}

    def _get_conn(self):
        return psycopg2.connect(self.db_url)

    def _get_cache(self, key: str) -> Optional[Any]:
        if key in self._cache:
            entry = self._cache[key]
            if entry["expires_at"] > datetime.now():
                return entry["data"]
            else:
                del self._cache[key]
        return None

    def _set_cache(self, key: str, data: Any, ttl_minutes: int) -> None:
        self._cache[key] = {
            "data": data,
            "expires_at": datetime.now() + timedelta(minutes=ttl_minutes),
        }
