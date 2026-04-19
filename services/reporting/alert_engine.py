import logging
from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import uuid4
import psycopg2

from integrations.dragonboat_client import DragonboatClient
from integrations.jira_client import JiraClient
from config import config as _cfg

log = logging.getLogger(__name__)


class AlertEngine:
    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or _cfg.__dict__.get("database_url", "postgresql://dreamfi:password@localhost:5432/dreamfi_dev")
        self.dragonboat = DragonboatClient()
        self.jira = JiraClient()
        self._ensure_tables()
        self.sla_days = 30
        self.blocked_threshold_days = 5
        self.no_progress_threshold_days = 10
        self.capacity_drop_threshold = 0.1

    def _get_conn(self):
        return psycopg2.connect(self.db_url)

    def _ensure_tables(self):
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS reporting_alerts (
                id UUID PRIMARY KEY,
                initiative_id TEXT,
                alert_type TEXT,
                severity TEXT,
                message TEXT,
                first_detected_at TIMESTAMP,
                last_updated_at TIMESTAMP,
                status TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            );
            """)
            conn.commit()
        finally:
            cursor.close()
            conn.close()

    async def check_alerts(self) -> list[dict[str, Any]]:
        alerts = []

        alerts.extend(await self._check_missed_slas())
        alerts.extend(await self._check_blocked_initiatives())
        alerts.extend(await self._check_no_progress())
        alerts.extend(await self._check_dependency_cycles())
        alerts.extend(await self._check_capacity_overflow())

        return alerts

    async def _check_missed_slas(self) -> list[dict[str, Any]]:
        alerts = []
        try:
            initiatives = await self.dragonboat.async_get_initiatives()

            for initiative in initiatives:
                initiative_id = initiative.get("id")
                created_at_str = initiative.get("created_at")
                status = initiative.get("status", "")

                if created_at_str and status not in ["completed", "cancelled"]:
                    created_at = datetime.fromisoformat(created_at_str)
                    days_elapsed = (datetime.now() - created_at).days

                    if days_elapsed > self.sla_days:
                        existing_alert = self._get_alert(initiative_id, "missed_sla")
                        if existing_alert:
                            self._update_alert(existing_alert["id"], "open")
                        else:
                            alert = {
                                "initiative_id": initiative_id,
                                "alert_type": "missed_sla",
                                "severity": "high",
                                "message": f"Initiative '{initiative.get('name')}' missed SLA (running for {days_elapsed} days)",
                                "status": "open",
                            }
                            self._create_alert(alert)
                            alerts.append(alert)

        except Exception as exc:
            log.error(f"Failed to check missed SLAs: {exc}")

        return alerts

    async def _check_blocked_initiatives(self) -> list[dict[str, Any]]:
        alerts = []
        try:
            initiatives = await self.dragonboat.async_get_initiatives()
            epics = self.jira.get_epics("DMON")

            for initiative in initiatives:
                initiative_id = initiative.get("id")

                matching_epic = None
                for epic in epics:
                    if initiative_id in epic.get("description", ""):
                        matching_epic = epic
                        break

                if matching_epic:
                    stories = self.jira.get_epic_stories(matching_epic.get("key"))
                    blocked_stories = [s for s in stories if "blocked" in s.get("fields", {}).get("status", {}).get("name", "").lower()]

                    if blocked_stories:
                        blocked_time_hours = 24
                        try:
                            status_change = blocked_stories[0].get("changelog", {}).get("histories", [])
                            if status_change:
                                blocked_since = datetime.fromisoformat(status_change[0].get("created", ""))
                                blocked_time_hours = (datetime.now() - blocked_since).total_seconds() / 3600
                        except:
                            pass

                        if blocked_time_hours > (self.blocked_threshold_days * 24):
                            existing_alert = self._get_alert(initiative_id, "blocked")
                            if existing_alert:
                                self._update_alert(existing_alert["id"], "open")
                            else:
                                alert = {
                                    "initiative_id": initiative_id,
                                    "alert_type": "blocked",
                                    "severity": "critical",
                                    "message": f"Initiative '{initiative.get('name')}' has {len(blocked_stories)} blocked items for {int(blocked_time_hours / 24)} days",
                                    "status": "open",
                                }
                                self._create_alert(alert)
                                alerts.append(alert)

        except Exception as exc:
            log.error(f"Failed to check blocked initiatives: {exc}")

        return alerts

    async def _check_no_progress(self) -> list[dict[str, Any]]:
        alerts = []
        try:
            initiatives = await self.dragonboat.async_get_initiatives()

            for initiative in initiatives:
                initiative_id = initiative.get("id")
                last_updated_str = initiative.get("updated_at")

                if last_updated_str and initiative.get("status") not in ["completed", "cancelled"]:
                    last_updated = datetime.fromisoformat(last_updated_str)
                    days_since_update = (datetime.now() - last_updated).days

                    if days_since_update > self.no_progress_threshold_days:
                        existing_alert = self._get_alert(initiative_id, "no_progress")
                        if existing_alert:
                            self._update_alert(existing_alert["id"], "open")
                        else:
                            alert = {
                                "initiative_id": initiative_id,
                                "alert_type": "no_progress",
                                "severity": "medium",
                                "message": f"Initiative '{initiative.get('name')}' has had zero progress for {days_since_update} days",
                                "status": "open",
                            }
                            self._create_alert(alert)
                            alerts.append(alert)

        except Exception as exc:
            log.error(f"Failed to check no progress: {exc}")

        return alerts

    async def _check_dependency_cycles(self) -> list[dict[str, Any]]:
        alerts = []
        try:
            initiatives = await self.dragonboat.async_get_initiatives()
            initiative_map = {i.get("id"): i for i in initiatives}

            visited = set()
            rec_stack = set()

            def has_cycle(node_id, path=None):
                if path is None:
                    path = []

                if node_id in rec_stack:
                    return True, path + [node_id]

                if node_id in visited:
                    return False, []

                visited.add(node_id)
                rec_stack.add(node_id)

                node = initiative_map.get(node_id)
                if node:
                    dependencies = node.get("dependencies", [])
                    for dep in dependencies:
                        dep_id = dep.get("id") if isinstance(dep, dict) else dep
                        is_cycle, cycle_path = has_cycle(dep_id, path + [node_id])
                        if is_cycle:
                            return True, cycle_path

                rec_stack.remove(node_id)
                return False, []

            for initiative_id in initiative_map.keys():
                if initiative_id not in visited:
                    is_cycle, cycle_path = has_cycle(initiative_id)
                    if is_cycle:
                        cycle_str = " → ".join(cycle_path)
                        existing_alert = self._get_alert(initiative_id, "cycle_risk")
                        if existing_alert:
                            self._update_alert(existing_alert["id"], "open")
                        else:
                            alert = {
                                "initiative_id": initiative_id,
                                "alert_type": "cycle_risk",
                                "severity": "critical",
                                "message": f"Dependency cycle detected: {cycle_str}",
                                "status": "open",
                            }
                            self._create_alert(alert)
                            alerts.append(alert)

        except Exception as exc:
            log.error(f"Failed to check dependency cycles: {exc}")

        return alerts

    async def _check_capacity_overflow(self) -> list[dict[str, Any]]:
        alerts = []
        try:
            board_id = 1
            sprint_data = self.jira.get_sprint_data(board_id)

            if sprint_data.get("sprint"):
                current_velocity = sprint_data.get("completed_story_points", 0)

                conn = self._get_conn()
                cursor = conn.cursor()
                cursor.execute("""
                SELECT AVG(velocity_points) as avg_velocity
                FROM reporting_metrics
                WHERE week_of >= NOW() - INTERVAL '8 weeks'
                """)
                row = cursor.fetchone()
                cursor.close()
                conn.close()

                if row and row[0]:
                    avg_velocity = row[0]
                    velocity_drop = (avg_velocity - current_velocity) / max(avg_velocity, 1)

                    if velocity_drop > self.capacity_drop_threshold:
                        existing_alert = self._get_alert(None, "capacity")
                        if existing_alert:
                            self._update_alert(existing_alert["id"], "open")
                        else:
                            alert = {
                                "initiative_id": None,
                                "alert_type": "capacity",
                                "severity": "high",
                                "message": f"Team velocity dropped {int(velocity_drop * 100)}% (from {avg_velocity:.0f} to {current_velocity} story points)",
                                "status": "open",
                            }
                            self._create_alert(alert)
                            alerts.append(alert)

        except Exception as exc:
            log.error(f"Failed to check capacity overflow: {exc}")

        return alerts

    def _create_alert(self, alert: dict[str, Any]) -> None:
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("""
            INSERT INTO reporting_alerts
            (id, initiative_id, alert_type, severity, message, first_detected_at, last_updated_at, status)
            VALUES (%s, %s, %s, %s, %s, NOW(), NOW(), %s)
            """, (
                str(uuid4()),
                alert.get("initiative_id"),
                alert.get("alert_type"),
                alert.get("severity"),
                alert.get("message"),
                alert.get("status"),
            ))
            conn.commit()
        finally:
            cursor.close()
            conn.close()

    def _get_alert(self, initiative_id: Optional[str], alert_type: str) -> Optional[dict[str, Any]]:
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("""
            SELECT id, status FROM reporting_alerts
            WHERE initiative_id = %s AND alert_type = %s AND status = 'open'
            LIMIT 1
            """, (initiative_id, alert_type))
            row = cursor.fetchone()
            if row:
                return {"id": str(row[0]), "status": row[1]}
            return None
        finally:
            cursor.close()
            conn.close()

    def _update_alert(self, alert_id: str, status: str) -> None:
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("""
            UPDATE reporting_alerts
            SET last_updated_at = NOW(), status = %s
            WHERE id = %s
            """, (status, alert_id))
            conn.commit()
        finally:
            cursor.close()
            conn.close()
