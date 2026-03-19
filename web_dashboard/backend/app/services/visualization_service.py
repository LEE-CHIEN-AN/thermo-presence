from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import os
import sys

import numpy as np

# Ensure repository root on path so we can import supabase_integration.*
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.append(REPO_ROOT)

from supabase_integration.supabase_client import SupabaseThermalProcessor  # type: ignore  # noqa: E402


class VisualizationService:
    """
    Service responsible for higher-level analytics and statistics.
    Provides people count trends, distributions, and time-based aggregations.
    """

    # Supabase 每次查詢的最大筆數
    SUPABASE_MAX_LIMIT = 1000

    def __init__(self, processor: Optional[SupabaseThermalProcessor] = None):
        self._processor = processor or SupabaseThermalProcessor()

    def _fetch_all_records(
        self,
        session_id: str,
        select_fields: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch all records with pagination to handle Supabase's 1000 record limit.
        
        Args:
            session_id: Session ID to filter
            select_fields: Fields to select (e.g., 'timestamp, people_count, people_count_rounded')
            start_time: Optional start time (ISO format)
            end_time: Optional end time (ISO format)
        
        Returns:
            List of all records
        """
        all_records = []
        offset = 0
        limit = self.SUPABASE_MAX_LIMIT
        
        while True:
            try:
                query = self._processor.supabase.table('people_count_results')\
                    .select(select_fields)\
                    .eq('session_id', session_id)\
                    .order('timestamp', desc=False)
                
                if start_time:
                    query = query.gte('timestamp', start_time)
                if end_time:
                    query = query.lte('timestamp', end_time)
                
                # Use range for pagination
                response = query.range(offset, offset + limit - 1).execute()
                
                if not response.data or len(response.data) == 0:
                    break
                
                all_records.extend(response.data)
                
                # If we got fewer records than the limit, we've reached the end
                if len(response.data) < limit:
                    break
                
                offset += limit
                
            except Exception as e:
                print(f"錯誤: 分頁查詢時發生錯誤 (offset={offset}): {e}")
                break
        
        return all_records

    def _fetch_wiolink_records(
        self,
        select_fields: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        sensor_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch wiolink environmental sensor records with pagination.

        Args:
            select_fields: Fields to select (e.g., 'time, name, celsius_degree, co2eq')
            start_time: Optional start time (ISO format, UTC)
            end_time: Optional end time (ISO format, UTC)
            sensor_name: Optional sensor name filter (e.g., '604_air_quality')

        Returns:
            List of wiolink records
        """
        all_records: List[Dict[str, Any]] = []
        offset = 0
        limit = self.SUPABASE_MAX_LIMIT

        while True:
            try:
                query = (
                    self._processor.supabase.table("wiolink")
                    .select(select_fields)
                    .order("time", desc=False)
                )

                if sensor_name:
                    query = query.eq("name", sensor_name)
                if start_time:
                    query = query.gte("time", start_time)
                if end_time:
                    query = query.lte("time", end_time)

                response = query.range(offset, offset + limit - 1).execute()

                if not response.data or len(response.data) == 0:
                    break

                all_records.extend(response.data)

                if len(response.data) < limit:
                    break

                offset += limit

            except Exception as e:
                print(f"錯誤: wiolink 分頁查詢時發生錯誤 (offset={offset}): {e}")
                break

        return all_records

    def get_people_trend(
        self,
        session_id: str,
        interval: str = "hour",
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get people count trend aggregated by time interval.
        
        Args:
            session_id: Session ID to filter
            interval: Aggregation interval ("hour" or "day")
            start_time: Optional start time (ISO format)
            end_time: Optional end time (ISO format)
        
        Returns:
            Dictionary with trend data points
        """
        try:
            # Fetch all records with pagination
            all_records = self._fetch_all_records(
                session_id=session_id,
                select_fields='timestamp, people_count, people_count_rounded',
                start_time=start_time,
                end_time=end_time,
            )
            
            if not all_records:
                return {
                    "session_id": session_id,
                    "interval": interval,
                    "points": [],
                }
            
            # Group by interval
            points = self._aggregate_by_interval(all_records, interval)
            
            return {
                "session_id": session_id,
                "interval": interval,
                "points": points,
            }
        except Exception as e:
            print(f"錯誤: 獲取人數趨勢時發生錯誤: {e}")
            return {
                "session_id": session_id,
                "interval": interval,
                "points": [],
            }

    def _aggregate_by_interval(self, data: List[Dict[str, Any]], interval: str) -> List[Dict[str, Any]]:
        """Aggregate data points by time interval"""
        from collections import defaultdict
        
        # Group by interval
        groups = defaultdict(list)
        
        for record in data:
            ts_str = record['timestamp']
            try:
                if isinstance(ts_str, str):
                    ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                else:
                    ts = ts_str
                
                # Round to interval
                if interval == "hour":
                    key = ts.replace(minute=0, second=0, microsecond=0)
                elif interval == "day":
                    key = ts.replace(hour=0, minute=0, second=0, microsecond=0)
                else:
                    key = ts
                
                groups[key].append(record['people_count'])
            except Exception:
                continue
        
        # Calculate statistics for each group
        points = []
        for key in sorted(groups.keys()):
            counts = groups[key]
            points.append({
                "time": key.isoformat(),
                "avg_people": float(np.mean(counts)),
                "max_people": float(np.max(counts)),
                "min_people": float(np.min(counts)),
                "count": len(counts),
            })
        
        return points

    def get_people_distribution(
        self,
        session_id: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get distribution of people counts (histogram).
        
        Returns:
            Dictionary with distribution data
        """
        try:
            # Fetch all records with pagination
            all_records = self._fetch_all_records(
                session_id=session_id,
                select_fields='people_count_rounded',
                start_time=start_time,
                end_time=end_time,
            )
            
            if not all_records:
                return {
                    "session_id": session_id,
                    "distribution": {},
                    "total_frames": 0,
                }
            
            # Count occurrences
            from collections import Counter
            counts = [r['people_count_rounded'] for r in all_records]
            distribution = dict(Counter(counts))
            
            return {
                "session_id": session_id,
                "distribution": distribution,
                "total_frames": len(all_records),
            }
        except Exception as e:
            print(f"錯誤: 獲取人數分佈時發生錯誤: {e}")
            return {
                "session_id": session_id,
                "distribution": {},
                "total_frames": 0,
            }

    def get_time_period_stats(
        self,
        session_id: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get statistics for a time period.
        
        Returns:
            Dictionary with summary statistics
        """
        try:
            # Fetch all records with pagination
            all_records = self._fetch_all_records(
                session_id=session_id,
                select_fields='people_count, people_count_rounded, timestamp',
                start_time=start_time,
                end_time=end_time,
            )
            
            if not all_records:
                return {
                    "session_id": session_id,
                    "total_frames": 0,
                    "avg_people": 0.0,
                    "max_people": 0,
                    "min_people": 0,
                    "median_people": 0.0,
                    "std_people": 0.0,
                }
            
            counts = [r['people_count'] for r in all_records]
            rounded_counts = [r['people_count_rounded'] for r in all_records]
            
            return {
                "session_id": session_id,
                "total_frames": len(all_records),
                "avg_people": float(np.mean(counts)),
                "max_people": int(np.max(rounded_counts)),
                "min_people": int(np.min(rounded_counts)),
                "median_people": float(np.median(counts)),
                "std_people": float(np.std(counts)),
            }
        except Exception as e:
            print(f"錯誤: 獲取時間段統計時發生錯誤: {e}")
            return {
                "session_id": session_id,
                "total_frames": 0,
                "avg_people": 0.0,
                "max_people": 0,
                "min_people": 0,
                "median_people": 0.0,
                "std_people": 0.0,
            }

    def get_people_env_timeseries(
        self,
        session_id: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        sensor_name: Optional[str] = None,
        max_delta_minutes: int = 5,
    ) -> Dict[str, Any]:
        """
        Get people count timeseries aligned with environmental sensor (wiolink) data.

        Each people_count_results record is matched with the nearest wiolink record
        (within max_delta_minutes). If no wiolink record is found within the window,
        env fields will be None.
        """
        try:
            # 1) Fetch all people count records in the range
            people_records = self._fetch_all_records(
                session_id=session_id,
                select_fields="timestamp, people_count",
                start_time=start_time,
                end_time=end_time,
            )

            if not people_records:
                return {
                    "session_id": session_id,
                    "sensor_name": sensor_name,
                    "max_delta_minutes": max_delta_minutes,
                    "points": [],
                }

            # 2) Fetch wiolink records in the same time range
            wiolink_records = self._fetch_wiolink_records(
                select_fields=(
                    "time, name, humidity, light_intensity, celsius_degree, "
                    "mag_approach, dust, total_voc, co2eq, "
                    "pm1_0_atm, pm2_5_atm, pm10_atm, touch_add, touch_minus"
                ),
                start_time=start_time,
                end_time=end_time,
                sensor_name=sensor_name,
            )

            # Helper to parse timestamps consistently (UTC-aware)
            def _parse_ts(value: Any) -> Optional[datetime]:
                try:
                    if isinstance(value, str):
                        # Support both '...Z' and '+00:00' styles
                        return datetime.fromisoformat(value.replace("Z", "+00:00"))
                    return value
                except Exception:
                    return None

            # Convert and sort people timestamps
            people_with_ts = []
            for r in people_records:
                ts = _parse_ts(r.get("timestamp"))
                if ts is not None:
                    people_with_ts.append((ts, r))

            people_with_ts.sort(key=lambda x: x[0])

            # Convert and sort wiolink timestamps
            wiolink_with_ts = []
            for r in wiolink_records:
                ts = _parse_ts(r.get("time"))
                if ts is not None:
                    wiolink_with_ts.append((ts, r))

            wiolink_with_ts.sort(key=lambda x: x[0])

            max_delta = timedelta(minutes=max_delta_minutes)

            # If there is no wiolink data, still return people series with env=None
            if not wiolink_with_ts:
                points = []
                for ts, p in people_with_ts:
                    points.append(
                        {
                            "time": ts.isoformat(),
                            "people_count": float(p.get("people_count", 0.0)),
                            "sensor_name": None,
                            "humidity": None,
                            "light_intensity": None,
                            "celsius_degree": None,
                            "mag_approach": None,
                            "dust": None,
                            "total_voc": None,
                            "co2eq": None,
                            "pm1_0_atm": None,
                            "pm2_5_atm": None,
                            "pm10_atm": None,
                            "touch_add": None,
                            "touch_minus": None,
                        }
                    )

                return {
                    "session_id": session_id,
                    "sensor_name": sensor_name,
                    "max_delta_minutes": max_delta_minutes,
                    "points": points,
                }

            # 3) Two-pointer scan to find nearest wiolink record for each people record
            points: List[Dict[str, Any]] = []
            w_idx = 0

            for ts, p in people_with_ts:
                # Move wiolink pointer to the closest timestamp
                while w_idx + 1 < len(wiolink_with_ts):
                    curr_dt, _ = wiolink_with_ts[w_idx]
                    next_dt, _ = wiolink_with_ts[w_idx + 1]
                    if abs(next_dt - ts) <= abs(curr_dt - ts):
                        w_idx += 1
                    else:
                        break

                w_dt, w_rec = wiolink_with_ts[w_idx]
                delta = abs(w_dt - ts)

                if delta <= max_delta:
                    # Use this wiolink record
                    point = {
                        "time": ts.isoformat(),
                        "people_count": float(p.get("people_count", 0.0)),
                        "sensor_name": w_rec.get("name"),
                        "humidity": w_rec.get("humidity"),
                        "light_intensity": w_rec.get("light_intensity"),
                        "celsius_degree": w_rec.get("celsius_degree"),
                        "mag_approach": w_rec.get("mag_approach"),
                        "dust": w_rec.get("dust"),
                        "total_voc": w_rec.get("total_voc"),
                        "co2eq": w_rec.get("co2eq"),
                        "pm1_0_atm": w_rec.get("pm1_0_atm"),
                        "pm2_5_atm": w_rec.get("pm2_5_atm"),
                        "pm10_atm": w_rec.get("pm10_atm"),
                        "touch_add": w_rec.get("touch_add"),
                        "touch_minus": w_rec.get("touch_minus"),
                        "wiolink_time": w_dt.isoformat(),
                        "time_delta_seconds": delta.total_seconds(),
                    }
                else:
                    # No wiolink record within threshold
                    point = {
                        "time": ts.isoformat(),
                        "people_count": float(p.get("people_count", 0.0)),
                        "sensor_name": None,
                        "humidity": None,
                        "light_intensity": None,
                        "celsius_degree": None,
                        "mag_approach": None,
                        "dust": None,
                        "total_voc": None,
                        "co2eq": None,
                        "pm1_0_atm": None,
                        "pm2_5_atm": None,
                        "pm10_atm": None,
                        "touch_add": None,
                        "touch_minus": None,
                        "wiolink_time": None,
                        "time_delta_seconds": None,
                    }

                points.append(point)

            return {
                "session_id": session_id,
                "sensor_name": sensor_name,
                "max_delta_minutes": max_delta_minutes,
                "points": points,
            }
        except Exception as e:
            print(f"錯誤: 獲取人數與環境感測器時序資料時發生錯誤: {e}")
            return {
                "session_id": session_id,
                "sensor_name": sensor_name,
                "max_delta_minutes": max_delta_minutes,
                "points": [],
            }



