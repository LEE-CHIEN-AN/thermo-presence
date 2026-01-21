"""
資料前處理工具：將熱影像和點座標轉換為 YOLO 訓練格式
"""

import numpy as np
import cv2
from typing import List, Tuple, Optional
import json


# 溫度正規化參數
TEMPERATURE_NORMALIZATION_MIN = 20.0
TEMPERATURE_NORMALIZATION_MAX = 35.0

# 原始和目標解析度
ORIGINAL_HEIGHT = 24
ORIGINAL_WIDTH = 32
TARGET_HEIGHT = 192
TARGET_WIDTH = 256

# Bounding box 大小（在原始 24×32 解析度下）
BOX_WIDTH = 6  # 像素
BOX_HEIGHT = 6  # 像素


def normalize_thermal(thermal_data: np.ndarray) -> np.ndarray:
    """
    溫度正規化：20-35°C → 0-255
    
    Args:
        thermal_data: 熱影像資料（numpy array）
    
    Returns:
        正規化後的影像（0-255 範圍）
    """
    normalized = (thermal_data - TEMPERATURE_NORMALIZATION_MIN) / (
        TEMPERATURE_NORMALIZATION_MAX - TEMPERATURE_NORMALIZATION_MIN
    )
    normalized = np.clip(normalized, 0.0, 1.0)
    return (normalized * 255).astype(np.uint8)


def thermal_to_rgb(
    thermal_data: np.ndarray,
    use_colormap: bool = False,
    colormap: int = cv2.COLORMAP_JET
) -> np.ndarray:
    """
    將 24×32 熱影像轉換為 192×256 RGB
    
    Args:
        thermal_data: 24×32 熱影像（numpy array）
        use_colormap: 是否使用 colormap（預設 False，直接複製 3 個 channel）
        colormap: OpenCV colormap（預設 JET）
    
    Returns:
        192×256 RGB 影像（numpy array, uint8）
    """
    # 1. 正規化溫度
    normalized = normalize_thermal(thermal_data)
    
    # 2. 上採樣：24×32 → 192×256
    upsampled = cv2.resize(
        normalized,
        (TARGET_WIDTH, TARGET_HEIGHT),  # (width, height)
        interpolation=cv2.INTER_CUBIC
    )
    
    # 3. Grayscale → RGB
    if use_colormap:
        rgb = cv2.applyColorMap(upsampled, colormap)
    else:
        # 複製 3 個 channel
        rgb = cv2.cvtColor(upsampled, cv2.COLOR_GRAY2RGB)
    
    return rgb


def detect_thermal_blob_size(
    thermal_image: np.ndarray,
    center_x: float,
    center_y: float,
    threshold_ratio: float = 0.7,
    max_size: Tuple[int, int] = (10, 10),
    min_size: Tuple[int, int] = (3, 3),
    margin: int = 1
) -> Tuple[float, float]:
    """
    根據熱源區域自動檢測 bounding box 大小
    每個熱點會根據其實際熱源區域大小得到不同的 bounding box
    
    Args:
        thermal_image: 24×32 熱影像（原始解析度）
        center_x, center_y: 中心點座標（原始解析度，像素座標）
        threshold_ratio: 溫度閾值比例（相對於中心點溫度，預設 0.7 = 70%）
        max_size: 最大 bounding box 大小 (width, height)，預設 (10, 10)
        min_size: 最小 bounding box 大小 (width, height)，預設 (3, 3)
        margin: 邊距（像素），預設 1
    
    Returns:
        (box_width, box_height) 像素大小（在原始 24×32 解析度下）
    """
    h, w = thermal_image.shape
    cx, cy = int(round(center_x)), int(round(center_y))
    
    # 確保座標在範圍內
    if not (0 <= cx < w and 0 <= cy < h):
        return float(min_size[0]), float(min_size[1])  # 回退到最小大小
    
    # 獲取中心點溫度
    center_temp = thermal_image[cy, cx]
    
    # 如果中心點溫度太低，使用固定大小
    if center_temp < 25.0:  # 低於 25°C 可能是背景
        return float(min_size[0]), float(min_size[1])
    
    # 計算閾值（低於此溫度的像素不屬於該熱源）
    # 使用相對閾值，確保每個熱點根據其自身溫度計算
    threshold = center_temp * threshold_ratio
    
    # 從中心點向外擴展，找到熱源邊界
    # 使用區域生長（Region Growing）方法
    visited = np.zeros((h, w), dtype=bool)
    queue = [(cx, cy)]
    visited[cy, cx] = True
    
    min_x, max_x = cx, cx
    min_y, max_y = cy, cy
    
    # 4 連通區域生長（上下左右）
    directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
    
    # 限制搜尋範圍，避免過度擴展
    max_search_radius = max(max_size[0], max_size[1]) + 2
    
    while queue:
        x, y = queue.pop(0)
        
        # 檢查是否超出搜尋半徑
        if abs(x - cx) > max_search_radius or abs(y - cy) > max_search_radius:
            continue
        
        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            
            if 0 <= nx < w and 0 <= ny < h and not visited[ny, nx]:
                pixel_temp = thermal_image[ny, nx]
                
                # 檢查是否屬於同一熱源（溫度 >= 閾值）
                if pixel_temp >= threshold:
                    visited[ny, nx] = True
                    queue.append((nx, ny))
                    
                    # 更新邊界
                    min_x = min(min_x, nx)
                    max_x = max(max_x, nx)
                    min_y = min(min_y, ny)
                    max_y = max(max_y, ny)
    
    # 計算實際檢測到的區域大小
    detected_width = max_x - min_x + 1
    detected_height = max_y - min_y + 1
    
    # 加上邊距
    box_width = detected_width + 2 * margin
    box_height = detected_height + 2 * margin
    
    # 限制在最小和最大範圍內
    box_width = max(min_size[0], min(max_size[0], box_width))
    box_height = max(min_size[1], min(max_size[1], box_height))
    
    return float(box_width), float(box_height)


def points_to_yolo_boxes(
    points: List[Tuple[float, float]],
    thermal_image: np.ndarray = None,
    image_width: int = ORIGINAL_WIDTH,
    image_height: int = ORIGINAL_HEIGHT,
    box_width: float = None,
    box_height: float = None,
    use_adaptive_size: bool = True
) -> List[Tuple[float, float, float, float]]:
    """
    將點座標轉換為 YOLO 格式的 bounding boxes
    支援固定大小或自適應大小（根據熱源區域）
    自動裁剪超出影像範圍的部分
    
    Args:
        points: 中心點座標列表 [(x1, y1), (x2, y2), ...]
        thermal_image: 24×32 熱影像（用於自適應大小檢測，可選）
        image_width: 影像寬度（預設 32）
        image_height: 影像高度（預設 24）
        box_width: bounding box 寬度（像素，預設 6，如果為 None 且 use_adaptive_size=True 則自動檢測）
        box_height: bounding box 高度（像素，預設 6，如果為 None 且 use_adaptive_size=True 則自動檢測）
        use_adaptive_size: 是否使用自適應大小（根據熱源區域自動調整）
    
    Returns:
        YOLO 格式的 bounding boxes 列表 [(x_center, y_center, width, height), ...]
        座標已 normalized [0, 1]，且保證 bounding box 完全在影像範圍內
    """
    boxes = []
    
    # 如果沒有提供固定大小，使用預設值
    if box_width is None:
        box_width = BOX_WIDTH
    if box_height is None:
        box_height = BOX_HEIGHT
    
    for x, y in points:
        # 如果使用自適應大小且有熱影像，自動檢測 bounding box 大小
        # 注意：每個熱點會根據其實際熱源區域大小得到不同的 bounding box
        if use_adaptive_size and thermal_image is not None:
            try:
                # 對每個點獨立檢測其熱源區域大小
                # 這確保了同一張圖中不同大小的熱點會有不同大小的 bounding box
                detected_width, detected_height = detect_thermal_blob_size(
                    thermal_image, x, y
                )
                # 使用檢測到的大小，但確保不小於最小值
                current_box_width = max(3.0, detected_width)
                current_box_height = max(3.0, detected_height)
            except Exception as e:
                # 如果檢測失敗，使用預設大小
                current_box_width = box_width
                current_box_height = box_height
        else:
            # 使用固定大小
            current_box_width = box_width
            current_box_height = box_height
        
        # 計算 normalized 座標
        x_center_norm = x / image_width
        y_center_norm = y / image_height
        width_norm = current_box_width / image_width
        height_norm = current_box_height / image_height
        
        # 計算 bounding box 邊界
        x_min = x_center_norm - width_norm / 2
        x_max = x_center_norm + width_norm / 2
        y_min = y_center_norm - height_norm / 2
        y_max = y_center_norm + height_norm / 2
        
        # 裁剪到 [0, 1] 範圍內
        x_min_clipped = max(0.0, x_min)
        x_max_clipped = min(1.0, x_max)
        y_min_clipped = max(0.0, y_min)
        y_max_clipped = min(1.0, y_max)
        
        # 重新計算中心點和寬高（裁剪後）
        x_center_clipped = (x_min_clipped + x_max_clipped) / 2
        y_center_clipped = (y_min_clipped + y_max_clipped) / 2
        width_clipped = x_max_clipped - x_min_clipped
        height_clipped = y_max_clipped - y_min_clipped
        
        # 確保寬高不為 0（如果點完全在影像外，跳過）
        if width_clipped <= 0 or height_clipped <= 0:
            continue
        
        boxes.append((x_center_clipped, y_center_clipped, width_clipped, height_clipped))
    
    return boxes


def resize_coordinates(
    x: float,
    y: float,
    width: float,
    height: float,
    src_width: int = ORIGINAL_WIDTH,
    src_height: int = ORIGINAL_HEIGHT,
    dst_width: int = TARGET_WIDTH,
    dst_height: int = TARGET_HEIGHT
) -> Tuple[float, float, float, float]:
    """
    將座標從原始解析度轉換為目標解析度的 normalized 座標
    
    Args:
        x, y, width, height: 原始解析度的 normalized 座標 [0, 1]
        src_width, src_height: 原始解析度
        dst_width, dst_height: 目標解析度
    
    Returns:
        目標解析度的 normalized 座標 (x_center, y_center, width, height)
    """
    # 座標在 normalized 空間中保持不變（因為都是相對於影像尺寸的比例）
    # 所以直接返回即可
    return (x, y, width, height)


def load_hdf5_dataset(hdf5_path: str) -> Tuple[np.ndarray, List[Tuple[float, float]]]:
    """
    從 HDF5 檔案讀取資料
    
    Args:
        hdf5_path: HDF5 檔案路徑
    
    Returns:
        (thermal_image, points_list)
        - thermal_image: 24×32 熱影像（numpy array）
        - points_list: 點座標列表 [(x1, y1), (x2, y2), ...]
    """
    import pandas as pd
    
    df = pd.read_hdf(hdf5_path)
    
    # 假設資料結構：每行包含 'data' 和 'points' 欄位
    # 這裡需要根據實際 HDF5 結構調整
    # 先讀取第一筆資料作為範例
    if len(df) > 0:
        first_row = df.iloc[0]
        thermal_image = np.array(first_row['data'])
        points = np.array(first_row['points'])
        
        # 轉換 points 為列表格式
        if points.ndim == 2:
            points_list = [(p[0], p[1]) for p in points]
        else:
            points_list = []
        
        return thermal_image, points_list
    
    return None, []


def apply_colormap(image: np.ndarray, colormap: int = cv2.COLORMAP_JET) -> np.ndarray:
    """
    對 grayscale 影像應用 colormap
    
    Args:
        image: Grayscale 影像（numpy array）
        colormap: OpenCV colormap（預設 JET）
    
    Returns:
        RGB 影像
    """
    return cv2.applyColorMap(image, colormap)
