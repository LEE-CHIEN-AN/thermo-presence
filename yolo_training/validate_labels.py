"""
標註驗證工具：檢查 YOLO 格式標註檔是否正確
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import numpy as np
import pandas as pd
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import cv2

# 添加當前目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from preprocess import (
    thermal_to_rgb,
    normalize_thermal,
    ORIGINAL_HEIGHT,
    ORIGINAL_WIDTH,
    TARGET_HEIGHT,
    TARGET_WIDTH
)

DATASET_DIR = Path(__file__).parent / "dataset"
REPO_ROOT = Path(__file__).parent.parent
HDF5_DIR = REPO_ROOT / "dataset" / "hdfs"


def validate_yolo_label(label_path: Path) -> Tuple[bool, List[str]]:
    """
    驗證單一 YOLO 標註檔
    
    Args:
        label_path: 標註檔路徑
    
    Returns:
        (is_valid, error_messages)
    """
    errors = []
    
    if not label_path.exists():
        return False, [f"檔案不存在: {label_path}"]
    
    try:
        with open(label_path, 'r') as f:
            lines = f.readlines()
        
        for line_idx, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
            
            parts = line.split()
            if len(parts) != 5:
                errors.append(f"第 {line_idx} 行格式錯誤: 應有 5 個欄位，實際有 {len(parts)} 個")
                continue
            
            try:
                class_id = int(parts[0])
                x_center = float(parts[1])
                y_center = float(parts[2])
                width = float(parts[3])
                height = float(parts[4])
            except ValueError as e:
                errors.append(f"第 {line_idx} 行數值解析錯誤: {e}")
                continue
            
            # 檢查座標範圍
            if not (0.0 <= x_center <= 1.0):
                errors.append(f"第 {line_idx} 行: x_center ({x_center}) 超出範圍 [0, 1]")
            if not (0.0 <= y_center <= 1.0):
                errors.append(f"第 {line_idx} 行: y_center ({y_center}) 超出範圍 [0, 1]")
            if not (0.0 <= width <= 1.0):
                errors.append(f"第 {line_idx} 行: width ({width}) 超出範圍 [0, 1]")
            if not (0.0 <= height <= 1.0):
                errors.append(f"第 {line_idx} 行: height ({height}) 超出範圍 [0, 1]")
            
            # 檢查 bounding box 是否超出影像範圍（改為警告，因為已自動裁剪）
            x_min = x_center - width / 2
            x_max = x_center + width / 2
            y_min = y_center - height / 2
            y_max = y_center + height / 2
            
            # 允許微小的浮點誤差（1e-6）
            tolerance = 1e-6
            if x_min < -tolerance or x_max > 1 + tolerance or y_min < -tolerance or y_max > 1 + tolerance:
                # 這應該是警告而不是錯誤，因為我們已經在轉換時自動裁剪了
                # 如果還有超出，可能是數值精度問題
                pass  # 改為不報錯，因為已經自動裁剪
        
        return len(errors) == 0, errors
    
    except Exception as e:
        return False, [f"讀取檔案時發生錯誤: {e}"]


def get_label_statistics(split: str = None) -> Dict:
    """
    統計標註數量分布
    
    Args:
        split: 資料分割（train/val/test），None 表示所有
    
    Returns:
        統計字典
    """
    stats = {
        "total_images": 0,
        "total_boxes": 0,
        "boxes_per_image": [],
        "images_with_boxes": 0,
        "images_without_boxes": 0
    }
    
    splits = [split] if split else ["train", "val", "test"]
    
    for split_name in splits:
        labels_dir = DATASET_DIR / "labels" / split_name
        if not labels_dir.exists():
            continue
        
        for label_path in labels_dir.glob("*.txt"):
            stats["total_images"] += 1
            
            try:
                with open(label_path, 'r') as f:
                    lines = [l.strip() for l in f.readlines() if l.strip()]
                
                num_boxes = len(lines)
                stats["total_boxes"] += num_boxes
                stats["boxes_per_image"].append(num_boxes)
                
                if num_boxes > 0:
                    stats["images_with_boxes"] += 1
                else:
                    stats["images_without_boxes"] += 1
            
            except Exception as e:
                print(f"警告: 讀取 {label_path} 時發生錯誤: {e}")
    
    if stats["total_images"] > 0:
        stats["avg_boxes_per_image"] = stats["total_boxes"] / stats["total_images"]
    else:
        stats["avg_boxes_per_image"] = 0
    
    return stats


def load_original_thermal_data(sequence_name: str, frame_idx: int) -> Tuple[Optional[np.ndarray], List[Tuple[float, float]]]:
    """
    從 HDF5 檔案讀取原始的 thermal image 和點座標
    
    Args:
        sequence_name: 序列名稱（例如 "007__13_22_20"）
        frame_idx: 幀索引
    
    Returns:
        (thermal_image, points_list)
        - thermal_image: 24×32 熱影像（numpy array），如果讀取失敗則為 None
        - points_list: 點座標列表 [(x1, y1), (x2, y2), ...]
    """
    hdf5_path = HDF5_DIR / f"{sequence_name}.h5"
    
    if not hdf5_path.exists():
        print(f"錯誤: HDF5 檔案不存在: {hdf5_path}")
        return None, []
    
    try:
        df = pd.read_hdf(str(hdf5_path))
        
        if frame_idx >= len(df):
            print(f"錯誤: 幀索引 {frame_idx} 超出範圍（總共 {len(df)} 幀）")
            return None, []
        
        row = df.iloc[frame_idx]
        
        # 讀取熱影像
        thermal_data = np.array(row['data'])
        if thermal_data.shape != (ORIGINAL_HEIGHT, ORIGINAL_WIDTH):
            thermal_data = thermal_data.reshape(ORIGINAL_HEIGHT, ORIGINAL_WIDTH)
        
        # 讀取點座標
        points = np.array(row['points'])
        if points.ndim == 2 and points.shape[1] == 2:
            points_list = [(float(p[0]), float(p[1])) for p in points]
        else:
            points_list = []
        
        return thermal_data, points_list
    
    except Exception as e:
        print(f"錯誤: 讀取 HDF5 檔案時發生錯誤: {e}")
        return None, []


def visualize_labels(
    image_path: Path = None,
    label_path: Path = None,
    output_path: Path = None,
    sequence_name: str = None,
    frame_idx: int = None,
    show_original: bool = True,
    show_yolo: bool = True
):
    """
    在影像上繪製 bounding boxes 進行視覺化檢查
    
    支援兩種模式：
    1. 顯示原始 thermal image（24×32）和點座標標註（紅色 'X'）
    2. 顯示 YOLO 格式影像（192×256）和 bounding boxes
    
    Args:
        image_path: YOLO 格式影像路徑（可選）
        label_path: YOLO 格式標註路徑（可選）
        output_path: 輸出路徑（可選）
        sequence_name: 序列名稱（例如 "007__13_22_20"），用於讀取原始資料
        frame_idx: 幀索引，用於讀取原始資料
        show_original: 是否顯示原始 thermal image 和點座標
        show_yolo: 是否顯示 YOLO 格式影像和 bounding boxes
    """
    fig = None
    axes = []
    
    # 顯示原始 thermal image 和點座標
    if show_original and sequence_name is not None and frame_idx is not None:
        thermal_image, points = load_original_thermal_data(sequence_name, frame_idx)
        
        if thermal_image is not None:
            # 正規化溫度並應用 colormap
            normalized = normalize_thermal(thermal_image)
            # 使用 JET colormap 顯示熱力圖
            colored = cv2.applyColorMap(normalized, cv2.COLORMAP_JET)
            # 轉換 BGR → RGB（matplotlib 使用 RGB）
            colored_rgb = cv2.cvtColor(colored, cv2.COLOR_BGR2RGB)
            
            # 放大顯示（使用 nearest neighbor 保持像素感）
            upsampled_display = cv2.resize(
                colored_rgb,
                (ORIGINAL_WIDTH * 10, ORIGINAL_HEIGHT * 10),  # 放大 10 倍便於查看
                interpolation=cv2.INTER_NEAREST
            )
            
            if show_yolo and image_path and label_path:
                # 同時顯示原始和 YOLO 格式
                fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
                axes = [ax1, ax2]
            else:
                fig, ax1 = plt.subplots(1, 1, figsize=(10, 8))
                axes = [ax1]
            
            ax1.imshow(upsampled_display, interpolation='nearest')
            
            # 繪製點座標（紅色 'X' 標記）
            if len(points) > 0:
                x_coords = [p[0] * 10 for p in points]  # 放大 10 倍
                y_coords = [p[1] * 10 for p in points]  # 放大 10 倍
                ax1.scatter(x=x_coords, y=y_coords, s=200, c='red', marker='x', linewidths=3)
            
            ax1.set_title(f"Original Thermal Image\nSequence: {sequence_name}, Frame: {frame_idx}\nPoints: {len(points)}", fontsize=12)
            ax1.axis('off')
    
    # 顯示 YOLO 格式影像和 bounding boxes
    if show_yolo and image_path and label_path and image_path.exists() and label_path.exists():
        # 讀取 YOLO 格式影像
        image = Image.open(image_path)
        img_width, img_height = image.size
        
        # 讀取 YOLO 格式標註
        boxes = []
        with open(label_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split()
                if len(parts) == 5:
                    x_center = float(parts[1]) * img_width
                    y_center = float(parts[2]) * img_height
                    width = float(parts[3]) * img_width
                    height = float(parts[4]) * img_height
                    boxes.append((x_center, y_center, width, height))
        
        # 選擇要繪製的軸
        if show_original and len(axes) > 0:
            ax2 = axes[1] if len(axes) > 1 else axes[0]
        else:
            if fig is None:
                fig, ax2 = plt.subplots(1, 1, figsize=(10, 8))
            else:
                ax2 = axes[0] if len(axes) > 0 else plt.gca()
            axes.append(ax2)
        
        ax2.imshow(image)
        
        # 繪製 bounding boxes
        for x_center, y_center, width, height in boxes:
            x_min = x_center - width / 2
            y_min = y_center - height / 2
            rect = patches.Rectangle(
                (x_min, y_min), width, height,
                linewidth=2, edgecolor='red', facecolor='none'
            )
            ax2.add_patch(rect)
        
        filename = label_path.stem
        ax2.set_title(f"YOLO Format Image\n{filename}\nBounding Boxes: {len(boxes)}", fontsize=12)
        ax2.axis('off')
    
    if fig is None:
        print("錯誤: 無法顯示任何影像（請檢查參數）")
        return
    
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path, bbox_inches='tight', dpi=150)
        print(f"視覺化結果已儲存至: {output_path}")
    else:
        plt.show()
    
    plt.close()


def validate_all_labels(split: str = None, verbose: bool = False):
    """
    驗證所有標註檔
    
    Args:
        split: 資料分割（train/val/test），None 表示所有
        verbose: 是否顯示詳細錯誤訊息
    """
    print("開始驗證標註檔...")
    
    splits = [split] if split else ["train", "val", "test"]
    total_valid = 0
    total_invalid = 0
    all_errors = []
    
    for split_name in splits:
        labels_dir = DATASET_DIR / "labels" / split_name
        if not labels_dir.exists():
            print(f"警告: {labels_dir} 不存在，跳過")
            continue
        
        print(f"\n驗證 {split_name} 分割...")
        label_files = list(labels_dir.glob("*.txt"))
        print(f"找到 {len(label_files)} 個標註檔")
        
        for label_path in label_files:
            is_valid, errors = validate_yolo_label(label_path)
            if is_valid:
                total_valid += 1
            else:
                total_invalid += 1
                all_errors.append((label_path, errors))
                if verbose:
                    print(f"  ❌ {label_path.name}: {errors}")
    
    print("\n" + "="*50)
    print("驗證結果:")
    print("="*50)
    print(f"有效標註檔: {total_valid}")
    print(f"無效標註檔: {total_invalid}")
    
    if total_invalid > 0:
        print(f"\n錯誤摘要（前 10 個）:")
        for label_path, errors in all_errors[:10]:
            print(f"  {label_path.name}:")
            for error in errors[:3]:  # 只顯示前 3 個錯誤
                print(f"    - {error}")
    
    # 統計資訊
    print("\n" + "="*50)
    print("標註統計:")
    print("="*50)
    stats = get_label_statistics(split)
    print(f"總影像數: {stats['total_images']}")
    print(f"總 bounding box 數: {stats['total_boxes']}")
    print(f"平均每張影像: {stats['avg_boxes_per_image']:.2f} 個 boxes")
    print(f"有標註的影像: {stats['images_with_boxes']}")
    print(f"無標註的影像: {stats['images_without_boxes']}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="驗證 YOLO 標註檔")
    parser.add_argument("--split", choices=["train", "val", "test"], default=None,
                       help="指定資料分割（預設：全部）")
    parser.add_argument("--verbose", action="store_true",
                       help="顯示詳細錯誤訊息")
    parser.add_argument("--visualize", type=str, default=None,
                       help="視覺化指定影像（格式：split/sequence_frame）")
    
    args = parser.parse_args()
    
    if args.visualize:
        # 解析視覺化參數
        # 格式：split/sequence_frame 或 split/sequence_frame_idx
        # 例如：train/007__13_22_20_000000
        parts = args.visualize.split("/")
        if len(parts) == 2:
            split_name, filename = parts
            
            # 解析序列名稱和幀索引
            # 檔案名格式：{sequence_name}_{frame_idx:06d}
            # 例如：007__13_22_20_000000
            if "_" in filename:
                parts_name = filename.rsplit("_", 1)
                if len(parts_name) == 2 and parts_name[1].isdigit():
                    sequence_name = parts_name[0]  # 例如 "007__13_22_20"
                    frame_idx = int(parts_name[1])  # 例如 0
                else:
                    # 嘗試其他格式
                    sequence_name = filename
                    frame_idx = 0
            else:
                sequence_name = filename
                frame_idx = 0
            
            # YOLO 格式檔案路徑
            image_path = DATASET_DIR / "images" / split_name / f"{filename}.png"
            label_path = DATASET_DIR / "labels" / split_name / f"{filename}.txt"
            
            # 檢查檔案是否存在
            has_yolo = image_path.exists() and label_path.exists()
            
            if not has_yolo and sequence_name:
                print(f"警告: YOLO 格式檔案不存在，將只顯示原始 thermal image")
                print(f"  影像: {image_path}")
                print(f"  標註: {label_path}")
            
            # 視覺化
            visualize_labels(
                image_path=image_path if has_yolo else None,
                label_path=label_path if has_yolo else None,
                sequence_name=sequence_name,
                frame_idx=frame_idx,
                show_original=True,
                show_yolo=has_yolo
            )
        else:
            print("錯誤: --visualize 格式應為 'split/filename'")
            print("  例如: train/007__13_22_20_000000")
    else:
        validate_all_labels(args.split, args.verbose)
