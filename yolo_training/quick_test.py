"""
快速測試腳本：使用當前訓練的模型進行驗證和測試
"""

import os
from pathlib import Path
from ultralytics import YOLO
import yaml
import tempfile


# 路徑設定
BASE_DIR = Path(__file__).parent
MODEL_PATH = BASE_DIR / "runs" / "train" / "weights" / "best.pt"  # 使用最佳模型
DATA_YAML = BASE_DIR / "data.yaml"
DATASET_DIR = BASE_DIR / "dataset"
OUTPUT_DIR = BASE_DIR / "test_results"


def quick_validate():
    """
    快速驗證模型性能
    """
    print("="*60)
    print("快速模型驗證")
    print("="*60)
    
    # 檢查模型是否存在
    if not MODEL_PATH.exists():
        print(f"✗ 錯誤: 找不到模型檔案 {MODEL_PATH}")
        print("\n可用的模型檔案:")
        weights_dir = BASE_DIR / "runs" / "train" / "weights"
        if weights_dir.exists():
            for model_file in weights_dir.glob("*.pt"):
                print(f"  - {model_file.name}")
        return
    
    print(f"✓ 載入模型: {MODEL_PATH}")
    model = YOLO(str(MODEL_PATH))
    
    # 更新 data.yaml 路徑
    with open(DATA_YAML, 'r', encoding='utf-8') as f:
        data_config = yaml.safe_load(f)
    
    data_config['path'] = str(DATASET_DIR.resolve())
    
    temp_yaml = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8')
    yaml.dump(data_config, temp_yaml, default_flow_style=False, allow_unicode=True, sort_keys=False)
    temp_yaml.close()
    temp_yaml_path = temp_yaml.name
    
    try:
        # 在驗證集上測試
        print("\n在驗證集上測試...")
        val_results = model.val(data=temp_yaml_path, split="val", plots=True, save_json=True)
        
        print("\n" + "="*60)
        print("驗證集結果")
        print("="*60)
        if hasattr(val_results, 'results_dict'):
            for key, value in val_results.results_dict.items():
                print(f"  {key}: {value:.4f}" if isinstance(value, (int, float)) else f"  {key}: {value}")
        
        # 在測試集上測試
        print("\n在測試集上測試...")
        test_results = model.val(data=temp_yaml_path, split="test", plots=True, save_json=True)
        
        print("\n" + "="*60)
        print("測試集結果")
        print("="*60)
        if hasattr(test_results, 'results_dict'):
            for key, value in test_results.results_dict.items():
                print(f"  {key}: {value:.4f}" if isinstance(value, (int, float)) else f"  {key}: {value}")
        
        print("\n" + "="*60)
        print("✓ 測試完成！")
        print(f"結果圖表保存在: {BASE_DIR / 'runs' / 'val'}")
        print("="*60)
        
    except Exception as e:
        print(f"\n測試過程中發生錯誤: {e}")
        import traceback
        traceback.print_exc()
    finally:
        os.unlink(temp_yaml_path)


def test_single_image(image_path: str, conf_threshold: float = 0.25):
    """
    測試單張影像
    
    Args:
        image_path: 影像路徑
        conf_threshold: 信心度閾值
    """
    if not MODEL_PATH.exists():
        print(f"✗ 錯誤: 找不到模型檔案 {MODEL_PATH}")
        return
    
    print(f"載入模型: {MODEL_PATH}")
    model = YOLO(str(MODEL_PATH))
    
    # 預測
    results = model.predict(
        source=image_path,
        conf=conf_threshold,
        save=True,
        project=str(OUTPUT_DIR),
        name="predictions"
    )
    
    print(f"\n✓ 預測完成！")
    print(f"檢測到 {len(results[0].boxes)} 個人")
    print(f"結果保存在: {OUTPUT_DIR / 'predictions'}")
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="快速測試模型")
    parser.add_argument("--mode", choices=["val", "test", "image"], default="val",
                       help="測試模式：val（驗證集）、test（測試集）、image（單張影像）")
    parser.add_argument("--image", type=str, default=None,
                       help="單張影像模式下的影像路徑")
    parser.add_argument("--conf", type=float, default=0.25,
                       help="信心度閾值（預設: 0.25）")
    
    args = parser.parse_args()
    
    if args.mode == "val":
        quick_validate()
    elif args.mode == "test":
        # 只測試測試集
        if not MODEL_PATH.exists():
            print(f"✗ 錯誤: 找不到模型檔案 {MODEL_PATH}")
        else:
            model = YOLO(str(MODEL_PATH))
            with open(DATA_YAML, 'r', encoding='utf-8') as f:
                data_config = yaml.safe_load(f)
            data_config['path'] = str(DATASET_DIR.resolve())
            temp_yaml = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8')
            yaml.dump(data_config, temp_yaml, default_flow_style=False, allow_unicode=True, sort_keys=False)
            temp_yaml.close()
            temp_yaml_path = temp_yaml.name
            
            try:
                results = model.val(data=temp_yaml_path, split="test", plots=True)
                print("\n測試集結果:")
                if hasattr(results, 'results_dict'):
                    for key, value in results.results_dict.items():
                        print(f"  {key}: {value:.4f}" if isinstance(value, (int, float)) else f"  {key}: {value}")
            finally:
                os.unlink(temp_yaml_path)
    elif args.mode == "image":
        if args.image is None:
            print("錯誤: 請提供影像路徑 --image <path>")
        else:
            test_single_image(args.image, args.conf)
