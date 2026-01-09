#!/usr/bin/env python3
"""
Supabase 熱像儀人數偵測主程式
從 Supabase 讀取 MLX90641 熱像儀資料並進行人數偵測
"""

import os
import sys
import argparse
from datetime import datetime
from typing import Optional
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from PIL import Image
import cv2
from dotenv import load_dotenv

# 設置中文字體支持（Windows）
if sys.platform == 'win32':
    matplotlib.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'SimHei', 'Arial Unicode MS']
    matplotlib.rcParams['axes.unicode_minus'] = False

# 載入 .env 檔案
load_dotenv()

# 添加路徑以便導入模組
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from supabase_client import SupabaseThermalProcessor


def main():
    parser = argparse.ArgumentParser(
        description='從 Supabase 讀取熱像儀資料並進行人數偵測'
    )
    
    parser.add_argument(
        '--supabase-url',
        type=str,
        default=None,
        help='Supabase 專案 URL（可選，會從 .env 或環境變數讀取）'
    )
    
    parser.add_argument(
        '--supabase-key',
        type=str,
        default=None,
        help='Supabase API key（可選，會從 .env 或環境變數讀取）'
    )
    
    parser.add_argument(
        '--session-id',
        type=str,
        required=True,
        help='會話 ID，例如 "604_windowside"'
    )
    
    parser.add_argument(
        '--model-path',
        type=str,
        default=None,
        help='模型檔案路徑（可選，會自動尋找預設路徑）'
    )
    
    parser.add_argument(
        '--frame-id',
        type=int,
        default=None,
        help='處理特定 ID 的資料（可選）'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        default=1,
        help='處理的記錄數量（預設為 1，只處理最新的）'
    )
    
    parser.add_argument(
        '--save-results',
        action='store_true',
        help='將結果儲存回 Supabase'
    )
    
    parser.add_argument(
        '--save-density-map',
        action='store_true',
        help='同時儲存密度圖到資料庫（會增加儲存空間，但可加快後續查詢）'
    )
    
    parser.add_argument(
        '--results-table',
        type=str,
        default='people_count_results',
        help='儲存結果的資料表名稱（預設: people_count_results）'
    )
    
    parser.add_argument(
        '--visualize',
        action='store_true',
        help='生成並顯示熱影像圖和密度圖（疊加感測器範圍圖）'
    )
    
    parser.add_argument(
        '--overlay-image',
        type=str,
        default=None,
        help='疊加的圖片檔路徑（預設使用 supabase_integration/604vlab-感測器_白線去背.png）'
    )
    
    parser.add_argument(
        '--save-images',
        action='store_true',
        help='保存生成的圖像到文件（預設: 只顯示）'
    )
    
    args = parser.parse_args()
    
    # 從參數、環境變數或 .env 讀取 Supabase 設定
    supabase_url = args.supabase_url or os.getenv('SUPABASE_URL')
    supabase_key = args.supabase_key or os.getenv('SUPABASE_KEY')
    
    if not supabase_url:
        print("✗ 錯誤: 找不到 SUPABASE_URL")
        print("  請使用 --supabase-url 參數，或在 .env 檔案中設定 SUPABASE_URL")
        sys.exit(1)
    
    if not supabase_key:
        print("✗ 錯誤: 找不到 SUPABASE_KEY")
        print("  請使用 --supabase-key 參數，或在 .env 檔案中設定 SUPABASE_KEY")
        sys.exit(1)
    
    # 初始化處理器
    print("正在初始化 Supabase 處理器...")
    try:
        processor = SupabaseThermalProcessor(
            supabase_url=supabase_url,
            supabase_key=supabase_key,
            model_path=args.model_path
        )
        print("✓ 處理器初始化成功")
    except Exception as e:
        print(f"✗ 初始化失敗: {e}")
        sys.exit(1)
    
    # 處理資料
    try:
        if args.frame_id:
            # 處理特定 ID 的資料
            print(f"\n正在處理 ID {args.frame_id} 的資料...")
            result = processor.process_frame_by_id(args.frame_id)
            
            if result:
                print_result(result)
                
                if args.save_results:
                    saved = processor.save_results_to_supabase(
                        result,
                        table_name=args.results_table,
                        save_density_map=args.save_density_map
                    )
                    if saved:
                        density_info = "（含密度圖）" if args.save_density_map else "（不含密度圖）"
                        print(f"\n✓ 結果已儲存到 Supabase 資料表 '{args.results_table}' {density_info}")
                
                if args.visualize:
                    visualize_results(processor, result, args.overlay_image, args.save_images, args.frame_id)
            else:
                print(f"✗ 找不到 ID {args.frame_id} 的資料")
        
        else:
            # 處理最新的資料
            print(f"\n正在處理 session '{args.session_id}' 的最新 {args.limit} 筆資料...")
            
            if args.limit == 1:
                result = processor.process_latest_frame(args.session_id)
                if result:
                    print_result(result)
                    
                    if args.save_results:
                        saved = processor.save_results_to_supabase(
                            result,
                            table_name=args.results_table,
                            save_density_map=args.save_density_map
                        )
                        if saved:
                            density_info = "（含密度圖）" if args.save_density_map else "（不含密度圖）"
                            print(f"\n✓ 結果已儲存到 Supabase 資料表 '{args.results_table}' {density_info}")
                    
                    if args.visualize:
                        visualize_results(processor, result, args.overlay_image, args.save_images, result['id'])
                else:
                    print(f"✗ 找不到 session '{args.session_id}' 的資料")
            else:
                results = processor.process_multiple_frames(
                    args.session_id,
                    limit=args.limit
                )
                
                if results:
                    print(f"\n處理了 {len(results)} 筆資料：\n")
                    for i, result in enumerate(results, 1):
                        print(f"--- 記錄 {i} ---")
                        print_result(result)
                        print()
                    
                    if args.save_results:
                        saved_count = 0
                        for result in results:
                            saved = processor.save_results_to_supabase(
                                result,
                                table_name=args.results_table,
                                save_density_map=args.save_density_map
                            )
                            if saved:
                                saved_count += 1
                        density_info = "（含密度圖）" if args.save_density_map else "（不含密度圖）"
                        print(f"✓ {saved_count}/{len(results)} 筆結果已儲存到 Supabase {density_info}")
                else:
                    print(f"✗ 找不到 session '{args.session_id}' 的資料")
    
    except Exception as e:
        print(f"✗ 處理資料時發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def print_result(result: dict):
    """列印處理結果"""
    print("\n" + "="*50)
    print("處理結果")
    print("="*50)
    print(f"記錄 ID:        {result['id']}")
    print(f"會話 ID:        {result['session_id']}")
    print(f"時間戳記:       {result['timestamp']}")
    print(f"偵測人數:       {result['people_count']:.2f}")
    print(f"偵測人數(整數): {result['people_count_rounded']}")
    print(f"密度圖總和:     {result.get('density_map_sum', 'N/A'):.2f}")
    print(f"密度圖形狀:     {result['density_map_shape']}")
    print(f"原始資料長度:   {result['raw_data_length']}")
    print("="*50)


def _draw_room_layout(ax, width: int, height: int, alpha: float = 0.6) -> None:
    """
    在目前的座標系上，以程式畫出 604 教室的白線平面圖。

    座標系與熱圖/密度圖一致：x ∈ [0, width], y ∈ [0, height]。

    你提供的實際座標（單位約為 cm）：
    - 可偵測範圍：x = 120 ~ 600, y = 40 ~ 340
    - 中間橫條（左半）：(210,180) (390,180) (210,240) (390,240)
    - 中間橫條（右半）：(390,180) (570,180) (390,240) (570,240)
    - 由中間橫條左半往上的兩條直線：
        (210,240) -> (210,340), (270,240) -> (270,340)
    - 下方橫線： (120,80) -> (524,80)
    - 下方直線： (524,80) -> (524,40)
      右下角起點約為 (120,40)
    """

    # 1. 實際座標 (cm) 轉為 圖像座標 (pixel)
    X_MIN, X_MAX = 120.0, 600.0
    Y_MIN, Y_MAX = 40.0, 340.0

    def to_px(x_cm: float, y_cm: float) -> tuple[float, float]:
        """將實際座標 (cm) 映射到目前圖像的像素座標。"""
        # 正規化到 0~1
        x_norm = (x_cm - X_MIN) / (X_MAX - X_MIN)
        y_norm = (y_cm - Y_MIN) / (Y_MAX - Y_MIN)
        # 映射到 0~width / 0~height
        x_px = x_norm * float(width)
        y_px = y_norm * float(height)
        return x_px, y_px

    def rect_cm(x0: float, y0: float, x1: float, y1: float, lw: float = 0.6) -> None:
        """以實際座標定義矩形，畫在目前座標系上。"""
        px0, py0 = to_px(x0, y0)
        px1, py1 = to_px(x1, y1)
        xs = [px0, px1, px1, px0, px0]
        ys = [py0, py0, py1, py1, py0]
        ax.plot(xs, ys, color="white", linewidth=lw, alpha=alpha)

    def line_cm(x0: float, y0: float, x1: float, y1: float, lw: float = 0.6) -> None:
        """以實際座標定義線段，畫在目前座標系上。"""
        px0, py0 = to_px(x0, y0)
        px1, py1 = to_px(x1, y1)
        ax.plot([px0, px1], [py0, py1], color="white", linewidth=lw, alpha=alpha)

    # 2. 依照你提供的實際座標來畫

    # 中間橫條（左半） #(210,180) (390,180) (210,240) (390,240)
    rect_cm(210, 180, 390, 240)

    # 中間橫條（右半）(390,180) (570,180) (390,240) (570,240)
    rect_cm(390, 180, 570, 240)

    # 中間橫條左半往上的兩條直線 (210,180)->(210,340), (270,180)->(270,340)
    line_cm(210, 240, 210, 340)
    line_cm(270, 240, 270, 340)

    # 下方橫線 (120,80) -> (524,80)
    line_cm(120, 80, 524, 80)

    # 下方直線 (524,80) -> (524,40)
    line_cm(524, 80, 524, 40)

    # （可選）如果你希望把可偵測邊界也畫出來，可以打開這一行：
    # rect_cm(120, 0, 600, 340, lw=0.5)

def visualize_results(
    processor: SupabaseThermalProcessor,
    result: dict,
    overlay_image_path: Optional[str] = None,
    save_images: bool = False,
    frame_id: Optional[int] = None
):
    """
    生成並顯示熱影像圖和密度圖，疊加感測器範圍圖
    
    Args:
        processor: SupabaseThermalProcessor 實例
        result: 處理結果字典
        overlay_image_path: 疊加圖片路徑（None 則使用預設路徑）
        save_images: 是否保存圖像
        frame_id: 幀 ID（用於保存文件名）
    """
    try:
        # 1. 獲取原始熱影像數據（12x16）
        frame_response = processor.supabase.table('thermal_frames')\
            .select('data')\
            .eq('id', result['id'])\
            .execute()
        
        if not frame_response.data:
            print("✗ 無法獲取原始熱影像數據")
            return
        
        # 解析原始數據
        raw_data = processor.parse_data_array(frame_response.data[0]['data'])
        thermal_2d = raw_data.reshape(12, 16)
        
        # 上採樣到 24x32（與密度圖相同尺寸）
        thermal_upsampled = cv2.resize(
            thermal_2d,
            (32, 24),  # (width, height)
            interpolation=cv2.INTER_CUBIC
        )
        
        # #region agent log
        with open(r'c:\Users\a0903\Documents\CAE\thermo-presence\.cursor\debug.log', 'a', encoding='utf-8') as f:
            import json, time
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"main.py:349","message":"上採樣後的熱影像圖形狀","data":{"shape":list(thermal_upsampled.shape)},"timestamp":int(time.time()*1000)}) + '\n')
        # #endregion
        
        # 2. 獲取密度圖（24x32）
        density_map = result.get('density_map')
        if density_map is None:
            print("✗ 無法獲取密度圖數據")
            return

        # #region agent log
        with open(r'c:\Users\a0903\Documents\CAE\thermo-presence\.cursor\debug.log', 'a', encoding='utf-8') as f:
            import json, time
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"main.py:356","message":"密度圖形狀","data":{"shape":list(density_map.shape)},"timestamp":int(time.time()*1000)}) + '\n')
        # #endregion

        # 水平翻轉熱影像圖和密度圖（左右翻轉），但線框位置不變
        thermal_upsampled_flipped = np.fliplr(thermal_upsampled)
        density_map_flipped = np.fliplr(density_map)
        
        # #region agent log
        with open(r'c:\Users\a0903\Documents\CAE\thermo-presence\.cursor\debug.log', 'a', encoding='utf-8') as f:
            import json, time
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"main.py:363","message":"翻轉後的形狀","data":{"thermal_shape":list(thermal_upsampled_flipped.shape),"density_shape":list(density_map_flipped.shape)},"timestamp":int(time.time()*1000)}) + '\n')
        # #endregion

        # 熱影像圖和密度圖的尺寸 (height, width) = (24, 32)
        thermal_height, thermal_width = thermal_upsampled_flipped.shape
        density_height, density_width = density_map_flipped.shape
        
        # 4. 創建圖像
        fig, axes = plt.subplots(1, 2, figsize=(16, 8))
        
        # 4.1 熱影像圖
        ax1 = axes[0]
        # 底層：熱影像圖（使用翻轉後的數據）
        im1 = ax1.imshow(
            thermal_upsampled_flipped, 
            cmap='viridis', 
            origin='upper',
            extent=(0, thermal_width, 0, thermal_height),
            aspect='equal'
        )
        # 上層：以程式畫出的教室線框
        _draw_room_layout(ax1, thermal_width, thermal_height, alpha=0.7)
        
        ax1.set_title(f'熱影像圖 (Frame ID: {result["id"]})', fontsize=14, fontweight='bold')
        ax1.set_xlabel('Width (pixels)')
        ax1.set_ylabel('Height (pixels)')
        ax1.set_aspect('equal', adjustable='box')
        plt.colorbar(im1, ax=ax1, label='Temperature (°C)')
        
        # 4.2 密度圖
        ax2 = axes[1]
        # 底層：密度圖（使用翻轉後的數據）
        im2 = ax2.imshow(
            density_map_flipped,
            cmap='viridis',
            origin='upper',
            extent=(0, density_width, 0, density_height),
            aspect='equal'
        )
        _draw_room_layout(ax2, density_width, density_height, alpha=0.7)
        
        ax2.set_title(f'密度圖 (人數: {result["people_count"]:.2f})', fontsize=14, fontweight='bold')
        ax2.set_xlabel('Width (pixels)')
        ax2.set_ylabel('Height (pixels)')
        ax2.set_aspect('equal', adjustable='box')
        plt.colorbar(im2, ax=ax2, label='Density')
        
        plt.tight_layout()
        
        # 5. 保存或顯示
        if save_images:
            if frame_id is None:
                frame_id = result['id']
            timestamp_str = result['timestamp'].replace(':', '-').replace(' ', '_').split('.')[0]
            output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output_images')
            os.makedirs(output_dir, exist_ok=True)
            
            thermal_path = os.path.join(output_dir, f'thermal_frame_{frame_id}_{timestamp_str}.png')
            density_path = os.path.join(output_dir, f'density_frame_{frame_id}_{timestamp_str}.png')
            combined_path = os.path.join(output_dir, f'combined_frame_{frame_id}_{timestamp_str}.png')
            
            # 保存單獨的圖像
            fig1, ax1 = plt.subplots(figsize=(8, 6))
            # 底層：熱影像圖（使用翻轉後的數據）
            im1 = ax1.imshow(
                thermal_upsampled_flipped,
                cmap='viridis',
                origin='upper',
                extent=(0, thermal_width, 0, thermal_height),
                aspect='equal'
            )
            _draw_room_layout(ax1, thermal_width, thermal_height, alpha=0.7)
            ax1.set_title(f'熱影像圖 (Frame ID: {frame_id})', fontsize=14, fontweight='bold')
            ax1.set_xlabel('Width (pixels)')
            ax1.set_ylabel('Height (pixels)')
            ax1.set_aspect('equal', adjustable='box')
            plt.colorbar(im1, ax=ax1, label='Temperature (°C)')
            plt.tight_layout()
            plt.savefig(thermal_path, dpi=150, bbox_inches='tight')
            plt.close(fig1)
            
            fig2, ax2 = plt.subplots(figsize=(8, 6))
            # 底層：密度圖（使用翻轉後的數據）
            im2 = ax2.imshow(
                density_map_flipped,
                cmap='viridis',
                origin='upper',
                extent=(0, density_width, 0, density_height),
                aspect='equal'
            )
            _draw_room_layout(ax2, density_width, density_height, alpha=0.7)
            ax2.set_title(f'密度圖 (人數: {result["people_count"]:.2f})', fontsize=14, fontweight='bold')
            ax2.set_xlabel('Width (pixels)')
            ax2.set_ylabel('Height (pixels)')
            ax2.set_aspect('equal', adjustable='box')
            plt.colorbar(im2, ax=ax2, label='Density')
            plt.tight_layout()
            plt.savefig(density_path, dpi=150, bbox_inches='tight')
            plt.close(fig2)
            
            # 保存合併圖像
            plt.savefig(combined_path, dpi=150, bbox_inches='tight')
            plt.close(fig)
            
            print(f"\n✓ 圖像已保存:")
            print(f"  - 熱影像圖: {thermal_path}")
            print(f"  - 密度圖: {density_path}")
            print(f"  - 合併圖: {combined_path}")
        else:
            plt.show()
            print("\n✓ 圖像已顯示（關閉窗口以繼續）")
    
    except Exception as e:
        print(f"✗ 生成圖像時發生錯誤: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()

