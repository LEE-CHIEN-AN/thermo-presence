"""
資料匯出腳本：從 HDF5 檔案讀取資料，轉換為 YOLO 格式
"""

import os
import sys
import json
import numpy as np
import pandas as pd
import cv2
from pathlib import Path
from typing import Dict, List, Tuple
from PIL import Image

# 添加當前目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from preprocess import (
    thermal_to_rgb,
    points_to_yolo_boxes,
    ORIGINAL_HEIGHT,
    ORIGINAL_WIDTH,
    TARGET_HEIGHT,
    TARGET_WIDTH
)

# 資料分割定義（從 dataset/README.md）
TRAINING_DIRS = [
    "006__11_44_59", "007__11_48_59", "008__11_52_59",
    "009__11_57_00", "000__14_15_19", "001__14_19_19",
    "002__14_23_19", "003__14_27_20", "004__14_31_20",
    "012__15_03_21", "013__15_07_21", "014__15_11_21",
    "015__15_15_21", "016__15_19_21", "011__13_38_20",
    "012__13_42_20", "013__13_46_21", "007__13_22_20"
]

VALIDATION_DIRS = [
    "004__13_10_20", "014__13_50_21", "005__14_35_20",
    "006__14_39_20", "007__14_43_20", "008__14_47_20"
]

TEST_DIRS = [
    "008__13_26_20", "009__14_51_20", "010__14_55_20",
    "011__14_59_20", "015__13_54_21"
]

# 路徑設定
REPO_ROOT = Path(__file__).parent.parent
HDF5_DIR = REPO_ROOT / "dataset" / "hdfs"
OUTPUT_DIR = Path(__file__).parent / "dataset"
CLASS_ID = 0  # person class


def get_split_for_sequence(sequence_name: str) -> str:
    """
    根據序列名稱判斷屬於哪個資料集分割
    
    Args:
        sequence_name: 序列名稱（例如 "007__13_22_20"）
    
    Returns:
        'train', 'val', 或 'test'
    """
    if sequence_name in TRAINING_DIRS:
        return "train"
    elif sequence_name in VALIDATION_DIRS:
        return "val"
    elif sequence_name in TEST_DIRS:
        return "test"
    else:
        print(f"警告: 序列 '{sequence_name}' 不在任何分割中，預設為 'train'")
        return "train"


def load_hdf5_data(hdf5_path: Path) -> List[Tuple[np.ndarray, List[Tuple[float, float]]]]:
    """
    從 HDF5 檔案讀取所有資料
    
    Args:
        hdf5_path: HDF5 檔案路徑
    
    Returns:
        資料列表 [(thermal_image, points_list), ...]
    """
    try:
        df = pd.read_hdf(str(hdf5_path))
        data_list = []
        
        for idx in range(len(df)):
            row = df.iloc[idx]
            
            # 讀取熱影像
            thermal_data = np.array(row['data'])
            if thermal_data.shape != (ORIGINAL_HEIGHT, ORIGINAL_WIDTH):
                # 嘗試 reshape
                thermal_data = thermal_data.reshape(ORIGINAL_HEIGHT, ORIGINAL_WIDTH)
            
            # 讀取點座標
            points = np.array(row['points'])
            if points.ndim == 2 and points.shape[1] == 2:
                points_list = [(float(p[0]), float(p[1])) for p in points]
            else:
                points_list = []
            
            data_list.append((thermal_data, points_list))
        
        return data_list
    except Exception as e:
        print(f"錯誤: 讀取 {hdf5_path} 時發生錯誤: {e}")
        return []


def convert_to_yolo_format(
    thermal_image: np.ndarray,
    points: List[Tuple[float, float]],
    sequence_name: str,
    frame_idx: int,
    output_split: str
) -> Tuple[str, str]:
    """
    將單一影像和標註轉換為 YOLO 格式
    
    Args:
        thermal_image: 24×32 熱影像
        points: 點座標列表
        sequence_name: 序列名稱
        frame_idx: 幀索引
        output_split: 輸出分割（train/val/test）
    
    Returns:
        (image_path, label_path) 相對路徑
    """
    # 1. 轉換影像：24×32 → 192×256 RGB
    # 使用 colormap 產生彩色熱力圖（與論文中的圖片一致）
    rgb_image = thermal_to_rgb(thermal_image, use_colormap=True, colormap=cv2.COLORMAP_JET)
    
    # 2. 轉換點座標為 YOLO bounding boxes（使用自適應大小）
    yolo_boxes = points_to_yolo_boxes(
        points,
        thermal_image=thermal_image,
        use_adaptive_size=True  # 根據熱源區域自動調整 bounding box 大小
    )
    
    # 3. 生成檔名
    image_filename = f"{sequence_name}_{frame_idx:06d}.png"
    label_filename = f"{sequence_name}_{frame_idx:06d}.txt"
    
    # 4. 儲存影像
    image_dir = OUTPUT_DIR / "images" / output_split
    image_dir.mkdir(parents=True, exist_ok=True)
    image_path = image_dir / image_filename
    Image.fromarray(rgb_image).save(image_path)
    
    # 5. 儲存標註（YOLO 格式）
    label_dir = OUTPUT_DIR / "labels" / output_split
    label_dir.mkdir(parents=True, exist_ok=True)
    label_path = label_dir / label_filename
    
    with open(label_path, 'w') as f:
        for x_center, y_center, width, height in yolo_boxes:
            # YOLO 格式：class x_center y_center width height (all normalized)
            f.write(f"{CLASS_ID} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}\n")
    
    # 返回相對路徑（相對於 dataset 目錄）
    image_rel_path = f"images/{output_split}/{image_filename}"
    label_rel_path = f"labels/{output_split}/{label_filename}"
    
    return image_rel_path, label_rel_path


def export_dataset():
    """
    主函數：匯出所有資料集
    """
    print("開始匯出 YOLO 格式資料集...")
    print(f"HDF5 目錄: {HDF5_DIR}")
    print(f"輸出目錄: {OUTPUT_DIR}")
    
    # 統計資訊
    stats = {
        "train": {"images": 0, "labels": 0, "total_points": 0},
        "val": {"images": 0, "labels": 0, "total_points": 0},
        "test": {"images": 0, "labels": 0, "total_points": 0}
    }
    
    # 遍歷所有 HDF5 檔案
    hdf5_files = sorted(HDF5_DIR.glob("*.h5"))
    print(f"找到 {len(hdf5_files)} 個 HDF5 檔案")
    
    for hdf5_path in hdf5_files:
        sequence_name = hdf5_path.stem  # 例如 "007__13_22_20"
        split = get_split_for_sequence(sequence_name)
        
        print(f"\n處理: {sequence_name} ({split})")
        
        # 讀取資料
        data_list = load_hdf5_data(hdf5_path)
        print(f"  讀取到 {len(data_list)} 筆資料")
        
        # 轉換每一筆資料
        for frame_idx, (thermal_image, points) in enumerate(data_list):
            if len(points) == 0:
                # 跳過沒有標註的影像（可選：也可以保留作為負樣本）
                continue
            
            try:
                image_rel_path, label_rel_path = convert_to_yolo_format(
                    thermal_image, points, sequence_name, frame_idx, split
                )
                
                stats[split]["images"] += 1
                stats[split]["labels"] += 1
                stats[split]["total_points"] += len(points)
                
            except Exception as e:
                print(f"  錯誤: 處理 {sequence_name} frame {frame_idx} 時發生錯誤: {e}")
                continue
        
        print(f"  完成: {stats[split]['images']} 張影像")
    
    # 輸出統計資訊
    print("\n" + "="*50)
    print("匯出完成！統計資訊：")
    print("="*50)
    for split in ["train", "val", "test"]:
        print(f"\n{split.upper()}:")
        print(f"  影像數量: {stats[split]['images']}")
        print(f"  標註數量: {stats[split]['labels']}")
        print(f"  總人數: {stats[split]['total_points']}")
        if stats[split]['images'] > 0:
            avg_people = stats[split]['total_points'] / stats[split]['images']
            print(f"  平均人數: {avg_people:.2f}")
    
    total_images = sum(s["images"] for s in stats.values())
    total_points = sum(s["total_points"] for s in stats.values())
    print(f"\n總計:")
    print(f"  影像數量: {total_images}")
    print(f"  總人數: {total_points}")
    if total_images > 0:
        print(f"  平均人數: {total_points / total_images:.2f}")


if __name__ == "__main__":
    export_dataset()
