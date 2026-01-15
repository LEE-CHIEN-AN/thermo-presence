from fastapi import APIRouter, Query

from app.services.integrated_service import IntegratedService


router = APIRouter()
integrated_service = IntegratedService()


@router.get("/latest-full")
def latest_full(session_id: str = Query(..., description="Session ID, e.g. '604_windowside'")):
    """
    Return latest integrated data (thermal + environment) for a session.
    """
    return integrated_service.get_latest_full(session_id=session_id)


@router.get("/synchronized")
def synchronized(
    timestamp: str = Query(..., description="ISO timestamp"),
    time_window: int = Query(30, ge=1, le=600, description="Time window in seconds"),
):
    """
    Return synchronized data around a given timestamp.
    """
    return integrated_service.get_synchronized(timestamp=timestamp, time_window_seconds=time_window)




