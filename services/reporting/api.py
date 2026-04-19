import logging
from datetime import datetime, timedelta
from typing import Any, Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from services.reporting.dragonboat_jira_sync import DragonboatJiraSync
from services.reporting.metrics_aggregator import MetricsAggregator
from services.reporting.dashboard_data import DashboardDataProvider
from services.reporting.alert_engine import AlertEngine
from services.reporting.report_generator import ReportGenerator

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/reporting", tags=["reporting"])

sync_service = DragonboatJiraSync()
metrics_service = MetricsAggregator()
dashboard_service = DashboardDataProvider()
alert_service = AlertEngine()
report_service = ReportGenerator()

_cache = {}


def _get_cached(key: str, ttl_seconds: int = 1800) -> Optional[Any]:
    if key in _cache:
        entry = _cache[key]
        if entry["expires_at"] > datetime.now():
            return {"data": entry["data"], "cache_age": (datetime.now() - entry["created_at"]).total_seconds()}
        else:
            del _cache[key]
    return None


def _set_cache(key: str, data: Any) -> None:
    _cache[key] = {
        "data": data,
        "created_at": datetime.now(),
        "expires_at": datetime.now() + timedelta(seconds=1800),
    }


@router.get("/health")
async def get_health():
    cache_result = _get_cached("dashboard_health")
    if cache_result:
        response_data = {
            "timestamp": datetime.now().isoformat(),
            "cache_age": cache_result["cache_age"],
            "next_refresh": (cache_result["data"]["expires_at"] - datetime.now()).total_seconds(),
        }
        response_data.update(cache_result["data"]["content"])
        return JSONResponse(content=response_data)

    try:
        initiatives_count = 0
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            initiatives = loop.run_until_complete(sync_service.dragonboat.async_get_initiatives())
            loop.close()
            initiatives_count = len(initiatives)
        except:
            pass

        health = {
            "status": "healthy",
            "total_initiatives": initiatives_count,
            "synced_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(seconds=1800)).isoformat(),
        }
        _set_cache("dashboard_health", health)

        return JSONResponse(content={
            "timestamp": datetime.now().isoformat(),
            "cache_age": 0,
            "next_refresh": 1800,
            **health,
        })

    except Exception as exc:
        log.error(f"Failed to get health: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/metrics")
async def get_metrics(weeks: int = Query(12, ge=1, le=52)):
    cache_result = _get_cached("metrics")
    if cache_result:
        return JSONResponse(content={
            "timestamp": datetime.now().isoformat(),
            "cache_age": cache_result["cache_age"],
            "next_refresh": 1800,
            **cache_result["data"],
        })

    try:
        velocity_data = await metrics_service.get_velocity(weeks)
        on_schedule_rate = await metrics_service.get_on_schedule_rate()

        metrics_data = {
            "period_weeks": weeks,
            "average_velocity": velocity_data.get("average_velocity", 0),
            "on_schedule_rate": on_schedule_rate,
        }
        _set_cache("metrics", metrics_data)

        return JSONResponse(content={
            "timestamp": datetime.now().isoformat(),
            "cache_age": 0,
            "next_refresh": 1800,
            **metrics_data,
        })

    except Exception as exc:
        log.error(f"Failed to get metrics: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/alerts")
async def get_alerts():
    cache_result = _get_cached("alerts", ttl_seconds=300)
    if cache_result:
        return JSONResponse(content={
            "timestamp": datetime.now().isoformat(),
            "cache_age": cache_result["cache_age"],
            "next_refresh": 300,
            **cache_result["data"],
        })

    try:
        alerts = await alert_service.check_alerts()
        
        alert_data = {
            "critical_count": len([a for a in alerts if a.get("severity") == "critical"]),
            "high_count": len([a for a in alerts if a.get("severity") == "high"]),
            "total_alerts": len(alerts),
            "alerts": alerts,
        }
        _set_cache("alerts", alert_data)

        return JSONResponse(content={
            "timestamp": datetime.now().isoformat(),
            "cache_age": 0,
            "next_refresh": 300,
            **alert_data,
        })

    except Exception as exc:
        log.error(f"Failed to get alerts: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/initiatives/{initiative_id}")
async def get_initiative(initiative_id: str):
    try:
        mapping = sync_service._get_mapping(initiative_id)
        if not mapping:
            raise HTTPException(status_code=404, detail="Initiative not found")

        health = dashboard_service.get_initiative_health(initiative_id)
        blocked = dashboard_service._get_blocked_count_sync(initiative_id)

        return JSONResponse(content={
            "timestamp": datetime.now().isoformat(),
            "mapping": mapping,
            "health": health,
            "blocked_count": blocked,
        })

    except Exception as exc:
        log.error(f"Failed to get initiative: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/sync-now")
async def trigger_sync(initiative_id: Optional[str] = Query(None)):
    try:
        if initiative_id:
            result = await sync_service.sync_dragonboat_to_jira(initiative_id)
        else:
            try:
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                initiatives = loop.run_until_complete(sync_service.dragonboat.async_get_initiatives())
                loop.close()
            except:
                initiatives = []

            results = []
            for initiative in initiatives:
                result = await sync_service.sync_dragonboat_to_jira(initiative.get("id"))
                results.append(result)

            return JSONResponse(content={
                "timestamp": datetime.now().isoformat(),
                "synced": len([r for r in results if r.get("success")]),
                "failed": len([r for r in results if not r.get("success")]),
                "results": results,
            })

        return JSONResponse(content={
            "timestamp": datetime.now().isoformat(),
            **result,
        })

    except Exception as exc:
        log.error(f"Failed to trigger sync: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/reports/weekly")
async def get_weekly_report(format: str = Query("markdown", regex="^(markdown|html|json)$")):
    try:
        report_content = await report_service.generate_weekly(format)

        return JSONResponse(content={
            "timestamp": datetime.now().isoformat(),
            "report_type": "weekly",
            "format": format,
            "content": report_content,
        })

    except Exception as exc:
        log.error(f"Failed to generate weekly report: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/reports/monthly")
async def get_monthly_report(format: str = Query("markdown", regex="^(markdown|html|json)$")):
    try:
        report_content = await report_service.generate_monthly(format)

        return JSONResponse(content={
            "timestamp": datetime.now().isoformat(),
            "report_type": "monthly",
            "format": format,
            "content": report_content,
        })

    except Exception as exc:
        log.error(f"Failed to generate monthly report: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/reports/dependency")
async def get_dependency_report(format: str = Query("markdown", regex="^(markdown|html|json)$")):
    try:
        report_content = await report_service.generate_dependency_report(format)

        return JSONResponse(content={
            "timestamp": datetime.now().isoformat(),
            "report_type": "dependency",
            "format": format,
            "content": report_content,
        })

    except Exception as exc:
        log.error(f"Failed to generate dependency report: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
