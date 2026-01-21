from typing import Any, Dict, List, Optional

import os
import sys

from datetime import datetime

import numpy as np

# Ensure repository root on path so we can import supabase_integration.*
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# thermal_service.py is at: web_dashboard/backend/app/services/thermal_service.py
# Go up 4 levels to reach repo root: services -> app -> backend -> web_dashboard -> repo_root
REPO_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.append(REPO_ROOT)

from supabase_integration.supabase_client import SupabaseThermalProcessor  # type: ignore  # noqa: E402

# YOLO imports (lazy loading to avoid import errors if YOLO is not available)
_yolo_model = None
_yolo_available = None


class ThermalService:
    """
    Thin service layer around SupabaseThermalProcessor providing data in a
    JSON-serializable format tailored for the web dashboard.
    """

    def __init__(self, processor: Optional[SupabaseThermalProcessor] = None):
        self._processor = processor or SupabaseThermalProcessor()
        self._yolo_model = None
        self._yolo_available = None

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

    def _load_yolo_model(self) -> Optional[Any]:
        """Lazy load YOLO model if available"""
        global _yolo_model, _yolo_available
        
        if _yolo_available is False:
            return None
        
        if _yolo_model is not None:
            return _yolo_model
        
        try:
            from ultralytics import YOLO
            from pathlib import Path
            
            # Convert REPO_ROOT to Path object if it's a string
            repo_root_path = Path(REPO_ROOT) if isinstance(REPO_ROOT, str) else REPO_ROOT
            
            # Try to find YOLO weights
            weights_paths = [
                repo_root_path / "yolo_training" / "runs" / "train" / "weights" / "best.pt",
                repo_root_path / "yolo_training" / "runs" / "train" / "weights" / "last.pt",
            ]
            
            weights_path = None
            for path in weights_paths:
                if path.exists():
                    weights_path = str(path)
                    print(f"找到 YOLO 權重檔案: {weights_path}")
                    break
            
            if weights_path is None:
                print(f"警告: 找不到 YOLO 權重檔案。搜尋路徑:")
                for p in weights_paths:
                    print(f"  - {p} (存在: {p.exists()})")
                _yolo_available = False
                return None
            
            _yolo_model = YOLO(weights_path)
            print(f"✓ YOLO 模型載入成功: {weights_path}")
            _yolo_available = True
            return _yolo_model
        except ImportError:
            _yolo_available = False
            return None
        except Exception as e:
            print(f"警告: 載入 YOLO 模型時發生錯誤: {e}")
            _yolo_available = False
            return None

    def _run_yolo_detection(self, thermal_24x32: np.ndarray) -> Optional[Dict[str, Any]]:
        """Run YOLO detection on thermal image"""
        model = self._load_yolo_model()
        if model is None:
            return None
        
        try:
            import cv2
            from yolo_training.preprocess import thermal_to_rgb, ORIGINAL_HEIGHT, ORIGINAL_WIDTH
            
            if thermal_24x32.shape != (ORIGINAL_HEIGHT, ORIGINAL_WIDTH):
                return None
            
            # Convert to RGB image (same as training)
            bgr_image = thermal_to_rgb(
                thermal_24x32,
                use_colormap=True,
                colormap=cv2.COLORMAP_JET,
            )
            yolo_input = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2RGB)
            
            # Run YOLO inference
            results = model.predict(
                source=yolo_input,
                imgsz=ORIGINAL_HEIGHT * 8,  # 192
                conf=0.25,
                iou=0.7,
                max_det=300,
                verbose=False,
            )
            
            if not results:
                return {
                    "people_count": 0,
                    "boxes": [],
                }
            
            r0 = results[0]
            boxes = r0.boxes
            
            if boxes is None or len(boxes) == 0:
                return {
                    "people_count": 0,
                    "boxes": [],
                }
            
            # Extract bounding boxes (normalized coordinates: x_center, y_center, width, height)
            box_list = []
            for box in boxes:
                xywhn = box.xywhn[0].cpu().numpy()  # normalized coordinates
                conf = float(box.conf[0].cpu().numpy())
                box_list.append({
                    "x_center": float(xywhn[0]),
                    "y_center": float(xywhn[1]),
                    "width": float(xywhn[2]),
                    "height": float(xywhn[3]),
                    "confidence": conf,
                })
            
            return {
                "people_count": len(box_list),
                "boxes": box_list,
            }
        except Exception as e:
            print(f"警告: YOLO 偵測時發生錯誤: {e}")
            return None

    def get_latest_frame(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch latest thermal frame for a session and run people detection.
        Automatically saves results to people_count_results table if not already saved.
        """
        try:
            result = self._processor.process_latest_frame(session_id=session_id, limit=1)
            if not result:
                return None

            # Re-run processing to obtain density map and raw thermal data for this frame
            try:
                detail = self._processor.process_frame_by_id(result["id"])
            except RuntimeError as e:
                # Supabase 連接錯誤，記錄但繼續使用已獲取的結果
                print(f"警告: 無法重新處理 frame {result['id']}，使用已獲取的結果: {e}")
                detail = result  # 使用已獲取的結果
            
            if not detail:
                return None
        except RuntimeError as e:
            # Supabase 連接錯誤
            print(f"錯誤: 無法從 Supabase 獲取資料: {e}")
            return None
        except Exception as e:
            # 其他未預期的錯誤
            print(f"錯誤: 處理熱影像資料時發生未預期的錯誤: {e}")
            import traceback
            traceback.print_exc()
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

        # Run YOLO detection if available
        yolo_result = None
        yolo_thermal_image = None  # Upsampled thermal image for YOLO visualization
        if thermal_image is not None:
            thermal_array = np.array(thermal_image["data"]).reshape(thermal_image["shape"])
            yolo_result = self._run_yolo_detection(thermal_array)
            
            # Create upsampled thermal image for YOLO visualization (192×256)
            # This matches the resolution YOLO actually detects on
            if yolo_result is not None:
                import cv2
                from yolo_training.preprocess import TARGET_HEIGHT, TARGET_WIDTH
                thermal_upsampled = cv2.resize(
                    thermal_array,
                    (TARGET_WIDTH, TARGET_HEIGHT),  # (width, height) = (256, 192)
                    interpolation=cv2.INTER_CUBIC
                )
                yolo_thermal_image = self._serialize_thermal_image(thermal_upsampled)

        return {
            "frame_id": result["id"],
            "session_id": result["session_id"],
            "timestamp": self._to_iso(result["timestamp"]),
            "people_count": result["people_count"],
            "people_count_rounded": result["people_count_rounded"],
            "density_map": self._serialize_density_map(density_map) if density_map is not None else None,
            "thermal_image": thermal_image,
            "yolo_detection": yolo_result,
            "yolo_thermal_image": yolo_thermal_image,  # Upsampled 192×256 thermal image
        }

    def _get_raw_thermal_data(self, frame_id: int) -> Optional[np.ndarray]:
        """Get raw thermal frame data from Supabase with retry mechanism"""
        import time
        import httpx
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self._processor.supabase.table('thermal_frames')\
                    .select('data')\
                    .eq('id', frame_id)\
                    .execute()
                
                if not response.data or len(response.data) == 0:
                    return None
                
                return self._processor.parse_data_array(response.data[0]['data'])
            except (httpx.ReadError, httpx.RemoteProtocolError, httpx.ConnectError, httpx.TimeoutException) as e:
                if attempt < max_retries - 1:
                    time.sleep(1.0 * (attempt + 1))  # 指數退避
                    continue
                else:
                    print(f"警告: 無法獲取 raw thermal data (frame_id={frame_id})，已重試 {max_retries} 次: {e}")
                    return None
            except Exception as e:
                print(f"警告: 獲取 raw thermal data 時發生錯誤: {e}")
                return None
        return None

    def get_frame_by_id(self, frame_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetch a specific thermal frame by its id and run people detection.
        Automatically saves results to people_count_results table if not already saved.
        """
        try:
            result = self._processor.process_frame_by_id(frame_id)
            if not result:
                return None
        except RuntimeError as e:
            # Supabase 連接錯誤
            print(f"錯誤: 無法從 Supabase 獲取 frame {frame_id}: {e}")
            return None
        except Exception as e:
            # 其他未預期的錯誤
            print(f"錯誤: 處理熱影像資料時發生未預期的錯誤: {e}")
            import traceback
            traceback.print_exc()
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

        # Run YOLO detection if available
        yolo_result = None
        yolo_thermal_image = None  # Upsampled thermal image for YOLO visualization
        if thermal_image is not None:
            thermal_array = np.array(thermal_image["data"]).reshape(thermal_image["shape"])
            yolo_result = self._run_yolo_detection(thermal_array)
            
            # Create upsampled thermal image for YOLO visualization (192×256)
            # This matches the resolution YOLO actually detects on
            if yolo_result is not None:
                import cv2
                from yolo_training.preprocess import TARGET_HEIGHT, TARGET_WIDTH
                thermal_upsampled = cv2.resize(
                    thermal_array,
                    (TARGET_WIDTH, TARGET_HEIGHT),  # (width, height) = (256, 192)
                    interpolation=cv2.INTER_CUBIC
                )
                yolo_thermal_image = self._serialize_thermal_image(thermal_upsampled)

        return {
            "frame_id": result["id"],
            "session_id": result["session_id"],
            "timestamp": self._to_iso(result["timestamp"]),
            "people_count": result["people_count"],
            "people_count_rounded": result["people_count_rounded"],
            "density_map": self._serialize_density_map(density_map) if density_map is not None else None,
            "thermal_image": thermal_image,
            "yolo_detection": yolo_result,
            "yolo_thermal_image": yolo_thermal_image,  # Upsampled 192×256 thermal image
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



