import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime, timedelta
from uuid import uuid4

from services.reporting.dragonboat_jira_sync import DragonboatJiraSync
from services.reporting.metrics_aggregator import MetricsAggregator
from services.reporting.dashboard_data import DashboardDataProvider
from services.reporting.alert_engine import AlertEngine
from services.reporting.report_generator import ReportGenerator


@pytest.fixture
def mock_db_url():
    return "postgresql://test:test@localhost:5432/dreamfi_test"


@pytest.fixture
def mock_dragonboat_initiatives():
    return [
        {
            "id": "init_001",
            "name": "API Redesign",
            "status": "active",
            "created_at": (datetime.now() - timedelta(days=20)).isoformat(),
            "updated_at": datetime.now().isoformat(),
            "description": "Redesign API for performance",
            "dependencies": [],
        },
        {
            "id": "init_002",
            "name": "Mobile App",
            "status": "at_risk",
            "created_at": (datetime.now() - timedelta(days=45)).isoformat(),
            "updated_at": (datetime.now() - timedelta(days=15)).isoformat(),
            "description": "Build new mobile app",
            "dependencies": ["init_001"],
        },
        {
            "id": "init_003",
            "name": "Infrastructure",
            "status": "planning",
            "created_at": (datetime.now() - timedelta(days=5)).isoformat(),
            "updated_at": datetime.now().isoformat(),
            "description": "Cloud infrastructure upgrade",
            "dependencies": [],
        },
    ]


@pytest.fixture
def mock_jira_epics():
    return [
        {
            "key": "DMON-100",
            "fields": {
                "summary": "API Redesign",
                "description": "init_001",
                "status": {"name": "In Progress", "statusCategory": {"key": "indeterminate"}},
            },
        },
        {
            "key": "DMON-101",
            "fields": {
                "summary": "Mobile App",
                "description": "init_002",
                "status": {"name": "Blocked", "statusCategory": {"key": "indeterminate"}},
            },
        },
    ]


class TestDragonboatJiraSync:
    @patch("services.reporting.dragonboat_jira_sync.psycopg2.connect")
    @patch("services.reporting.dragonboat_jira_sync.DragonboatClient")
    @patch("services.reporting.dragonboat_jira_sync.JiraClient")
    async def test_sync_dragonboat_to_jira_new_epic(self, mock_jira_client, mock_db_client, mock_conn, mock_db_url, mock_dragonboat_initiatives):
        mock_cursor = MagicMock()
        mock_conn.return_value.cursor.return_value = mock_cursor

        sync = DragonboatJiraSync(db_url=mock_db_url)

        with patch.object(sync, "dragonboat") as mock_dragon:
            with patch.object(sync, "jira") as mock_jira:
                mock_dragon.async_get_initiatives = AsyncMock(return_value=mock_dragonboat_initiatives)
                mock_jira.create_epic.return_value = {"key": "DMON-999"}

                result = await sync.sync_dragonboat_to_jira("init_001")

                assert result["success"] is True
                assert result["jira_epic_key"] == "DMON-999"
                mock_jira.create_epic.assert_called_once()

    @patch("services.reporting.dragonboat_jira_sync.psycopg2.connect")
    @patch("services.reporting.dragonboat_jira_sync.DragonboatClient")
    @patch("services.reporting.dragonboat_jira_sync.JiraClient")
    async def test_sync_dragonboat_to_jira_missing_initiative(self, mock_jira_client, mock_db_client, mock_conn, mock_db_url):
        mock_cursor = MagicMock()
        mock_conn.return_value.cursor.return_value = mock_cursor

        sync = DragonboatJiraSync(db_url=mock_db_url)

        with patch.object(sync, "dragonboat") as mock_dragon:
            mock_dragon.async_get_initiatives = AsyncMock(return_value=[])

            result = await sync.sync_dragonboat_to_jira("init_999")

            assert result["success"] is False
            assert "not found" in result["error"].lower()

    @patch("services.reporting.dragonboat_jira_sync.psycopg2.connect")
    @patch("services.reporting.dragonboat_jira_sync.DragonboatClient")
    @patch("services.reporting.dragonboat_jira_sync.JiraClient")
    def test_get_sync_status(self, mock_jira_client, mock_db_client, mock_conn, mock_db_url):
        mock_cursor = MagicMock()
        mock_conn.return_value.cursor.return_value = mock_cursor

        sync_time = datetime.now()
        mapping_id = uuid4()

        mock_cursor.fetchall.return_value = [
            (mapping_id, "init_001", "DMON-100", sync_time, "bidir", "in_sync", sync_time),
            (uuid4(), "init_002", "DMON-101", sync_time, "bidir", "conflict", sync_time),
        ]

        sync = DragonboatJiraSync(db_url=mock_db_url)
        status = sync.get_sync_status()

        assert status["total_mappings"] == 2
        assert len(status["mappings"]) == 2
        assert status["mappings"][0]["dragonboat_initiative_id"] == "init_001"


class TestMetricsAggregator:
    @patch("services.reporting.metrics_aggregator.psycopg2.connect")
    @patch("services.reporting.metrics_aggregator.DragonboatClient")
    @patch("services.reporting.metrics_aggregator.JiraClient")
    async def test_get_velocity(self, mock_jira_client, mock_db_client, mock_conn, mock_db_url):
        mock_cursor = MagicMock()
        mock_conn.return_value.cursor.return_value = mock_cursor

        metrics = MetricsAggregator(db_url=mock_db_url)

        with patch.object(metrics, "jira") as mock_jira:
            mock_jira.get_sprint_data.return_value = {
                "sprint": {"id": 1, "name": "Sprint 1"},
                "completed_story_points": 25,
            }

            velocity = await metrics.get_velocity(12)

            assert "average_velocity" in velocity
            assert len(velocity["sprints"]) > 0

    @patch("services.reporting.metrics_aggregator.psycopg2.connect")
    @patch("services.reporting.metrics_aggregator.DragonboatClient")
    @patch("services.reporting.metrics_aggregator.JiraClient")
    async def test_get_quality_metrics(self, mock_jira_client, mock_db_client, mock_conn, mock_db_url, mock_jira_epics):
        mock_cursor = MagicMock()
        mock_conn.return_value.cursor.return_value = mock_cursor

        metrics = MetricsAggregator(db_url=mock_db_url)

        with patch.object(metrics, "dragonboat") as mock_dragon:
            with patch.object(metrics, "jira") as mock_jira:
                mock_dragon.async_get_initiatives = AsyncMock(return_value=[
                    {"id": "init_001", "name": "API Redesign"}
                ])
                mock_jira.get_epics.return_value = mock_jira_epics
                mock_jira.get_epic_stories.return_value = [
                    {
                        "key": "DMON-1",
                        "fields": {"issuetype": {"name": "Story"}},
                    },
                    {
                        "key": "DMON-2",
                        "fields": {"issuetype": {"name": "Bug"}},
                    },
                ]

                quality = await metrics.get_quality_metrics("init_001")

                assert "bug_escape_rate" in quality
                assert "defect_density" in quality

    @patch("services.reporting.metrics_aggregator.psycopg2.connect")
    @patch("services.reporting.metrics_aggregator.DragonboatClient")
    @patch("services.reporting.metrics_aggregator.JiraClient")
    async def test_get_health_score(self, mock_jira_client, mock_db_client, mock_conn, mock_db_url):
        mock_cursor = MagicMock()
        mock_conn.return_value.cursor.return_value = mock_cursor

        metrics = MetricsAggregator(db_url=mock_db_url)

        with patch.object(metrics, "get_velocity") as mock_velocity:
            with patch.object(metrics, "get_cycle_time") as mock_cycle:
                with patch.object(metrics, "get_quality_metrics") as mock_quality:
                    with patch.object(metrics, "dragonboat") as mock_dragon:
                        mock_velocity.return_value = {"average_velocity": 20}
                        mock_cycle.return_value = {"cycle_time_days": 25}
                        mock_quality.return_value = {"bug_escape_rate": 5}
                        mock_dragon.async_get_initiatives = AsyncMock(return_value=[
                            {"id": "init_001", "status": "active"}
                        ])

                        health = await metrics.get_health_score("init_001")

                        assert "health_score" in health
                        assert health["health_score"] > 0
                        assert health["health_score"] <= 100


class TestAlertEngine:
    @patch("services.reporting.alert_engine.psycopg2.connect")
    @patch("services.reporting.alert_engine.DragonboatClient")
    @patch("services.reporting.alert_engine.JiraClient")
    async def test_check_missed_sla_alert(self, mock_jira_client, mock_db_client, mock_conn, mock_db_url, mock_dragonboat_initiatives):
        mock_cursor = MagicMock()
        mock_conn.return_value.cursor.return_value = mock_cursor

        alerts = AlertEngine(db_url=mock_db_url)
        alerts.sla_days = 30

        with patch.object(alerts, "dragonboat") as mock_dragon:
            mock_dragon.async_get_initiatives = AsyncMock(return_value=mock_dragonboat_initiatives)

            sla_alerts = await alerts._check_missed_slas()

            missed = [a for a in sla_alerts if a.get("alert_type") == "missed_sla"]
            assert len(missed) > 0
            assert "Mobile App" in missed[0]["message"]

    @patch("services.reporting.alert_engine.psycopg2.connect")
    @patch("services.reporting.alert_engine.DragonboatClient")
    @patch("services.reporting.alert_engine.JiraClient")
    async def test_check_no_progress_alert(self, mock_jira_client, mock_db_client, mock_conn, mock_db_url, mock_dragonboat_initiatives):
        mock_cursor = MagicMock()
        mock_conn.return_value.cursor.return_value = mock_cursor

        alerts = AlertEngine(db_url=mock_db_url)
        alerts.no_progress_threshold_days = 10

        with patch.object(alerts, "dragonboat") as mock_dragon:
            mock_dragon.async_get_initiatives = AsyncMock(return_value=mock_dragonboat_initiatives)

            progress_alerts = await alerts._check_no_progress()

            no_progress = [a for a in progress_alerts if a.get("alert_type") == "no_progress"]
            assert len(no_progress) > 0
            assert "zero progress" in no_progress[0]["message"].lower()

    @patch("services.reporting.alert_engine.psycopg2.connect")
    @patch("services.reporting.alert_engine.DragonboatClient")
    @patch("services.reporting.alert_engine.JiraClient")
    async def test_check_dependency_cycles(self, mock_jira_client, mock_db_client, mock_conn, mock_db_url):
        mock_cursor = MagicMock()
        mock_conn.return_value.cursor.return_value = mock_cursor

        cyclic_initiatives = [
            {
                "id": "init_a",
                "name": "Task A",
                "status": "active",
                "dependencies": ["init_b"],
            },
            {
                "id": "init_b",
                "name": "Task B",
                "status": "active",
                "dependencies": ["init_a"],
            },
        ]

        alerts = AlertEngine(db_url=mock_db_url)

        with patch.object(alerts, "dragonboat") as mock_dragon:
            mock_dragon.async_get_initiatives = AsyncMock(return_value=cyclic_initiatives)

            cycle_alerts = await alerts._check_dependency_cycles()

            assert len(cycle_alerts) > 0
            assert "cycle" in cycle_alerts[0]["message"].lower()


class TestReportGenerator:
    @patch("services.reporting.report_generator.ReportGenerator.dragonboat")
    @patch("services.reporting.report_generator.ReportGenerator.jira")
    async def test_generate_weekly_report(self, mock_jira, mock_dragon, mock_db_url, mock_dragonboat_initiatives):
        report = ReportGenerator(db_url=mock_db_url)

        with patch.object(report, "dragonboat") as mock_db:
            with patch.object(report, "_get_health_score_sync") as mock_health:
                with patch.object(report, "_get_blocked_count_sync") as mock_blocked:
                    mock_db.async_get_initiatives = AsyncMock(return_value=mock_dragonboat_initiatives)
                    mock_health.return_value = {"health_score": 75}
                    mock_blocked.return_value = 0

                    report_content = await report.generate_weekly("markdown")

                    assert "Weekly Status Report" in report_content
                    assert "API Redesign" in report_content
                    assert "Health Score" in report_content

    @patch("services.reporting.report_generator.ReportGenerator.dragonboat")
    @patch("services.reporting.report_generator.ReportGenerator.jira")
    async def test_generate_monthly_report(self, mock_jira, mock_dragon, mock_db_url, mock_dragonboat_initiatives):
        report = ReportGenerator(db_url=mock_db_url)

        with patch.object(report, "dragonboat") as mock_db:
            with patch.object(report, "metrics") as mock_metrics:
                with patch.object(report, "_get_health_score_sync") as mock_health:
                    with patch.object(report, "_get_blocked_count_sync") as mock_blocked:
                        mock_db.async_get_initiatives = AsyncMock(return_value=mock_dragonboat_initiatives)
                        mock_metrics.get_velocity = AsyncMock(return_value={"average_velocity": 22})
                        mock_metrics.get_on_schedule_rate = AsyncMock(return_value=75.0)
                        mock_health.return_value = {"health_score": 75}
                        mock_blocked.return_value = 0

                        report_content = await report.generate_monthly("markdown")

                        assert "Monthly Metrics Summary" in report_content
                        assert "Velocity" in report_content

    @patch("services.reporting.report_generator.ReportGenerator.dragonboat")
    @patch("services.reporting.report_generator.ReportGenerator.jira")
    async def test_generate_dependency_report(self, mock_jira, mock_dragon, mock_db_url, mock_dragonboat_initiatives):
        report = ReportGenerator(db_url=mock_db_url)

        with patch.object(report, "dragonboat") as mock_db:
            with patch.object(report, "_get_health_score_sync") as mock_health:
                with patch.object(report, "_get_blocked_count_sync") as mock_blocked:
                    mock_db.async_get_initiatives = AsyncMock(return_value=mock_dragonboat_initiatives)
                    mock_health.return_value = {"health_score": 75}
                    mock_blocked.return_value = 1

                    report_content = await report.generate_dependency_report("markdown")

                    assert "Dependency" in report_content
                    assert "Risk" in report_content

    async def test_report_json_format(self, mock_db_url, mock_dragonboat_initiatives):
        report = ReportGenerator(db_url=mock_db_url)

        with patch.object(report, "dragonboat") as mock_db:
            with patch.object(report, "_get_health_score_sync") as mock_health:
                with patch.object(report, "_get_blocked_count_sync") as mock_blocked:
                    mock_db.async_get_initiatives = AsyncMock(return_value=mock_dragonboat_initiatives)
                    mock_health.return_value = {"health_score": 75}
                    mock_blocked.return_value = 0

                    report_content = await report.generate_weekly("json")

                    import json
                    parsed = json.loads(report_content)
                    assert parsed["type"] == "weekly"
                    assert "metrics" in parsed


class TestDashboardDataProvider:
    def test_get_initiative_health(self, mock_db_url):
        dashboard = DashboardDataProvider(db_url=mock_db_url)

        with patch.object(dashboard, "_get_health_score_sync") as mock_health:
            with patch.object(dashboard, "_get_blocked_count_sync") as mock_blocked:
                with patch.object(dashboard, "jira") as mock_jira:
                    mock_health.return_value = {"health_score": 80, "on_schedule": 1}
                    mock_blocked.return_value = 0
                    mock_jira.get_epics.return_value = []

                    health = dashboard.get_initiative_health("init_001")

                    assert health["health_score"] == 80
                    assert health["blockers"] == 0

    async def test_get_team_velocity(self, mock_db_url):
        dashboard = DashboardDataProvider(db_url=mock_db_url)

        with patch.object(dashboard, "_get_velocity_sync") as mock_velocity:
            mock_velocity.return_value = {
                "average_velocity": 22,
                "sprints": [
                    {"sprint_name": "Sprint 1", "completed_story_points": 20},
                    {"sprint_name": "Sprint 2", "completed_story_points": 24},
                ]
            }

            velocity = dashboard.get_team_velocity()

            assert velocity["average_velocity"] == 22
            assert len(velocity["velocity_trend"]) > 0

    def test_cache_functionality(self, mock_db_url):
        dashboard = DashboardDataProvider(db_url=mock_db_url, cache_ttl_minutes=1)

        dashboard._set_cache("test_key", {"data": "test"})
        cached = dashboard._get_cache("test_key")

        assert cached is not None
        assert cached["data"] == "test"
