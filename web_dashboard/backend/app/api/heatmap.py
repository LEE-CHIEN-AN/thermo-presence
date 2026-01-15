from fastapi import APIRouter, Query

from app.services.environment_service import EnvironmentService


router = APIRouter()
env_service = EnvironmentService()


@router.get("/temperature")
def temperature_heatmap(
    timestamp: str = Query(..., description="Base timestamp (ISO string)"),
):
    """
    Placeholder temperature heatmap endpoint.
    For now it just returns latest sensor values near the timestamp.
    """
    return env_service.get_spatial_snapshot(timestamp=timestamp)




