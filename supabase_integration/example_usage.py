"""
Supabase 整合使用範例
"""

import os
import numpy as np
from dotenv import load_dotenv
from supabase_client import SupabaseThermalProcessor

# 載入 .env 檔案
load_dotenv()


def example_basic_usage():
    """基本使用範例"""
    
    # 從 .env 檔案讀取 Supabase 連線資訊
    SESSION_ID = '604_windowside'
    
    # 初始化處理器（會自動從 .env 讀取 SUPABASE_URL 和 SUPABASE_KEY）
    processor = SupabaseThermalProcessor()
    
    # 處理最新的資料
    result = processor.process_latest_frame(SESSION_ID)
    
    if result:
        print(f"時間: {result['timestamp']}")
        print(f"偵測到人數: {result['people_count']:.2f}")
        print(f"偵測到人數(整數): {result['people_count_rounded']}")
    else:
        print("找不到資料")


def example_process_multiple_frames():
    """處理多個資料的範例"""
    
    SESSION_ID = '604_windowside'
    
    # 初始化處理器（會自動從 .env 讀取設定）
    processor = SupabaseThermalProcessor()
    
    # 處理最近 10 筆資料
    results = processor.process_multiple_frames(
        session_id=SESSION_ID,
        limit=10
    )
    
    print(f"處理了 {len(results)} 筆資料")
    for result in results:
        print(f"ID {result['id']}: {result['people_count']:.2f} 人")


def example_process_specific_frame():
    """處理特定 ID 的資料範例"""
    
    FRAME_ID = 20082  # 您提供的範例 ID
    
    # 初始化處理器（會自動從 .env 讀取設定）
    processor = SupabaseThermalProcessor()
    
    result = processor.process_frame_by_id(FRAME_ID)
    
    if result:
        print(f"ID {result['id']}: {result['people_count']:.2f} 人")
    else:
        print("找不到資料")


def example_save_with_density_map():
    """儲存結果並包含密度圖的範例"""
    
    SESSION_ID = '604_windowside'
    processor = SupabaseThermalProcessor()
    
    # 處理資料
    result = processor.process_latest_frame(SESSION_ID)
    
    if result:
        # 儲存結果（包含密度圖）
        saved = processor.save_results_to_supabase(
            result,
            save_density_map=True  # 儲存密度圖
        )
        
        if saved:
            print("✓ 結果已儲存（包含密度圖）")
        else:
            print("✗ 儲存失敗")


def example_get_density_map():
    """按需獲取密度圖的範例"""
    
    FRAME_ID = 31768
    
    processor = SupabaseThermalProcessor()
    
    # 獲取密度圖（會自動檢查是否有儲存，沒有則重新計算）
    density_map = processor.get_density_map_for_frame(
        FRAME_ID,
        cache_if_missing=True  # 如果沒有儲存，計算後自動快取
    )
    
    if density_map is not None:
        print(f"密度圖形狀: {density_map.shape}")
        print(f"密度圖總和: {np.sum(density_map):.2f}")
        print(f"計算出的人數: {np.sum(density_map) / 52.0:.2f}")
    else:
        print("找不到資料")


def example_direct_data_processing():
    """直接處理資料陣列的範例（不從 Supabase 讀取）"""
    
    from frame_processor_mlx90641 import FrameProcessorMLX90641
    
    # 初始化處理器
    fp = FrameProcessorMLX90641()
    
    # 範例資料（您提供的 Supabase 資料格式）
    data_str = '["21.5853","21.1291","20.9217","20.7298","20.8028","20.7284","20.6816","20.8559","20.6559","20.9017","20.9351","20.9916","20.8925","21.0526","20.93","21.2715","21.1319","21.1657","20.9259","20.9508","20.8245","20.7739","20.8109","20.7994","20.8287","20.8529","20.8546","20.9697","21.0756","20.9977","20.9672","21.3692","21.1864","21.1061","21.1989","20.9881","20.9575","20.8682","20.9315","20.8347","20.8724","20.8423","20.939","20.9297","21.2216","21.1569","21.2615","21.3992","21.3915","21.3635","21.2138","21.2179","21.1623","20.9405","20.8868","20.8644","20.8745","20.9464","20.8915","21.0374","21.0559","21.1746","21.3897","21.255","21.1609","21.1805","21.3465","21.0551","21.1555","20.965","20.8426","20.9015","20.9676","20.9216","21.0204","21.0732","21.0506","21.0685","21.199","21.4938","21.1544","21.025","21.0752","21.0169","21.0051","20.7913","20.8838","20.8993","20.9381","20.9453","20.9794","21.0363","20.9268","21.2028","21.4016","21.4142","21.2544","21.1695","21.0792","20.8178","20.8414","20.7522","20.7787","20.8134","20.9645","20.9174","20.9734","20.9816","21.1264","21.1191","21.1211","21.3831","21.049","20.8997","21.0191","20.8757","20.7755","20.768","20.7009","20.805","20.8699","20.8807","20.9555","20.9188","21.016","21.2223","21.3771","21.35","20.9575","20.9165","21.0075","21.0585","20.9115","20.7405","20.8151","20.8448","20.8176","20.9646","21.0296","20.9707","21.0448","21.412","21.3764","21.3892","21.4794","21.0075","20.8933","20.8618","20.6886","20.832","20.8575","20.6807","20.9429","21.0259","21.1874","21.1878","21.4215","21.3472","21.5709","21.5745","21.0988","20.6786","21.0014","20.9035","20.7144","20.7257","20.7316","20.9539","20.9723","21.0725","21.2787","21.6846","21.9265","21.6159","21.6933","21.6455","20.6283","20.4801","20.6918","20.7825","20.7241","20.8508","20.7797","20.7765","21.0616","21.1285","21.3462","21.9519","21.8356","21.5983","21.3734","21.644"]'
    
    import json
    data_array = json.loads(data_str)
    
    # 處理資料
    density_map = fp.process_frame(data_array)
    people_count = fp.get_people_count_on_latest_frame()
    
    print(f"偵測到人數: {people_count:.2f}")
    print(f"密度圖形狀: {density_map.shape}")


if __name__ == '__main__':
    # 執行範例
    print("=== 範例 1: 直接處理資料 ===")
    example_direct_data_processing()
    
    print("\n=== 範例 2: 基本 Supabase 使用 ===")
    # 需要設定環境變數 SUPABASE_URL 和 SUPABASE_KEY
    # example_basic_usage()

