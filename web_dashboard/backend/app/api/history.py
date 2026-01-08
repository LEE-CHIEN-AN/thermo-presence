from typing import Optional

from fastapi import APIRouter, Query

from app.services.thermal_service import ThermalService


router = APIRouter()
thermal_service = ThermalService()


@router.get("/thermal")
def list_thermal_history(
    session_id: str = Query(..., description="Session ID to filter, e.g. '604_windowside'"),
    start_time: Optional[str] = Query(None, description="ISO start time (optional, UTC)"),
    end_time: Optional[str] = Query(None, description="ISO end time (optional, UTC)"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of records to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """
    List thermal history for a given session.

    This returns only metadata (frame id, timestamp, people count). Use
    `/api/realtime/thermal-by-id` to retrieve full details (thermal image and
    density map) for a specific frame.
    """
    return thermal_service.list_frames(
        session_id=session_id,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset,
    )

