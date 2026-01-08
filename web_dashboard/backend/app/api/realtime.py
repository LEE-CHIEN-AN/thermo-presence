from fastapi import APIRouter, Query, HTTPException

from app.services.thermal_service import ThermalService


router = APIRouter()
thermal_service = ThermalService()


@router.get("/thermal-latest")
def get_latest_thermal(session_id: str = Query(..., description="Session ID, e.g. '604_windowside'")):
    """
    Return latest thermal frame, density map and people count for a session.
    """
    result = thermal_service.get_latest_frame(session_id)
    if result is None:
        raise HTTPException(status_code=404, detail="No thermal frame found for the given session_id")
    return result


@router.get("/thermal-by-id")
def get_thermal_by_id(frame_id: int = Query(..., description="thermal_frames.id")):
    """
    Return thermal frame, density map and people count by frame id.
    """
    result = thermal_service.get_frame_by_id(frame_id)
    if result is None:
        raise HTTPException(status_code=404, detail="No thermal frame found for the given frame_id")
    return result



