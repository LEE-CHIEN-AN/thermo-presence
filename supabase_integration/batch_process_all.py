#!/usr/bin/env python3
"""
批次處理所有 thermal_frames 資料
將所有現存的資料進行人數計算並儲存到 people_count_results 表
"""

import os
import sys
import time
from typing import List, Dict, Any
from dotenv import load_dotenv

# 載入 .env 檔案
load_dotenv()

# 添加路徑以便導入模組
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from supabase_client import SupabaseThermalProcessor

# Supabase 每次查詢的最大筆數
SUPABASE_MAX_LIMIT = 1000


def get_total_count(processor: SupabaseThermalProcessor, session_id: str = None) -> int:
    """
    獲取總資料筆數
    
    Args:
        processor: Supabase 處理器
        session_id: 可選的 session_id 過濾條件
    
    Returns:
        總筆數
    """
    try:
        query = processor.supabase.table('thermal_frames').select('id', count='exact')
        
        if session_id:
            query = query.eq('session_id', session_id)
        
        response = query.limit(1).execute()
        return response.count if hasattr(response, 'count') and response.count is not None else 0
    except Exception as e:
        print(f"警告: 無法獲取總筆數: {e}")
        return 0


def get_frames_batch(
    processor: SupabaseThermalProcessor,
    offset: int,
    limit: int,
    session_id: str = None
) -> List[Dict[str, Any]]:
    """
    批次獲取 thermal_frames 資料
    
    Args:
        processor: Supabase 處理器
        offset: 偏移量
        limit: 每批筆數（最多 1000）
        session_id: 可選的 session_id 過濾條件
    
    Returns:
        資料列表
    """
    try:
        query = processor.supabase.table('thermal_frames')\
            .select('id, session_id, ts, data')\
            .order('id', desc=False)  # 按 ID 升序排列，確保順序一致
        
        if session_id:
            query = query.eq('session_id', session_id)
        
        # Supabase Python 客戶端使用 range 方法進行分頁
        # range(start, end) 包含 start 和 end
        response = query.range(offset, offset + limit - 1).execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"錯誤: 獲取資料批次時發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        return []


def check_already_processed(processor: SupabaseThermalProcessor, frame_id: int) -> bool:
    """
    檢查該 frame 是否已經處理過
    
    Args:
        processor: Supabase 處理器
        frame_id: frame ID
    
    Returns:
        是否已處理
    """
    try:
        response = processor.supabase.table('people_count_results')\
            .select('id')\
            .eq('frame_id', frame_id)\
            .limit(1)\
            .execute()
        return len(response.data) > 0
    except Exception:
        return False


def process_batch(
    processor: SupabaseThermalProcessor,
    frames: List[Dict[str, Any]],
    save_density_map: bool = False,
    skip_existing: bool = True
) -> Dict[str, int]:
    """
    處理一批資料
    
    Args:
        processor: Supabase 處理器
        frames: 要處理的資料列表
        save_density_map: 是否儲存密度圖
        skip_existing: 是否跳過已處理的資料
    
    Returns:
        統計資訊字典
    """
    stats = {
        'total': len(frames),
        'processed': 0,
        'saved': 0,
        'skipped': 0,
        'errors': 0
    }
    
    for frame in frames:
        frame_id = frame['id']
        
        # 檢查是否已處理
        if skip_existing and check_already_processed(processor, frame_id):
            stats['skipped'] += 1
            continue
        
        try:
            # 解析資料陣列
            data_array = processor.parse_data_array(frame['data'])
            
            # 處理幀
            density_map = processor.frame_processor.process_frame(data_array)
            people_count = processor.frame_processor.get_people_count_on_latest_frame()
            
            # 準備結果
            result = {
                'id': frame_id,
                'session_id': frame['session_id'],
                'timestamp': frame['ts'],
                'people_count': float(people_count),
                'people_count_rounded': int(round(people_count)),
                'density_map': density_map,
                'density_map_sum': float(density_map.sum()),
                'density_map_shape': density_map.shape,
                'raw_data_length': len(data_array)
            }
            
            # 儲存結果
            saved = processor.save_results_to_supabase(
                result,
                save_density_map=save_density_map
            )
            
            if saved:
                stats['saved'] += 1
            else:
                stats['errors'] += 1
            
            stats['processed'] += 1
            
        except Exception as e:
            print(f"錯誤: 處理 frame_id={frame_id} 時發生錯誤: {e}")
            stats['errors'] += 1
            continue
    
    return stats


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='批次處理所有 thermal_frames 資料並儲存到 people_count_results'
    )
    
    parser.add_argument(
        '--session-id',
        type=str,
        default=None,
        help='只處理指定 session_id 的資料（可選）'
    )
    
    parser.add_argument(
        '--save-density-map',
        action='store_true',
        help='同時儲存密度圖到資料庫（會增加儲存空間）'
    )
    
    parser.add_argument(
        '--skip-existing',
        action='store_true',
        default=True,
        help='跳過已經處理過的資料（預設: True）'
    )
    
    parser.add_argument(
        '--no-skip-existing',
        action='store_false',
        dest='skip_existing',
        help='不跳過已處理的資料（會重新處理）'
    )
    
    parser.add_argument(
        '--batch-size',
        type=int,
        default=1000,
        help='每批處理的筆數（預設: 1000，Supabase 限制）'
    )
    
    parser.add_argument(
        '--max-batches',
        type=int,
        default=None,
        help='最多處理的批次數（可選，用於測試）'
    )
    
    args = parser.parse_args()
    
    # 驗證 batch_size
    if args.batch_size > SUPABASE_MAX_LIMIT:
        print(f"警告: batch_size ({args.batch_size}) 超過 Supabase 限制 ({SUPABASE_MAX_LIMIT})，將使用 {SUPABASE_MAX_LIMIT}")
        args.batch_size = SUPABASE_MAX_LIMIT
    
    # 初始化處理器
    print("正在初始化 Supabase 處理器...")
    try:
        processor = SupabaseThermalProcessor()
        print("✓ 處理器初始化成功")
    except Exception as e:
        print(f"✗ 初始化失敗: {e}")
        sys.exit(1)
    
    # 獲取總筆數
    print("\n正在獲取資料統計...")
    total_count = get_total_count(processor, args.session_id)
    
    if total_count == 0:
        print("✗ 找不到任何資料")
        sys.exit(1)
    
    session_info = f" (session_id: {args.session_id})" if args.session_id else ""
    print(f"✓ 找到 {total_count} 筆資料{session_info}")
    
    # 計算總批次數
    total_batches = (total_count + args.batch_size - 1) // args.batch_size
    
    if args.max_batches:
        total_batches = min(total_batches, args.max_batches)
        print(f"限制處理批次數: {args.max_batches}")
    
    print(f"\n將分 {total_batches} 批處理，每批 {args.batch_size} 筆")
    print(f"跳過已處理: {'是' if args.skip_existing else '否'}")
    print(f"儲存密度圖: {'是' if args.save_density_map else '否'}")
    print("\n開始處理...\n")
    
    # 統計資訊
    overall_stats = {
        'total_frames': 0,
        'processed': 0,
        'saved': 0,
        'skipped': 0,
        'errors': 0
    }
    
    start_time = time.time()
    
    # 批次處理
    for batch_num in range(total_batches):
        offset = batch_num * args.batch_size
        
        print(f"[批次 {batch_num + 1}/{total_batches}] 處理第 {offset + 1} 到 {min(offset + args.batch_size, total_count)} 筆...")
        
        # 獲取資料批次
        frames = get_frames_batch(processor, offset, args.batch_size, args.session_id)
        
        if not frames:
            print(f"  警告: 批次 {batch_num + 1} 沒有資料，跳過")
            continue
        
        # 處理批次
        batch_stats = process_batch(
            processor,
            frames,
            save_density_map=args.save_density_map,
            skip_existing=args.skip_existing
        )
        
        # 更新總統計
        overall_stats['total_frames'] += batch_stats['total']
        overall_stats['processed'] += batch_stats['processed']
        overall_stats['saved'] += batch_stats['saved']
        overall_stats['skipped'] += batch_stats['skipped']
        overall_stats['errors'] += batch_stats['errors']
        
        # 顯示批次結果
        print(f"  ✓ 處理: {batch_stats['processed']}, "
              f"儲存: {batch_stats['saved']}, "
              f"跳過: {batch_stats['skipped']}, "
              f"錯誤: {batch_stats['errors']}")
        
        # 顯示進度
        progress = ((batch_num + 1) / total_batches) * 100
        print(f"  進度: {progress:.1f}% ({batch_num + 1}/{total_batches} 批次)")
        
        # 避免請求過於頻繁（可選）
        if batch_num < total_batches - 1:  # 最後一批不需要等待
            time.sleep(0.1)
    
    # 顯示最終統計
    elapsed_time = time.time() - start_time
    
    print("\n" + "="*60)
    print("處理完成！")
    print("="*60)
    print(f"總資料筆數:     {overall_stats['total_frames']}")
    print(f"已處理:         {overall_stats['processed']}")
    print(f"成功儲存:       {overall_stats['saved']}")
    print(f"跳過（已存在）: {overall_stats['skipped']}")
    print(f"錯誤:           {overall_stats['errors']}")
    print(f"總耗時:         {elapsed_time:.2f} 秒")
    
    if overall_stats['processed'] > 0:
        avg_time = elapsed_time / overall_stats['processed']
        print(f"平均每筆:       {avg_time:.3f} 秒")
    
    print("="*60)


if __name__ == '__main__':
    main()

