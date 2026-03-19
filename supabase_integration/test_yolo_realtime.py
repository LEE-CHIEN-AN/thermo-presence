"""
使用訓練好的 YOLOv8 模型，直接對 Supabase 的即時熱影像資料做人數偵測，
用來「套套看」實際效果，並與原本 U-Net 密度圖的人數做對比。

這個腳本：
- 從 Supabase 抓取最新或指定的熱影像 frame
- 使用原本的 U-Net/AutoEncoder 管線算出「舊方法」人數
- 使用 YOLOv8 (best.pt 或 last.pt) 在同一張影像上做偵測，算出「YOLO 人數」
- 在終端列出兩者的人數與差異
- 可選：將 YOLO 結果另外寫入 Supabase 的一個獨立資料表（不會覆蓋原本結果）
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Optional, Dict, Any, List

import numpy as np
import cv2
import matplotlib.pyplot as plt
from dotenv import load_dotenv
from ultralytics import YOLO

# 載入 .env 檔案（Supabase 設定）
load_dotenv()

# 確保可以匯入 supabase_integration 內的模組
CURRENT_DIR = Path(__file__).parent
REPO_ROOT = CURRENT_DIR.parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from supabase_client import SupabaseThermalProcessor  # type: ignore
from yolo_training.preprocess import (  # type: ignore
    thermal_to_rgb,
    ORIGINAL_HEIGHT,
    ORIGINAL_WIDTH,
)


def load_yolo_model(weights_path: Optional[str] = None) -> YOLO:
    """
    載入 YOLOv8 模型。

    Args:
        weights_path: 權重檔路徑（預設使用 yolo_training/runs/train/weights/best.pt）
    """
    if weights_path is None:
        default_path = REPO_ROOT / "yolo_training" / "runs" / "train" / "weights" / "best.pt"
        alt_path = REPO_ROOT / "yolo_training" / "runs" / "train" / "weights" / "last.pt"
        if default_path.exists():
            weights_path = str(default_path)
        elif alt_path.exists():
            weights_path = str(alt_path)
        else:
            raise FileNotFoundError(
                "找不到 YOLO 權重檔案。\n"
                f"預期路徑之一：\n - {default_path}\n - {alt_path}\n"
                "請先完成 yolo_training/train.py 的訓練，或手動指定 --weights 路徑。"
            )

    print(f"載入 YOLO 權重: {weights_path}")
    model = YOLO(weights_path)
    return model


def fetch_thermal_frame(
    processor: SupabaseThermalProcessor,
    frame_id: int,
) -> np.ndarray:
    """
    從 Supabase 取得指定 frame 的熱影像資料，並轉成 24×32 的熱影像。

    熱影像原始格式為 12×16（MLX90641），會上採樣到 24×32，
    與 U-Net / YOLO 前處理保持一致。
    """
    resp = (
        processor.supabase.table("thermal_frames")
        .select("data")
        .eq("id", frame_id)
        .execute()
    )
    if not resp.data:
        raise RuntimeError(f"在 Supabase 中找不到 frame_id={frame_id} 的資料")

    raw_data = processor.parse_data_array(resp.data[0]["data"])  # 192 floats
    thermal_12x16 = raw_data.reshape(12, 16)

    # 上採樣到 24×32（與現有 U-Net 管線一致）
    thermal_24x32 = cv2.resize(
        thermal_12x16,
        (ORIGINAL_WIDTH, ORIGINAL_HEIGHT),  # (width, height) = (32, 24)
        interpolation=cv2.INTER_CUBIC,
    )
    return thermal_24x32.astype(np.float32)


def run_yolo_on_thermal(
    model: YOLO,
    thermal_24x32: np.ndarray,
    conf: float = 0.25,
    iou: float = 0.7,
    max_det: int = 300,
) -> Dict[str, Any]:
    """
    對一張 24×32 熱影像跑 YOLOv8 偵測。

    流程：
    - 使用跟訓練時一樣的前處理：normalize + 上採樣 + colormap (JET)
    - 得到 192×256 RGB 影像
    - 丟進 YOLO 做偵測
    """
    if thermal_24x32.shape != (ORIGINAL_HEIGHT, ORIGINAL_WIDTH):
        raise ValueError(
            f"預期輸入為 24×32，但得到 {thermal_24x32.shape}，請先調整尺寸。"
        )

    # 轉成 192×256 彩色熱力圖（與訓練資料一致）
    # 注意：cv2.applyColorMap 產出的是 BGR。
    # 但我們的訓練資料是用 PIL 直接把這個 BGR array 當成 RGB 存成 PNG，
    # Ultralytics 訓練時又用 cv2.imread 讀回 BGR，因此「訓練時實際餵進模型的通道順序」等於 BGR->RGB 反轉一次後的結果。
    # 為了讓即時推論跟訓練一致，這裡也做一次 BGR->RGB 再餵給 YOLO。
    bgr_image = thermal_to_rgb(
        thermal_24x32,
        use_colormap=True,
        colormap=cv2.COLORMAP_JET,
    )  # shape: (192, 256, 3), uint8 (BGR)

    # YOLO 輸入（對齊訓練時實際讀圖的通道順序）
    yolo_input = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2RGB)

    # Matplotlib 顯示用（RGB）
    rgb_image_for_plot = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2RGB)

    # YOLO 推論（直接用 numpy array 當輸入）
    results = model.predict(
        source=yolo_input,
        imgsz=ORIGINAL_HEIGHT * 8,  # 192，與訓練時一致
        conf=conf,
        iou=iou,
        max_det=max_det,
        verbose=False,
    )

    if not results:
        return {
            "people_count": 0,
            "boxes": [],
            "raw_results": None,
            "rgb_image": bgr_image,
            "rgb_image_plot": rgb_image_for_plot,
            "thermal_24x32": thermal_24x32,
        }

    r0 = results[0]
    boxes = r0.boxes
    num_people = len(boxes) if boxes is not None else 0

    return {
        "people_count": int(num_people),
        "boxes": boxes,
        "raw_results": r0,
        "rgb_image": bgr_image,
        "rgb_image_plot": rgb_image_for_plot,
        "thermal_24x32": thermal_24x32,
    }


def save_yolo_result_to_supabase(
    processor: SupabaseThermalProcessor,
    frame_result: Dict[str, Any],
    yolo_people_count: int,
    table_name: str,
    model_tag: str,
) -> Optional[Dict[str, Any]]:
    """
    將 YOLO 的人數結果寫回 Supabase 的獨立資料表（不覆蓋原本 people_count_results）。

    建議資料表 schema（Postgres）：

    - id                BIGSERIAL PRIMARY KEY
    - frame_id          INTEGER (references thermal_frames.id)
    - session_id        TEXT
    - timestamp         TIMESTAMPTZ
    - people_count_yolo INTEGER
    - model_tag         TEXT        -- 例如 'yolov8n_best'
    - created_at        TIMESTAMPTZ DEFAULT now()
    """
    try:
        data = {
            "frame_id": frame_result["id"],
            "session_id": frame_result["session_id"],
            "timestamp": frame_result["timestamp"],
            "people_count_yolo": int(yolo_people_count),
            "model_tag": model_tag,
        }
        resp = processor.supabase.table(table_name).insert(data).execute()
        return resp.data[0] if resp.data else None
    except Exception as e:
        print(f"✗ 將 YOLO 結果寫回 Supabase 時發生錯誤: {e}")
        return None


def print_comparison(
    frame_result: Dict[str, Any],
    yolo_people_count: int,
) -> None:
    """在終端輸出 U-Net vs YOLO 的人數對比。"""
    print("\n" + "=" * 60)
    print("Supabase 即時資料：U-Net vs YOLO 人數對比")
    print("=" * 60)
    print(f"Frame ID        : {frame_result['id']}")
    print(f"Session ID      : {frame_result['session_id']}")
    print(f"Timestamp       : {frame_result['timestamp']}")
    print("-" * 60)
    print(f"U-Net 人數 (原系統): {frame_result['people_count']:.2f}  "
          f"(rounded={frame_result['people_count_rounded']})")
    print(f"YOLO 人數        : {yolo_people_count}")
    diff = yolo_people_count - frame_result["people_count_rounded"]
    sign = "+" if diff >= 0 else ""
    print(f"差異 (YOLO - U-Net): {sign}{diff}")
    print("=" * 60)


def visualize_comparison(
    frame_result: Dict[str, Any],
    thermal_24x32: np.ndarray,
    yolo_res: Dict[str, Any],
    save_images: bool = False,
    output_dir: Optional[str] = None,
) -> None:
    """
    視覺化 U-Net 與 YOLO 的結果：
    - 左：原始熱影像（JET colormap），疊 YOLO boxes
    - 右：U-Net 密度圖（24×32）
    """
    density_map = frame_result.get("density_map")
    if density_map is None:
        print("✗ 無法視覺化：找不到 density_map")
        return

    # 使用真實溫度矩陣畫 IR frame（避免 Ultralytics plot() 的通道/色彩反轉問題）
    # 以 24×32 上採樣到 192×256 方便疊加 YOLO boxes（YOLO 的 boxes 座標系就是 192×256）
    thermal_24x32_src = yolo_res.get("thermal_24x32", thermal_24x32)
    if thermal_24x32_src is None:
        thermal_24x32_src = np.zeros((24, 32), dtype=np.float32)

    thermal_display = cv2.resize(
        thermal_24x32_src.astype(np.float32),
        (256, 192),  # (width, height)
        interpolation=cv2.INTER_CUBIC,
    )

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # 左：IR frame + YOLO boxes（溫度用 viridis，與你貼的 IR frame 視覺一致）
    ax0 = axes[0]
    vmin = float(np.nanmin(thermal_24x32_src))
    vmax = float(np.nanmax(thermal_24x32_src))
    im_temp = ax0.imshow(thermal_display, cmap="viridis", origin="upper", vmin=vmin, vmax=vmax)

    # 疊加 YOLO boxes（若有）
    r0 = yolo_res.get("raw_results")
    if r0 is not None and getattr(r0, "boxes", None) is not None and len(r0.boxes) > 0:
        from matplotlib.patches import Rectangle
        xyxy = r0.boxes.xyxy.cpu().numpy()
        confs = r0.boxes.conf.cpu().numpy() if getattr(r0.boxes, "conf", None) is not None else None
        for i, (x1, y1, x2, y2) in enumerate(xyxy):
            rect = Rectangle(
                (float(x1), float(y1)),
                float(x2 - x1),
                float(y2 - y1),
                fill=False,
                edgecolor="deepskyblue",
                linewidth=2.0,
            )
            ax0.add_patch(rect)
            if confs is not None and i < len(confs):
                ax0.text(
                    float(x1),
                    max(0.0, float(y1) - 3.0),
                    f"person {float(confs[i]):.2f}",
                    color="white",
                    fontsize=10,
                    bbox=dict(facecolor="black", alpha=0.5, pad=1, edgecolor="none"),
                )

    ax0.set_title(f"YOLO detection (people count: {yolo_res.get('people_count', 0)})", fontsize=12)
    ax0.axis("off")
    fig.colorbar(im_temp, ax=ax0, fraction=0.046, pad=0.04, label="Temperature (°C)")

    # 右：U-Net 密度圖
    im_unet = axes[1].imshow(density_map, cmap="viridis", origin="upper")
    axes[1].set_title(
        f"U-Net density map (people count: {frame_result['people_count']:.2f})", fontsize=12
    )
    axes[1].axis("off")
    cbar_unet = fig.colorbar(
        im_unet, ax=axes[1], fraction=0.046, pad=0.04, label="Density"
    )

    plt.tight_layout()

    if save_images:
        if output_dir is None:
            output_dir = CURRENT_DIR / "output_images"
        else:
            output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        ts = str(frame_result["timestamp"]).replace(":", "-").replace(" ", "_").split(".")[0]
        fname = output_dir / f"compare_frame_{frame_result['id']}_{ts}.png"
        plt.savefig(fname, dpi=150, bbox_inches="tight")
        print(f"✓ 已保存視覺化圖：{fname}")
        plt.close(fig)
    else:
        plt.show()


def main():
    parser = argparse.ArgumentParser(
        description="使用 YOLOv8 對 Supabase 即時熱影像資料做人數偵測，並與原 U-Net 結果對比"
    )

    parser.add_argument(
        "--supabase-url",
        type=str,
        default=None,
        help="Supabase 專案 URL（可選，會從 .env 或環境變數讀取）",
    )
    parser.add_argument(
        "--supabase-key",
        type=str,
        default=None,
        help="Supabase API key（可選，會從 .env 或環境變數讀取）",
    )
    parser.add_argument(
        "--session-id",
        type=str,
        required=True,
        help='會話 ID，例如 "604_windowside"',
    )
    parser.add_argument(
        "--frame-id",
        type=int,
        default=None,
        help="只測試特定 frame_id（若未指定則使用最新的資料）",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=1,
        help="要測試的最新資料筆數（僅在未指定 --frame-id 時有效）",
    )
    parser.add_argument(
        "--weights",
        type=str,
        default=None,
        help="YOLO 權重檔路徑（預設使用 yolo_training/runs/train/weights/best.pt 或 last.pt）",
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=0.25,
        help="YOLO 信心度閾值（預設 0.25）",
    )
    parser.add_argument(
        "--iou",
        type=float,
        default=0.7,
        help="YOLO NMS IoU 閾值（預設 0.7；越低越容易抑制重疊框）",
    )
    parser.add_argument(
        "--max-det",
        type=int,
        default=300,
        help="每張圖最多保留的偵測框數（預設 300）",
    )
    parser.add_argument(
        "--save-yolo",
        action="store_true",
        help="是否將 YOLO 人數結果寫回 Supabase（獨立資料表，不覆蓋原本結果）",
    )
    parser.add_argument(
        "--yolo-table",
        type=str,
        default="people_count_results_yolo",
        help="儲存 YOLO 結果的資料表名稱（預設: people_count_results_yolo）",
    )
    parser.add_argument(
        "--model-tag",
        type=str,
        default="yolov8n_best",
        help="寫回 Supabase 時的 model_tag（預設: yolov8n_best）",
    )
    parser.add_argument(
        "--visualize",
        action="store_true",
        help="顯示 YOLO 偵測與 U-Net 密度圖的對比圖",
    )
    parser.add_argument(
        "--save-images",
        action="store_true",
        help="將視覺化結果儲存到 output_images（或指定 --output-dir）",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="視覺化輸出目錄（預設 supabase_integration/output_images）",
    )

    args = parser.parse_args()

    # Supabase 設定
    supabase_url = args.supabase_url or os.getenv("SUPABASE_URL")
    supabase_key = args.supabase_key or os.getenv("SUPABASE_KEY")

    if not supabase_url:
        print("✗ 錯誤: 找不到 SUPABASE_URL，請使用 --supabase-url 或在 .env 中設定。")
        sys.exit(1)
    if not supabase_key:
        print("✗ 錯誤: 找不到 SUPABASE_KEY，請使用 --supabase-key 或在 .env 中設定。")
        sys.exit(1)

    # 初始化 Supabase 處理器（仍會使用原本的 U-Net/AutoEncoder 管線）
    print("初始化 SupabaseThermalProcessor（U-Net 管線）...")
    processor = SupabaseThermalProcessor(
        supabase_url=supabase_url,
        supabase_key=supabase_key,
        model_path=None,
    )
    print("✓ SupabaseThermalProcessor 初始化完成")

    # 載入 YOLO 模型
    model = load_yolo_model(args.weights)

    # 取得要測試的 frame 結果（原本的 U-Net 輸出）
    frame_results: List[Dict[str, Any]] = []

    if args.frame_id is not None:
        print(f"\n從 Supabase 讀取指定 frame_id={args.frame_id} 的結果 (U-Net 管線)...")
        r = processor.process_frame_by_id(args.frame_id)
        if r is None:
            print(f"✗ 找不到 frame_id={args.frame_id} 的資料")
            sys.exit(1)
        frame_results.append(r)
    else:
        print(
            f"\n從 Supabase 讀取 session='{args.session_id}' 最新 {args.limit} 筆結果 (U-Net 管線)..."
        )
        if args.limit == 1:
            r = processor.process_latest_frame(args.session_id)
            if r is None:
                print(f"✗ 找不到 session='{args.session_id}' 的資料")
                sys.exit(1)
            frame_results.append(r)
        else:
            rs = processor.process_multiple_frames(args.session_id, limit=args.limit)
            if not rs:
                print(f"✗ 找不到 session='{args.session_id}' 的資料")
                sys.exit(1)
            frame_results.extend(rs)

    # 對每一筆 frame 結果套 YOLO
    saved_count = 0
    for fr in frame_results:
        frame_id = fr["id"]
        try:
            thermal_24x32 = fetch_thermal_frame(processor, frame_id)
            yolo_res = run_yolo_on_thermal(
                model,
                thermal_24x32,
                conf=args.conf,
                iou=args.iou,
                max_det=args.max_det,
            )
            yolo_people = yolo_res["people_count"]

            print_comparison(fr, yolo_people)

            if args.visualize or args.save_images:
                visualize_comparison(
                    frame_result=fr,
                    thermal_24x32=thermal_24x32,
                    yolo_res=yolo_res,
                    save_images=args.save_images,
                    output_dir=args.output_dir,
                )

            if args.save_yolo:
                saved = save_yolo_result_to_supabase(
                    processor,
                    frame_result=fr,
                    yolo_people_count=yolo_people,
                    table_name=args.yolo_table,
                    model_tag=args.model_tag,
                )
                if saved:
                    saved_count += 1
                    print(f"  ✓ 已將 YOLO 結果寫入資料表 '{args.yolo_table}' (id={saved.get('id')})")
        except Exception as e:
            print(f"✗ 處理 frame_id={frame_id} 時發生錯誤: {e}")

    if args.save_yolo and saved_count > 0:
        print(f"\n✓ 共 {saved_count}/{len(frame_results)} 筆 YOLO 結果已寫回 Supabase。")


if __name__ == "__main__":
    main()

