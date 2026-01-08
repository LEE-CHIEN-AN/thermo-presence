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
from dotenv import load_dotenv

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


if __name__ == '__main__':
    main()

