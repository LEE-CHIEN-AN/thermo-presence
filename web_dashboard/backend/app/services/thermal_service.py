from typing import Any, Dict, List, Optional

import os
import sys

from datetime import datetime

import numpy as np

# Ensure repository root on path so we can import supabase_integration.*
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.append(REPO_ROOT)

from supabase_integration.supabase_client import SupabaseThermalProcessor  # type: ignore  # noqa: E402


class ThermalService:
    """
    Thin service layer around SupabaseThermalProcessor providing data in a
    JSON-serializable format tailored for the web dashboard.
    """

    def __init__(self, processor: Optional[SupabaseThermalProcessor] = None):
        self._processor = processor or SupabaseThermalProcessor()

    def _serialize_density_map(self, density_map: np.ndarray) -> Dict[str, Any]:
        return {
            "data": density_map.astype(float).flatten().tolist(),
            "shape": list(density_map.shape),
        }

    def _serialize_thermal_image(self, thermal_data: np.ndarray) -> Dict[str, Any]:
        """Serialize thermal image data (12×16 or upsampled 24×32)"""
        return {
            "data": thermal_data.astype(float).flatten().tolist(),
            "shape": list(thermal_data.shape),
        }

    def get_latest_frame(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch latest thermal frame for a session and run people detection.
        Automatically saves results to people_count_results table if not already saved.
        """
        result = self._processor.process_latest_frame(session_id=session_id, limit=1)
        if not result:
            return None

        # Re-run processing to obtain density map and raw thermal data for this frame
        detail = self._processor.process_frame_by_id(result["id"])
        if not detail:
            return None

        density_map = self._processor.frame_processor.get_density_map()

        # Auto-save results to people_count_results table if not already saved
        self._auto_save_result(detail)

        # Get raw thermal frame data from Supabase
        raw_thermal_data = self._get_raw_thermal_data(result["id"])
        thermal_image = None
        if raw_thermal_data is not None:
            # Upsample from 12×16 to 24×32 (same as frame_processor_mlx90641.py)
            import cv2
            frame_2d = raw_thermal_data.reshape(12, 16)
            frame_upsampled = cv2.resize(
                frame_2d,
                (32, 24),  # (width, height) = (cols, rows)
                interpolation=cv2.INTER_CUBIC
            )
            thermal_image = self._serialize_thermal_image(frame_upsampled)

        return {
            "frame_id": result["id"],
            "session_id": result["session_id"],
            "timestamp": self._to_iso(result["timestamp"]),
            "people_count": result["people_count"],
            "people_count_rounded": result["people_count_rounded"],
            "density_map": self._serialize_density_map(density_map) if density_map is not None else None,
            "thermal_image": thermal_image,
        }

    def _get_raw_thermal_data(self, frame_id: int) -> Optional[np.ndarray]:
        """Get raw thermal frame data from Supabase"""
        try:
            response = self._processor.supabase.table('thermal_frames')\
                .select('data')\
                .eq('id', frame_id)\
                .execute()
            
            if not response.data or len(response.data) == 0:
                return None
            
            return self._processor.parse_data_array(response.data[0]['data'])
        except Exception:
            return None

    def get_frame_by_id(self, frame_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetch a specific thermal frame by its id and run people detection.
        Automatically saves results to people_count_results table if not already saved.
        """
        result = self._processor.process_frame_by_id(frame_id)
        if not result:
            return None

        density_map = self._processor.frame_processor.get_density_map()

        # Auto-save results to people_count_results table if not already saved
        self._auto_save_result(result)

        # Get raw thermal frame data
        raw_thermal_data = self._get_raw_thermal_data(frame_id)
        thermal_image = None
        if raw_thermal_data is not None:
            # Upsample from 12×16 to 24×32 (same as frame_processor_mlx90641.py)
            import cv2
            frame_2d = raw_thermal_data.reshape(12, 16)
            frame_upsampled = cv2.resize(
                frame_2d,
                (32, 24),  # (width, height) = (cols, rows)
                interpolation=cv2.INTER_CUBIC
            )
            thermal_image = self._serialize_thermal_image(frame_upsampled)

        return {
            "frame_id": result["id"],
            "session_id": result["session_id"],
            "timestamp": self._to_iso(result["timestamp"]),
            "people_count": result["people_count"],
            "people_count_rounded": result["people_count_rounded"],
            "density_map": self._serialize_density_map(density_map) if density_map is not None else None,
            "thermal_image": thermal_image,
        }

    def list_frames(
        self,
        session_id: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        List thermal frames for a given session, with optional time filtering.
        Uses SupabaseThermalProcessor.process_multiple_frames under the hood.
        Automatically saves results to people_count_results table if not already saved.
        """
        results = self._processor.process_multiple_frames(
            session_id=session_id,
            limit=limit,
            start_time=start_time,
            end_time=end_time,
            offset=offset,
        )
        items: List[Dict[str, Any]] = []
        for r in results:
            # Auto-save result to people_count_results table if not already saved
            self._auto_save_result(r)
            
            items.append(
                {
                    "frame_id": r["id"],
                    "session_id": r["session_id"],
                    "timestamp": self._to_iso(r["timestamp"]),
                    "people_count": r["people_count"],
                    "people_count_rounded": r["people_count_rounded"],
                }
            )
        return items

    def _auto_save_result(self, result: Dict[str, Any]) -> None:
        """
        Automatically save processing result to people_count_results table
        if it doesn't already exist.
        
        Args:
            result: Processing result dictionary from process_frame_by_id
        """
        try:
            frame_id = result["id"]
            
            # Check if result already exists
            existing = self._processor.supabase.table('people_count_results')\
                .select('id')\
                .eq('frame_id', frame_id)\
                .execute()
            
            if existing.data and len(existing.data) > 0:
                # Result already exists, skip saving
                return
            
            # Save result (without density_map to save space)
            self._processor.save_results_to_supabase(
                results=result,
                save_density_map=False  # Don't save density map by default
            )
        except Exception as e:
            # Log error but don't fail the request
            print(f"警告: 自動保存結果到 people_count_results 時發生錯誤: {e}")

    @staticmethod
    def _to_iso(ts: Any) -> str:
        if isinstance(ts, datetime):
            return ts.isoformat()
        return str(ts)



