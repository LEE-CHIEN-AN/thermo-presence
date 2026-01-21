"""
YOLOv8 訓練腳本
參考論文最佳配置進行訓練
"""

import os
import yaml
import tempfile
from pathlib import Path
from ultralytics import YOLO


# 訓練參數（參考論文最佳配置）
MODEL_NAME = "yolov8n.pt"  # 輕量級模型，適合 edge device
IMAGE_SIZE = (192, 256)  # (height, width) 保持 aspect ratio
EPOCHS = 200
BATCH_SIZE = 32
LEARNING_RATE = 0.001
OPTIMIZER = "Adam"

# 資料增強參數
AUGMENT_SCALE = 0.5  # scaling range
AUGMENT_FLIP = 0.5  # horizontal flip probability
AUGMENT_MOSAIC = 1.0  # mosaic augmentation probability
AUGMENT_MIXUP = 0.1  # mixup augmentation probability

# 路徑設定
DATA_YAML = Path(__file__).parent / "data.yaml"
OUTPUT_DIR = Path(__file__).parent / "runs"


def train():
    """
    訓練 YOLOv8 模型
    """
    print("="*60)
    print("YOLOv8 人數辨識模型訓練")
    print("="*60)
    print(f"模型: {MODEL_NAME}")
    print(f"影像尺寸: {IMAGE_SIZE}")
    print(f"Epochs: {EPOCHS}")
    print(f"Batch size: {BATCH_SIZE}")
    print(f"Learning rate: {LEARNING_RATE}")
    print(f"Optimizer: {OPTIMIZER}")
    print(f"資料配置: {DATA_YAML}")
    print("="*60)
    
    # 檢查資料配置檔案
    if not DATA_YAML.exists():
        print(f"錯誤: 找不到資料配置檔案 {DATA_YAML}")
        return
    
    # 檢查資料集目錄
    dataset_path = Path(__file__).parent / "dataset"
    if not dataset_path.exists():
        print(f"錯誤: 找不到資料集目錄 {dataset_path}")
        return
    
    # 更新 data.yaml 中的 path 為絕對路徑（動態修改）
    with open(DATA_YAML, 'r', encoding='utf-8') as f:
        data_config = yaml.safe_load(f)
    
    # 將 path 設為絕對路徑
    original_path = data_config.get('path', 'dataset')
    data_config['path'] = str(dataset_path.resolve())
    
    # 創建臨時的 YAML 檔案（避免修改原始檔案）
    temp_yaml = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8')
    yaml.dump(data_config, temp_yaml, default_flow_style=False, allow_unicode=True, sort_keys=False)
    temp_yaml.close()
    temp_yaml_path = temp_yaml.name
    
    print(f"資料集路徑: {dataset_path.resolve()}")
    print(f"使用臨時配置檔案: {temp_yaml_path}")
    
    # 載入模型
    print(f"\n載入模型: {MODEL_NAME}")
    model = YOLO(MODEL_NAME)
    
    # 訓練參數
    train_args = {
        "data": temp_yaml_path,  # 使用包含絕對路徑的臨時 YAML 檔案
        "epochs": EPOCHS,
        "batch": BATCH_SIZE,
        "imgsz": IMAGE_SIZE[0],  # YOLO 使用單一尺寸（高度）
        "lr0": LEARNING_RATE,
        "optimizer": OPTIMIZER.lower(),
        "project": str(OUTPUT_DIR),
        "name": "train",
        "exist_ok": True,
        "save": True,
        "save_period": 10,  # 每 10 epochs 儲存一次
        "val": True,  # 啟用驗證
        "plots": True,  # 生成訓練圖表
        "rect": True,  # 啟用 Rectangular Training（避免將 192×256 墊補成 256×256）
        "augment": True,  # 啟用資料增強
        "hsv_h": 0.015,  # HSV-Hue augmentation
        "hsv_s": 0.7,  # HSV-Saturation augmentation
        "hsv_v": 0.4,  # HSV-Value augmentation
        "degrees": 0.0,  # 旋轉角度（熱影像不建議旋轉）
        "translate": 0.1,  # 平移
        "scale": AUGMENT_SCALE,  # 縮放
        "flipud": 0.0,  # 垂直翻轉（不適用）
        "fliplr": AUGMENT_FLIP,  # 水平翻轉
        "mosaic": AUGMENT_MOSAIC,  # Mosaic augmentation
        "mixup": AUGMENT_MIXUP,  # Mixup augmentation
        "copy_paste": 0.0,  # Copy-paste augmentation
    }
    
    # 開始訓練
    print("\n開始訓練...")
    try:
        results = model.train(**train_args)
        
        print("\n" + "="*60)
        print("訓練完成！")
        print("="*60)
        print(f"最佳模型儲存位置: {OUTPUT_DIR / 'train' / 'weights' / 'best.pt'}")
        print(f"最後模型儲存位置: {OUTPUT_DIR / 'train' / 'weights' / 'last.pt'}")
        print(f"訓練結果: {OUTPUT_DIR / 'train'}")
        print("="*60)
        
        # 顯示訓練結果摘要
        if hasattr(results, 'results_dict'):
            print("\n訓練結果摘要:")
            for key, value in results.results_dict.items():
                print(f"  {key}: {value}")
        
    except Exception as e:
        print(f"\n訓練過程中發生錯誤: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 清理臨時檔案
        try:
            if 'temp_yaml_path' in locals():
                os.unlink(temp_yaml_path)
        except:
            pass


def validate_model(model_path: str = None):
    """
    驗證訓練好的模型
    
    Args:
        model_path: 模型路徑（預設使用最佳模型）
    """
    if model_path is None:
        model_path = OUTPUT_DIR / "train" / "weights" / "best.pt"
    
    if not Path(model_path).exists():
        print(f"錯誤: 找不到模型檔案 {model_path}")
        return
    
    print(f"載入模型: {model_path}")
    model = YOLO(str(model_path))
    
    # 在測試集上驗證
    print("在測試集上驗證...")
    results = model.val(data=str(DATA_YAML), split="test")
    
    print("\n驗證結果:")
    if hasattr(results, 'results_dict'):
        for key, value in results.results_dict.items():
            print(f"  {key}: {value}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="YOLOv8 訓練腳本")
    parser.add_argument("--mode", choices=["train", "val"], default="train",
                       help="執行模式：train（訓練）或 val（驗證）")
    parser.add_argument("--model", type=str, default=None,
                       help="驗證模式下的模型路徑")
    parser.add_argument("--epochs", type=int, default=EPOCHS,
                       help=f"訓練 epochs（預設: {EPOCHS}）")
    parser.add_argument("--batch", type=int, default=BATCH_SIZE,
                       help=f"Batch size（預設: {BATCH_SIZE}）")
    parser.add_argument("--lr", type=float, default=LEARNING_RATE,
                       help=f"Learning rate（預設: {LEARNING_RATE}）")
    
    args = parser.parse_args()
    
    if args.mode == "train":
        # 更新參數
        EPOCHS = args.epochs
        BATCH_SIZE = args.batch
        LEARNING_RATE = args.lr
        train()
    elif args.mode == "val":
        validate_model(args.model)
