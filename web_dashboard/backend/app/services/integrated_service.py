from typing import Any, Dict, Optional

from datetime import datetime, timedelta

from .thermal_service import ThermalService
from .environment_service import EnvironmentService


class IntegratedService:
    """
    Service that combines thermal and environmental data in a single response.

    This is a thin orchestration layer that calls ThermalService and
    EnvironmentService.
    """

    def __init__(
        self,
        thermal_service: Optional[ThermalService] = None,
        environment_service: Optional[EnvironmentService] = None,
    ):
        self.thermal_service = thermal_service or ThermalService()
        self.environment_service = environment_service or EnvironmentService()

    def get_latest_full(self, session_id: str) -> Dict[str, Any]:
        thermal = self.thermal_service.get_latest_frame(session_id=session_id)
        if not thermal:
            return {"thermal": None, "environment": []}

        timestamp = thermal["timestamp"]
        env = self._get_environment_near_time(timestamp)
        return {"thermal": thermal, "environment": env}

    def get_synchronized(self, timestamp: str, time_window_seconds: int = 30) -> Dict[str, Any]:
        """
        Return thermal and environment data around the given timestamp.
        For now, thermal part is not strictly time-filtered – it can be
        extended later if needed.
        """
        env = self._get_environment_near_time(timestamp, time_window_seconds)
        return {"timestamp": timestamp, "environment": env}

    def _get_environment_near_time(self, timestamp: str, time_window_seconds: int = 30):
        t = datetime.fromisoformat(timestamp)
        start = (t - timedelta(seconds=time_window_seconds)).isoformat()
        end = (t + timedelta(seconds=time_window_seconds)).isoformat()
        # We query all sensors in range and let the caller decide how to use them
        # In this phase we keep it simple and just return latest rows.
        # A more advanced implementation could group by sensor.
        return self.environment_service.get_history(sensor_name="604_air_quality", start_time=start, end_time=end)




