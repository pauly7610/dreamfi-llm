import logging
from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import uuid4
import psycopg2
from psycopg2 import sql

from integrations.dragonboat_client import DragonboatClient
from integrations.jira_client import JiraClient
from config import config as _cfg

log = logging.getLogger(__name__)


class MetricsAggregator:
    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or _cfg.__dict__.get("database_url", "postgresql://dreamfi:password@localhost:5432/dreamfi_dev")
        self.dragonboat = DragonboatClient()
        self.jira = JiraClient()
        self._ensure_tables()

    def _get_conn(self):
        return psycopg2.connect(self.db_url)

    def _ensure_tables(self):
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS reporting_metrics (
                id UUID PRIMARY KEY,
                initiative_id TEXT NOT NULL,
                week_of DATE,
                velocity_points INT,
                cycle_time_days FLOAT,
                bug_escape_rate FLOAT,
                defect_density FLOAT,
                on_schedule INT,
                blocked_count INT,
                health_score FLOAT,
                created_at TIMESTAMP DEFAULT NOW()
            );
            """)
            conn.commit()
        finally:
            cursor.close()
            conn.close()

    async def get_velocity(self, weeks: int = 12) -> dict[str, Any]:
        try:
            board_ids = [1]
            velocity_data = []

            for board_id in board_ids:
                sprint_data = self.jira.get_sprint_data(board_id)
                if sprint_data.get("sprint"):
                    sprint = sprint_data["sprint"]
                    completed_sp = sprint_data.get("completed_story_points", 0)
                    velocity_data.append({
                        "sprint_id": sprint.get("id"),
                        "sprint_name": sprint.get("name"),
                        "completed_story_points": completed_sp,
                        "sprint_start": sprint.get("startDate"),
                        "sprint_end": sprint.get("endDate"),
                    })

            return {
                "period_weeks": weeks,
                "sprints": velocity_data,
                "average_velocity": sum(v.get("completed_story_points", 0) for v in velocity_data) / max(len(velocity_data), 1),
            }

        except Exception as exc:
            log.error(f"Failed to get velocity: {exc}")
            return {"error": str(exc), "sprints": []}

    async def get_cycle_time(self, initiative_id: str) -> dict[str, Any]:
        try:
            initiatives = await self.dragonboat.async_get_initiatives()
            initiative = next((i for i in initiatives if i.get("id") == initiative_id), None)
            if not initiative:
                return {"error": "Initiative not found"}

            created_at_str = initiative.get("created_at")
            created_at = datetime.fromisoformat(created_at_str) if created_at_str else None

            epics = self.jira.get_epics("DMON")
            matching_epic = None
            for epic in epics:
                if initiative_id in epic.get("description", ""):
                    matching_epic = epic
                    break

            if matching_epic:
                status_category = matching_epic.get("fields", {}).get("status", {}).get("statusCategory", {}).get("key")
                if status_category == "done":
                    done_at_str = matching_epic.get("fields", {}).get("statuses_history", [])
                    if done_at_str:
                        done_at = datetime.fromisoformat(done_at_str[0]) if done_at_str else datetime.now()
                    else:
                        done_at = datetime.now()

                    if created_at and done_at:
                        cycle_time_days = (done_at - created_at).days
                        return {
                            "initiative_id": initiative_id,
                            "created_at": created_at.isoformat(),
                            "done_at": done_at.isoformat(),
                            "cycle_time_days": cycle_time_days,
                        }

            return {
                "initiative_id": initiative_id,
                "created_at": created_at.isoformat() if created_at else None,
                "cycle_time_days": None,
            }

        except Exception as exc:
            log.error(f"Failed to get cycle time for {initiative_id}: {exc}")
            return {"error": str(exc)}

    async def get_quality_metrics(self, initiative_id: str) -> dict[str, Any]:
        try:
            epics = self.jira.get_epics("DMON")
            matching_epic = None
            for epic in epics:
                if initiative_id in epic.get("description", ""):
                    matching_epic = epic
                    break

            if not matching_epic:
                return {"initiative_id": initiative_id, "bug_escape_rate": 0, "defect_density": 0}

            epic_key = matching_epic.get("key")
            stories = self.jira.get_epic_stories(epic_key)

            total_issues = len(stories)
            bug_issues = [s for s in stories if s.get("fields", {}).get("issuetype", {}).get("name") == "Bug"]
            bug_count = len(bug_issues)

            bug_escape_rate = (bug_count / total_issues * 100) if total_issues > 0 else 0
            defect_density = bug_count / max(total_issues, 1)

            self._store_metrics(
                initiative_id,
                bug_escape_rate=bug_escape_rate,
                defect_density=defect_density,
            )

            return {
                "initiative_id": initiative_id,
                "total_issues": total_issues,
                "bug_count": bug_count,
                "bug_escape_rate": round(bug_escape_rate, 2),
                "defect_density": round(defect_density, 3),
            }

        except Exception as exc:
            log.error(f"Failed to get quality metrics for {initiative_id}: {exc}")
            return {"error": str(exc)}

    async def get_health_score(self, initiative_id: str) -> dict[str, Any]:
        try:
            velocity_data = await self.get_velocity(12)
            avg_velocity = velocity_data.get("average_velocity", 0)

            cycle_time_data = await self.get_cycle_time(initiative_id)
            cycle_time = cycle_time_data.get("cycle_time_days", 0)

            quality_data = await self.get_quality_metrics(initiative_id)
            bug_escape_rate = quality_data.get("bug_escape_rate", 0)

            initiatives = await self.dragonboat.async_get_initiatives()
            initiative = next((i for i in initiatives if i.get("id") == initiative_id), None)
            on_schedule = 1 if initiative and initiative.get("status") != "at_risk" else 0

            velocity_score = min(100, (avg_velocity / 20) * 100) if avg_velocity > 0 else 50
            cycle_time_score = max(0, 100 - (cycle_time / 30) * 100) if cycle_time > 0 else 50
            quality_score = max(0, 100 - bug_escape_rate)
            schedule_score = 100 if on_schedule else 50

            health_score = (velocity_score * 0.25) + (cycle_time_score * 0.25) + (quality_score * 0.25) + (schedule_score * 0.25)

            self._store_metrics(
                initiative_id,
                health_score=health_score,
                on_schedule=on_schedule,
            )

            return {
                "initiative_id": initiative_id,
                "health_score": round(health_score, 2),
                "velocity_score": round(velocity_score, 2),
                "cycle_time_score": round(cycle_time_score, 2),
                "quality_score": round(quality_score, 2),
                "schedule_score": round(schedule_score, 2),
                "on_schedule": on_schedule,
            }

        except Exception as exc:
            log.error(f"Failed to calculate health score for {initiative_id}: {exc}")
            return {"error": str(exc)}

    async def get_blocked_count(self, initiative_id: str) -> int:
        try:
            epics = self.jira.get_epics("DMON")
            matching_epic = None
            for epic in epics:
                if initiative_id in epic.get("description", ""):
                    matching_epic = epic
                    break

            if not matching_epic:
                return 0

            epic_key = matching_epic.get("key")
            stories = self.jira.get_epic_stories(epic_key)

            blocked_count = 0
            for story in stories:
                status = story.get("fields", {}).get("status", {}).get("name", "").lower()
                if "blocked" in status or "stalled" in status:
                    blocked_count += 1

            self._store_metrics(initiative_id, blocked_count=blocked_count)
            return blocked_count

        except Exception as exc:
            log.error(f"Failed to get blocked count for {initiative_id}: {exc}")
            return 0

    async def get_on_schedule_rate(self) -> float:
        try:
            initiatives = await self.dragonboat.async_get_initiatives()
            on_schedule_count = sum(1 for i in initiatives if i.get("status") != "at_risk")
            total_count = len(initiatives)

            on_schedule_rate = (on_schedule_count / total_count * 100) if total_count > 0 else 0
            return round(on_schedule_rate, 2)

        except Exception as exc:
            log.error(f"Failed to get on-schedule rate: {exc}")
            return 0.0

    def _store_metrics(
        self,
        initiative_id: str,
        velocity_points: Optional[int] = None,
        cycle_time_days: Optional[float] = None,
        bug_escape_rate: Optional[float] = None,
        defect_density: Optional[float] = None,
        on_schedule: Optional[int] = None,
        blocked_count: Optional[int] = None,
        health_score: Optional[float] = None,
    ) -> None:
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            week_of = datetime.now().date()
            week_of = week_of - timedelta(days=week_of.weekday())

            cursor.execute("""
            INSERT INTO reporting_metrics
            (id, initiative_id, week_of, velocity_points, cycle_time_days, bug_escape_rate, defect_density, on_schedule, blocked_count, health_score)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                velocity_points = COALESCE(EXCLUDED.velocity_points, reporting_metrics.velocity_points),
                cycle_time_days = COALESCE(EXCLUDED.cycle_time_days, reporting_metrics.cycle_time_days),
                bug_escape_rate = COALESCE(EXCLUDED.bug_escape_rate, reporting_metrics.bug_escape_rate),
                defect_density = COALESCE(EXCLUDED.defect_density, reporting_metrics.defect_density),
                on_schedule = COALESCE(EXCLUDED.on_schedule, reporting_metrics.on_schedule),
                blocked_count = COALESCE(EXCLUDED.blocked_count, reporting_metrics.blocked_count),
                health_score = COALESCE(EXCLUDED.health_score, reporting_metrics.health_score)
            """, (
                str(uuid4()), initiative_id, week_of,
                velocity_points, cycle_time_days, bug_escape_rate, defect_density,
                on_schedule, blocked_count, health_score
            ))
            conn.commit()
        except Exception as exc:
            log.error(f"Failed to store metrics: {exc}")
        finally:
            cursor.close()
            conn.close()
