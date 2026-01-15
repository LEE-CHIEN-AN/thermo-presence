from typing import Any, Dict, List, Optional

import os
from datetime import datetime, timedelta, timezone

from supabase import create_client, Client  # type: ignore
from dotenv import load_dotenv


load_dotenv()


class EnvironmentService:
    """
    Service for reading environmental sensor data from the `wiolink` table.

    This is used for environment dashboards such as CO2/VOC trends and
    spatial heatmaps for temperature/humidity/PMV/PPD.
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
        Return latest rows from wiolink table (optionally filtered by sensor_name).
        """
        query = self.supabase.table("wiolink").select("*")
        if sensor_name:
            query = query.eq("name", sensor_name)
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
        # Currently just returns latest per sensor; can be refined later.
        latest = self.get_latest()
        return {"timestamp": timestamp, "sensors": latest}

    def get_air_quality_trend(self, days: int = 10) -> List[Dict[str, Any]]:
        """
        Return CO2 and VOC timeseries for the 604_air_quality sensor over the last N days.

        This mirrors the original Streamlit implementation:
        - Uses UTC time range [now - days, now]
        - Filters by name == '604_air_quality'
        - Returns sorted ascending by time
        """
        now_utc = datetime.now(timezone.utc)
        start_utc = now_utc - timedelta(days=days)

        start_iso = start_utc.isoformat()
        end_iso = now_utc.isoformat()

        response = (
            self.supabase.table("wiolink")
            .select("time, name, co2eq, total_voc")
            .eq("name", "604_air_quality")
            .gte("time", start_iso)
            .lte("time", end_iso)
            .order("time", desc=False)
            .execute()
        )

        return response.data or []

    def get_pm_trend(self, days: int = 10) -> List[Dict[str, Any]]:
        """
        Return PM1.0, PM2.5, PM10 timeseries for the 604_window sensor over the last N days.

        The 604_window sensor provides particulate matter readings.
        """
        now_utc = datetime.now(timezone.utc)
        start_utc = now_utc - timedelta(days=days)

        start_iso = start_utc.isoformat()
        end_iso = now_utc.isoformat()

        response = (
            self.supabase.table("wiolink")
            .select("time, name, pm1_0_atm, pm2_5_atm, pm10_atm")
            .eq("name", "604_window")
            .gte("time", start_iso)
            .lte("time", end_iso)
            .order("time", desc=False)
            .execute()
        )

        return response.data or []

    def get_temp_humidity_trend(self, days: int = 10, sensor_name: str = "604_center") -> List[Dict[str, Any]]:
        """
        Return temperature and humidity timeseries for a specified sensor over the last N days.

        Default sensor is 604_center which has both temperature and humidity readings.
        """
        now_utc = datetime.now(timezone.utc)
        start_utc = now_utc - timedelta(days=days)

        start_iso = start_utc.isoformat()
        end_iso = now_utc.isoformat()

        response = (
            self.supabase.table("wiolink")
            .select("time, name, celsius_degree, humidity")
            .eq("name", sensor_name)
            .gte("time", start_iso)
            .lte("time", end_iso)
            .order("time", desc=False)
            .execute()
        )

        return response.data or []
