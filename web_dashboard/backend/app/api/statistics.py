from typing import Optional
from fastapi import APIRouter, Query

from app.services.visualization_service import VisualizationService


router = APIRouter()
vis_service = VisualizationService()


@router.get("/people-trend")
def people_trend(
    session_id: str = Query(..., description="Session ID"),
    interval: str = Query("hour", description="Aggregation interval: hour/day"),
    start_time: Optional[str] = Query(None, description="ISO start time (optional, UTC)"),
    end_time: Optional[str] = Query(None, description="ISO end time (optional, UTC)"),
):
    """
    Get people count trend aggregated by time interval.
    """
    return vis_service.get_people_trend(
        session_id=session_id,
        interval=interval,
        start_time=start_time,
        end_time=end_time,
    )


@router.get("/people-distribution")
def people_distribution(
    session_id: str = Query(..., description="Session ID"),
    start_time: Optional[str] = Query(None, description="ISO start time (optional, UTC)"),
    end_time: Optional[str] = Query(None, description="ISO end time (optional, UTC)"),
):
    """
    Get distribution of people counts (histogram).
    """
    return vis_service.get_people_distribution(
        session_id=session_id,
        start_time=start_time,
        end_time=end_time,
    )


@router.get("/time-period-stats")
def time_period_stats(
    session_id: str = Query(..., description="Session ID"),
    start_time: Optional[str] = Query(None, description="ISO start time (optional, UTC)"),
    end_time: Optional[str] = Query(None, description="ISO end time (optional, UTC)"),
):
    """
    Get summary statistics for a time period.
    """
    return vis_service.get_time_period_stats(
        session_id=session_id,
        start_time=start_time,
        end_time=end_time,
    )


@router.get("/people-env-timeseries")
def people_env_timeseries(
    session_id: str = Query(..., description="Session ID"),
    start_time: Optional[str] = Query(None, description="ISO start time (optional, UTC)"),
    end_time: Optional[str] = Query(None, description="ISO end time (optional, UTC)"),
    sensor_name: Optional[str] = Query(None, description="Filter by wiolink sensor name (optional)"),
    max_delta_minutes: int = Query(
        5,
        description="Maximum time difference in minutes when matching wiolink records to people counts",
        ge=1,
        le=60,
    ),
):
    """
    Get people count timeseries aligned with environmental sensor (wiolink) data.
    """
    return vis_service.get_people_env_timeseries(
        session_id=session_id,
        start_time=start_time,
        end_time=end_time,
        sensor_name=sensor_name,
        max_delta_minutes=max_delta_minutes,
    )



