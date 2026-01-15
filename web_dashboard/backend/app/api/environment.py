from typing import Optional

from fastapi import APIRouter, Query

from app.services.environment_service import EnvironmentService


router = APIRouter()
env_service = EnvironmentService()


@router.get("/latest")
def latest_environment(sensor_name: Optional[str] = Query(None, description="wiolink.name, optional filter")):
    """
    Return latest environment data from wiolink table.
    """
    return env_service.get_latest(sensor_name=sensor_name)


@router.get("/history")
def environment_history(
    sensor_name: str = Query(..., description="wiolink.name"),
    start_time: str = Query(..., description="ISO start time"),
    end_time: str = Query(..., description="ISO end time"),
):
    """
    Return environment history for a single sensor.
    """
    return env_service.get_history(sensor_name=sensor_name, start_time=start_time, end_time=end_time)


@router.get("/air-quality-trend")
def air_quality_trend(
    days: int = Query(
        10,
        description="Number of days to include in CO2/VOC trend (default 10, max 60)",
        ge=1,
        le=60,
    )
):
    """
    Return CO2/VOC trend for 604_air_quality over the last N days.

    This is a backend equivalent of the original Streamlit 10-day CO2/VOC trend.
    """
    return env_service.get_air_quality_trend(days=days)


@router.get("/pm-trend")
def pm_trend(
    days: int = Query(
        10,
        description="Number of days to include in PM trend (default 10, max 60)",
        ge=1,
        le=60,
    )
):
    """
    Return PM1.0/PM2.5/PM10 trend for 604_window over the last N days.
    """
    return env_service.get_pm_trend(days=days)


@router.get("/temp-humidity-trend")
def temp_humidity_trend(
    days: int = Query(
        10,
        description="Number of days to include in trend (default 10, max 60)",
        ge=1,
        le=60,
    ),
    sensor_name: str = Query(
        "604_center",
        description="Sensor name (default: 604_center)",
    ),
):
    """
    Return temperature and humidity trend for a sensor over the last N days.
    """
    return env_service.get_temp_humidity_trend(days=days, sensor_name=sensor_name)

