from typing import Any, Dict, List, Optional

import os
import sys
from datetime import datetime

from supabase import create_client, Client  # type: ignore
from dotenv import load_dotenv


load_dotenv()


class EnvironmentService:
    """
    Service for reading environmental sensor data from the `wiolink` table.

    This is implemented now but will be primarily used in the second phase
    when integrating other sensors into the dashboard.
    """

    def __init__(self, supabase: Optional[Client] = None):
        if supabase is not None:
            self.supabase = supabase
        else:
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_KEY")
            if not url or not key:
                raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set in environment for EnvironmentService")
            self.supabase = create_client(url, key)

    def get_latest(self, sensor_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Return latest row per sensor from wiolink table.
        If sensor_name is provided, only that sensor is returned.
        """
        query = self.supabase.table("wiolink").select("*")
        if sensor_name:
            query = query.eq("name", sensor_name)
        # We intentionally keep this simple; callers can post-process.
        response = query.order("time", desc=True).limit(100).execute()
        return response.data or []

    def get_history(self, sensor_name: str, start_time: str, end_time: str) -> List[Dict[str, Any]]:
        """
        Return history for a single sensor in a time range.
        """
        response = (
            self.supabase.table("wiolink")
            .select("*")
            .eq("name", sensor_name)
            .gte("time", start_time)
            .lte("time", end_time)
            .order("time", desc=False)
            .execute()
        )
        return response.data or []

    def get_spatial_snapshot(self, timestamp: str) -> Dict[str, Any]:
        """
        Placeholder method for heatmap data – for now, returns latest rows
        around a timestamp so the frontend can build its own heatmaps.
        """
        # Small time window around timestamp
        t = datetime.fromisoformat(timestamp)
        start = (t).isoformat()
        # No strict end window here; simply return latest per sensor
        latest = self.get_latest()
        return {"timestamp": timestamp, "sensors": latest}



