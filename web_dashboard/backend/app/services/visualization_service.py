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



