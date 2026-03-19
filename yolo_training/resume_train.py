"""
YOLOv8 恢復訓練腳本
從檢查點恢復中斷的訓練
"""

import os
import sys
import yaml
import tempfile
import pandas as pd
from pathlib import Path
from ultralytics import YOLO


# 訓練參數（與 train.py 保持一致）
MODEL_NAME = "yolov8n.pt"
IMAGE_SIZE = (192, 256)
EPOCHS = 200
BATCH_SIZE = 32
LEARNING_RATE = 0.001
OPTIMIZER = "Adam"

# 資料增強參數
AUGMENT_SCALE = 0.5
AUGMENT_FLIP = 0.5
AUGMENT_MOSAIC = 1.0
AUGMENT_MIXUP = 0.1

# 路徑設定
DATA_YAML = Path(__file__).parent / "data.yaml"
OUTPUT_DIR = Path(__file__).parent / "runs"
TRAIN_DIR = OUTPUT_DIR / "train"
WEIGHTS_DIR = TRAIN_DIR / "weights"
RESULTS_CSV = TRAIN_DIR / "results.csv"


def find_latest_checkpoint():
    """
    自動找到最新的檢查點
    
    Returns:
        檢查點路徑，如果找不到則返回 None
    """
    if not WEIGHTS_DIR.exists():
        return None
    
    # 優先使用 last.pt
    last_pt = WEIGHTS_DIR / "last.pt"
    if last_pt.exists():
        return last_pt
    
    # 否則找最新的 epoch 檢查點
    epoch_files = sorted(WEIGHTS_DIR.glob("epoch*.pt"), reverse=True)
    if epoch_files:
        return epoch_files[0]
    
    return None


def get_training_progress():
    """
    從 results.csv 讀取訓練進度
    
    Returns:
        (current_epoch, total_epochs, latest_metrics) 或 None
    """
    if not RESULTS_CSV.exists():
        return None
    
    try:
        df = pd.read_csv(RESULTS_CSV)
        if len(df) == 0:
            return None
        
        latest_row = df.iloc[-1]
        current_epoch = int(latest_row['epoch']) if 'epoch' in latest_row else len(df) - 1
        
        return {
            'current_epoch': current_epoch,
            'total_epochs': EPOCHS,
            'progress': f"{current_epoch}/{EPOCHS}",
            'latest_metrics': latest_row.to_dict() if hasattr(latest_row, 'to_dict') else None
        }
    except Exception as e:
        print(f"警告: 無法讀取訓練進度: {e}")
        return None


def list_available_checkpoints():
    """
    列出所有可用的檢查點
    """
    if not WEIGHTS_DIR.exists():
        print("  沒有找到檢查點目錄")
        return
    
    checkpoints = []
    
    # 檢查 last.pt
    last_pt = WEIGHTS_DIR / "last.pt"
    if last_pt.exists():
        size = last_pt.stat().st_size / (1024 * 1024)  # MB
        checkpoints.append(("last.pt", size, "最後一個 epoch"))
    
    # 檢查所有 epoch 檢查點
    epoch_files = sorted(WEIGHTS_DIR.glob("epoch*.pt"))
    for epoch_file in epoch_files:
        size = epoch_file.stat().st_size / (1024 * 1024)  # MB
        epoch_num = epoch_file.stem.replace("epoch", "")
        checkpoints.append((epoch_file.name, size, f"Epoch {epoch_num}"))
    
    if checkpoints:
        print("\n可用的檢查點:")
        print(f"{'檔案名稱':<20} {'大小 (MB)':<12} {'說明':<20}")
        print("-" * 55)
        for name, size, desc in checkpoints:
            print(f"{name:<20} {size:>10.2f} MB  {desc:<20}")
    else:
        print("  沒有找到任何檢查點")


def resume_training(checkpoint_path: str = None, target_epochs: int = None):
    """
    從檢查點恢復訓練
    
    Args:
        checkpoint_path: 檢查點路徑（None 則自動尋找）
        target_epochs: 目標總 epochs（None 則使用預設值）
    """
    print("="*60)
    print("YOLOv8 恢復訓練")
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
    
    # 自動尋找檢查點
    if checkpoint_path is None:
        checkpoint_path = find_latest_checkpoint()
        if checkpoint_path is None:
            print("\n錯誤: 找不到任何檢查點！")
            print("\n可用的選項:")
            list_available_checkpoints()
            print("\n請先執行 train.py 開始訓練，或手動指定檢查點路徑。")
            return
        checkpoint_path = str(checkpoint_path)
    
    checkpoint_path_obj = Path(checkpoint_path)
    if not checkpoint_path_obj.exists():
        print(f"\n錯誤: 找不到檢查點檔案: {checkpoint_path}")
        list_available_checkpoints()
        return
    
    # 顯示檢查點資訊
    print(f"\n檢查點: {checkpoint_path}")
    checkpoint_size = checkpoint_path_obj.stat().st_size / (1024 * 1024)
    print(f"檔案大小: {checkpoint_size:.2f} MB")
    
    # 顯示訓練進度
    progress = get_training_progress()
    if progress:
        print(f"\n訓練進度: {progress['progress']} epochs")
        print(f"已完成: {progress['current_epoch']} / {progress['total_epochs']} epochs")
        remaining = progress['total_epochs'] - progress['current_epoch']
        print(f"剩餘: {remaining} epochs")
        
        if progress['latest_metrics']:
            print("\n最新指標:")
            metrics = progress['latest_metrics']
            if 'metrics/precision(B)' in metrics:
                print(f"  Precision: {metrics.get('metrics/precision(B)', 'N/A'):.4f}")
            if 'metrics/recall(B)' in metrics:
                print(f"  Recall: {metrics.get('metrics/recall(B)', 'N/A'):.4f}")
            if 'metrics/mAP50(B)' in metrics:
                print(f"  mAP50: {metrics.get('metrics/mAP50(B)', 'N/A'):.4f}")
    else:
        print("\n無法讀取訓練進度（results.csv 不存在或格式錯誤）")
    
    # 設定目標 epochs
    if target_epochs is None:
        target_epochs = EPOCHS
    
    print(f"\n目標 epochs: {target_epochs}")
    print("="*60)
    
    # 更新 data.yaml 中的 path 為絕對路徑
    with open(DATA_YAML, 'r', encoding='utf-8') as f:
        data_config = yaml.safe_load(f)
    
    dataset_path = Path(__file__).parent / "dataset"
    data_config['path'] = str(dataset_path.resolve())
    
    # 創建臨時的 YAML 檔案
    temp_yaml = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8')
    yaml.dump(data_config, temp_yaml, default_flow_style=False, allow_unicode=True, sort_keys=False)
    temp_yaml.close()
    temp_yaml_path = temp_yaml.name
    
    print(f"\n資料集路徑: {dataset_path.resolve()}")
    print(f"使用臨時配置檔案: {temp_yaml_path}")
    
    # 載入檢查點
    print(f"\n載入檢查點: {checkpoint_path}")
    try:
        model = YOLO(checkpoint_path)
    except Exception as e:
        print(f"錯誤: 無法載入檢查點: {e}")
        return
    
    # 訓練參數（與 train.py 保持一致）
    train_args = {
        "data": temp_yaml_path,
        "epochs": target_epochs,
        "batch": BATCH_SIZE,
        "imgsz": IMAGE_SIZE[0],
        "lr0": LEARNING_RATE,
        "optimizer": OPTIMIZER.lower(),
        "project": str(OUTPUT_DIR),
        "name": "train",
        "exist_ok": True,
        "save": True,
        "save_period": 10,
        "val": True,
        "plots": True,
        "rect": True,
        "augment": True,
        "hsv_h": 0.015,
        "hsv_s": 0.7,
        "hsv_v": 0.4,
        "degrees": 0.0,
        "translate": 0.1,
        "scale": AUGMENT_SCALE,
        "flipud": 0.0,
        "fliplr": AUGMENT_FLIP,
        "mosaic": AUGMENT_MOSAIC,
        "mixup": AUGMENT_MIXUP,
        "copy_paste": 0.0,
        "resume": True,  # 關鍵：啟用恢復訓練
    }
    
    # 開始恢復訓練
    print("\n" + "="*60)
    print("恢復訓練...")
    print("="*60)
    
    try:
        results = model.train(**train_args)
        
        print("\n" + "="*60)
        print("訓練完成！")
        print("="*60)
        print(f"最佳模型: {OUTPUT_DIR / 'train' / 'weights' / 'best.pt'}")
        print(f"最後模型: {OUTPUT_DIR / 'train' / 'weights' / 'last.pt'}")
        print(f"訓練結果: {OUTPUT_DIR / 'train'}")
        print("="*60)
        
        # 顯示訓練結果摘要
        if hasattr(results, 'results_dict'):
            print("\n訓練結果摘要:")
            for key, value in results.results_dict.items():
                if isinstance(value, (int, float)):
                    print(f"  {key}: {value:.4f}")
                else:
                    print(f"  {key}: {value}")
        
    except KeyboardInterrupt:
        print("\n\n訓練被用戶中斷")
        print("可以使用此腳本再次恢復訓練")
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


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="YOLOv8 恢復訓練腳本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  # 自動從最新的檢查點恢復
  python resume_train.py
  
  # 從指定的檢查點恢復
  python resume_train.py --checkpoint runs/train/weights/last.pt
  
  # 從特定 epoch 恢復並設定目標 epochs
  python resume_train.py --checkpoint runs/train/weights/epoch50.pt --epochs 200
  
  # 列出所有可用的檢查點
  python resume_train.py --list
        """
    )
    
    parser.add_argument(
        "--checkpoint", "-c",
        type=str,
        default=None,
        help="檢查點路徑（預設：自動尋找最新的檢查點）"
    )
    
    parser.add_argument(
        "--epochs", "-e",
        type=int,
        default=EPOCHS,
        help=f"目標總 epochs（預設: {EPOCHS}）"
    )
    
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="列出所有可用的檢查點"
    )
    
    args = parser.parse_args()
    
    if args.list:
        print("="*60)
        print("可用的檢查點列表")
        print("="*60)
        list_available_checkpoints()
        
        # 顯示訓練進度
        progress = get_training_progress()
        if progress:
            print(f"\n當前訓練進度: {progress['progress']} epochs")
        else:
            print("\n無法讀取訓練進度")
        
        sys.exit(0)
    
    resume_training(
        checkpoint_path=args.checkpoint,
        target_epochs=args.epochs
    )
