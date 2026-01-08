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



