import logging
from datetime import datetime, timedelta
from typing import Any, Optional
import json

from integrations.dragonboat_client import DragonboatClient
from integrations.jira_client import JiraClient
from services.reporting.metrics_aggregator import MetricsAggregator
from config import config as _cfg

log = logging.getLogger(__name__)


class ReportGenerator:
    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or _cfg.__dict__.get("database_url", "postgresql://dreamfi:password@localhost:5432/dreamfi_dev")
        self.dragonboat = DragonboatClient()
        self.jira = JiraClient()
        self.metrics = MetricsAggregator(db_url)

    async def generate_weekly(self, format_type: str = "markdown") -> str:
        try:
            initiatives = await self.dragonboat.async_get_initiatives()

            report_lines = []
            report_lines.append("# Weekly Status Report")
            report_lines.append(f"**Week of:** {datetime.now().strftime('%B %d, %Y')}")
            report_lines.append("")

            total_health = 0
            on_schedule_count = 0

            for initiative in initiatives:
                initiative_id = initiative.get("id")
                initiative_name = initiative.get("name")
                status = initiative.get("status")

                health_data = self._get_health_score_sync(initiative_id)
                health_score = health_data.get("health_score", 0)
                total_health += health_score

                if status != "at_risk":
                    on_schedule_count += 1

                block_count = self._get_blocked_count_sync(initiative_id)

                status_emoji = "🟢" if health_score >= 70 else "🟡" if health_score >= 50 else "🔴"
                block_indicator = f"⚠️ {block_count} blocked" if block_count > 0 else "✅ No blockers"

                report_lines.append(f"## {status_emoji} {initiative_name}")
                report_lines.append(f"- **Status:** {status}")
                report_lines.append(f"- **Health Score:** {health_score:.1f}/100")
                report_lines.append(f"- **Blockers:** {block_indicator}")
                report_lines.append("")

            avg_health = total_health / max(len(initiatives), 1)
            on_schedule_rate = (on_schedule_count / max(len(initiatives), 1)) * 100

            report_lines.append("## Summary")
            report_lines.append(f"- **Average Health Score:** {avg_health:.1f}/100")
            report_lines.append(f"- **On-Schedule Rate:** {on_schedule_rate:.1f}%")
            report_lines.append(f"- **Total Initiatives:** {len(initiatives)}")

            report_content = "\n".join(report_lines)

            if format_type == "html":
                return self._convert_markdown_to_html(report_content)
            elif format_type == "json":
                return json.dumps({
                    "type": "weekly",
                    "generated_at": datetime.now().isoformat(),
                    "content": report_content,
                    "metrics": {
                        "average_health": avg_health,
                        "on_schedule_rate": on_schedule_rate,
                        "total_initiatives": len(initiatives),
                    }
                }, indent=2)

            return report_content

        except Exception as exc:
            log.error(f"Failed to generate weekly report: {exc}")
            return f"Error generating weekly report: {str(exc)}"

    async def generate_monthly(self, format_type: str = "markdown") -> str:
        try:
            initiatives = await self.dragonboat.async_get_initiatives()
            velocity_data = await self.metrics.get_velocity(12)
            on_schedule_rate = await self.metrics.get_on_schedule_rate()

            report_lines = []
            report_lines.append("# Monthly Metrics Summary")
            report_lines.append(f"**Month:** {datetime.now().strftime('%B %Y')}")
            report_lines.append("")

            report_lines.append("## Key Metrics")
            report_lines.append(f"- **Average Velocity:** {velocity_data.get('average_velocity', 0):.1f} story points")
            report_lines.append(f"- **On-Schedule Rate:** {on_schedule_rate:.1f}%")
            report_lines.append(f"- **Active Initiatives:** {len(initiatives)}")
            report_lines.append("")

            report_lines.append("## Initiative Health Breakdown")
            report_lines.append("| Initiative | Status | Health | Blockers |")
            report_lines.append("|---|---|---|---|")

            for initiative in initiatives:
                initiative_id = initiative.get("id")
                initiative_name = initiative.get("name")
                status = initiative.get("status")

                health_data = self._get_health_score_sync(initiative_id)
                health_score = health_data.get("health_score", 0)
                block_count = self._get_blocked_count_sync(initiative_id)

                report_lines.append(f"| {initiative_name} | {status} | {health_score:.1f} | {block_count} |")

            report_lines.append("")
            report_lines.append("## Velocity Trend")
            for sprint in velocity_data.get("sprints", [])[-4:]:
                report_lines.append(f"- {sprint.get('sprint_name')}: {sprint.get('completed_story_points')} SP")

            report_content = "\n".join(report_lines)

            if format_type == "html":
                return self._convert_markdown_to_html(report_content)
            elif format_type == "json":
                return json.dumps({
                    "type": "monthly",
                    "generated_at": datetime.now().isoformat(),
                    "content": report_content,
                    "metrics": {
                        "average_velocity": velocity_data.get("average_velocity", 0),
                        "on_schedule_rate": on_schedule_rate,
                        "total_initiatives": len(initiatives),
                    }
                }, indent=2)

            return report_content

        except Exception as exc:
            log.error(f"Failed to generate monthly report: {exc}")
            return f"Error generating monthly report: {str(exc)}"

    async def generate_dependency_report(self, format_type: str = "markdown") -> str:
        try:
            initiatives = await self.dragonboat.async_get_initiatives()
            initiative_map = {i.get("id"): i for i in initiatives}

            blocked_initiatives = []
            high_risk_initiatives = []

            for initiative in initiatives:
                initiative_id = initiative.get("id")
                dependencies = initiative.get("dependencies", [])

                health_data = self._get_health_score_sync(initiative_id)
                health_score = health_data.get("health_score", 0)
                block_count = self._get_blocked_count_sync(initiative_id)

                if block_count > 0:
                    blocked_initiatives.append({
                        "id": initiative_id,
                        "name": initiative.get("name"),
                        "blocked_count": block_count,
                    })

                if health_score < 50 or len(dependencies) > 3:
                    high_risk_initiatives.append({
                        "id": initiative_id,
                        "name": initiative.get("name"),
                        "health_score": health_score,
                        "dependency_count": len(dependencies),
                    })

            report_lines = []
            report_lines.append("# Dependency & Risk Report")
            report_lines.append(f"**Generated:** {datetime.now().strftime('%B %d, %Y at %H:%M')}")
            report_lines.append("")

            report_lines.append("## Blocked Initiatives")
            if blocked_initiatives:
                for blocked in blocked_initiatives:
                    report_lines.append(f"- **{blocked['name']}**: {blocked['blocked_count']} blocked items")
            else:
                report_lines.append("- No blocked initiatives")

            report_lines.append("")
            report_lines.append("## High-Risk Initiatives")
            if high_risk_initiatives:
                for risk in high_risk_initiatives:
                    report_lines.append(f"- **{risk['name']}**: Health {risk['health_score']:.0f}/100, {risk['dependency_count']} dependencies")
            else:
                report_lines.append("- No high-risk initiatives")

            report_lines.append("")
            report_lines.append("## Dependency Map")
            for initiative in initiatives:
                dependencies = initiative.get("dependencies", [])
                if dependencies:
                    dep_names = []
                    for dep in dependencies:
                        dep_id = dep.get("id") if isinstance(dep, dict) else dep
                        dep_name = initiative_map.get(dep_id, {}).get("name", dep_id)
                        dep_names.append(dep_name)
                    report_lines.append(f"- {initiative.get('name')} depends on: {', '.join(dep_names)}")

            report_content = "\n".join(report_lines)

            if format_type == "html":
                return self._convert_markdown_to_html(report_content)
            elif format_type == "json":
                return json.dumps({
                    "type": "dependency",
                    "generated_at": datetime.now().isoformat(),
                    "content": report_content,
                    "metrics": {
                        "blocked_count": len(blocked_initiatives),
                        "high_risk_count": len(high_risk_initiatives),
                    }
                }, indent=2)

            return report_content

        except Exception as exc:
            log.error(f"Failed to generate dependency report: {exc}")
            return f"Error generating dependency report: {str(exc)}"

    async def generate_on_demand(self, report_type: str, format_type: str = "markdown") -> str:
        if report_type == "weekly":
            return await self.generate_weekly(format_type)
        elif report_type == "monthly":
            return await self.generate_monthly(format_type)
        elif report_type == "dependency":
            return await self.generate_dependency_report(format_type)
        else:
            return f"Unknown report type: {report_type}"

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

    def _convert_markdown_to_html(self, markdown_content: str) -> str:
        try:
            import markdown
            return markdown.markdown(markdown_content)
        except ImportError:
            simple_html = markdown_content.replace(
                "# ", "<h1>").replace("## ", "<h2>").replace("- ", "<li>")
            simple_html = simple_html.replace(
                "**", "<strong>").replace("*", "<em>")
            return f"<html><body>{simple_html}</body></html>"
