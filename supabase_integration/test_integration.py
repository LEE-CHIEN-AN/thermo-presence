#!/usr/bin/env python3
"""
測試 Supabase 整合功能
"""

import json
import numpy as np
from frame_processor_mlx90641 import FrameProcessorMLX90641


def test_frame_processor():
    """測試 FrameProcessor 基本功能"""
    print("=" * 60)
    print("測試 1: FrameProcessor 基本功能")
    print("=" * 60)
    
    try:
        # 初始化處理器
        print("\n正在初始化 FrameProcessor...")
        fp = FrameProcessorMLX90641()
        print("✓ FrameProcessor 初始化成功")
        
        # 測試資料（您提供的 Supabase 資料格式）
        test_data_str = '["21.5853","21.1291","20.9217","20.7298","20.8028","20.7284","20.6816","20.8559","20.6559","20.9017","20.9351","20.9916","20.8925","21.0526","20.93","21.2715","21.1319","21.1657","20.9259","20.9508","20.8245","20.7739","20.8109","20.7994","20.8287","20.8529","20.8546","20.9697","21.0756","20.9977","20.9672","21.3692","21.1864","21.1061","21.1989","20.9881","20.9575","20.8682","20.9315","20.8347","20.8724","20.8423","20.939","20.9297","21.2216","21.1569","21.2615","21.3992","21.3915","21.3635","21.2138","21.2179","21.1623","20.9405","20.8868","20.8644","20.8745","20.9464","20.8915","21.0374","21.0559","21.1746","21.3897","21.255","21.1609","21.1805","21.3465","21.0551","21.1555","20.965","20.8426","20.9015","20.9676","20.9216","21.0204","21.0732","21.0506","21.0685","21.199","21.4938","21.1544","21.025","21.0752","21.0169","21.0051","20.7913","20.8838","20.8993","20.9381","20.9453","20.9794","21.0363","20.9268","21.2028","21.4016","21.4142","21.2544","21.1695","21.0792","20.8178","20.8414","20.7522","20.7787","20.8134","20.9645","20.9174","20.9734","20.9816","21.1264","21.1191","21.1211","21.3831","21.049","20.8997","21.0191","20.8757","20.7755","20.768","20.7009","20.805","20.8699","20.8807","20.9555","20.9188","21.016","21.2223","21.3771","21.35","20.9575","20.9165","21.0075","21.0585","20.9115","20.7405","20.8151","20.8448","20.8176","20.9646","21.0296","20.9707","21.0448","21.412","21.3764","21.3892","21.4794","21.0075","20.8933","20.8618","20.6886","20.832","20.8575","20.6807","20.9429","21.0259","21.1874","21.1878","21.4215","21.3472","21.5709","21.5745","21.0988","20.6786","21.0014","20.9035","20.7144","20.7257","20.7316","20.9539","20.9723","21.0725","21.2787","21.6846","21.9265","21.6159","21.6933","21.6455","20.6283","20.4801","20.6918","20.7825","20.7241","20.8508","20.7797","20.7765","21.0616","21.1285","21.3462","21.9519","21.8356","21.5983","21.3734","21.644"]'
        
        # 解析資料
        print("\n正在解析測試資料...")
        data_array = json.loads(test_data_str)
        print(f"✓ 資料解析成功，長度: {len(data_array)}")
        
        # 驗證資料長度
        if len(data_array) != 192:
            print(f"✗ 錯誤: 資料長度應為 192，但得到 {len(data_array)}")
            return False
        
        # 處理資料
        print("\n正在處理資料...")
        density_map = fp.process_frame(data_array)
        people_count = fp.get_people_count_on_latest_frame()
        
        print(f"✓ 處理成功")
        print(f"\n結果:")
        print(f"  密度圖形狀: {density_map.shape}")
        print(f"  偵測到人數: {people_count:.2f}")
        print(f"  偵測到人數(整數): {int(round(people_count))}")
        
        # 驗證輸出形狀
        if density_map.shape != (24, 32):
            print(f"✗ 錯誤: 密度圖形狀應為 (24, 32)，但得到 {density_map.shape}")
            return False
        
        print("\n✓ 所有測試通過！")
        return True
        
    except FileNotFoundError as e:
        print(f"\n✗ 錯誤: 找不到模型檔案")
        print(f"  請確保模型檔案存在於以下位置之一:")
        print(f"  - ../data_collection/src/trained_model/unet_v2_cpu1")
        print(f"  - ../data_collection/src/trained_model/unet_gauss_model_cpu1")
        print(f"  - ../data_collection/src/trained_model/unet_gauss_model_gpu1")
        print(f"\n  或使用 --model-path 參數指定模型路徑")
        return False
        
    except Exception as e:
        print(f"\n✗ 錯誤: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_data_parsing():
    """測試資料解析功能"""
    print("\n" + "=" * 60)
    print("測試 2: 資料解析功能")
    print("=" * 60)
    
    from supabase_client import SupabaseThermalProcessor
    
    # 創建一個臨時的處理器實例（不需要 Supabase 連線）
    try:
        # 測試資料解析
        test_data_str = '["21.5853","21.1291","20.9217"]'
        # 這會失敗因為長度不對，但我們只是想測試解析功能
        
        # 正確長度的測試資料（前 192 個值）
        full_data = ['21.5853'] * 192
        
        processor = SupabaseThermalProcessor(
            supabase_url="dummy",
            supabase_key="dummy"
        )
        
        # 測試解析
        try:
            data_array = processor.parse_data_array(json.dumps(full_data))
            print(f"✓ 資料解析成功，長度: {len(data_array)}")
            return True
        except Exception as e:
            print(f"✗ 解析錯誤: {e}")
            return False
            
    except Exception as e:
        print(f"✗ 錯誤: {e}")
        return False


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("Supabase 整合測試")
    print("=" * 60)
    
    # 執行測試
    test1_passed = test_frame_processor()
    
    # 注意：test_data_parsing 需要 Supabase 連線，所以跳過
    # test2_passed = test_data_parsing()
    
    print("\n" + "=" * 60)
    if test1_passed:
        print("✓ 基本功能測試通過！")
        print("\n下一步:")
        print("1. 設定 Supabase URL 和 API key")
        print("2. 執行: python main.py --supabase-url <url> --supabase-key <key> --session-id <session>")
    else:
        print("✗ 測試失敗，請檢查錯誤訊息")
    print("=" * 60 + "\n")

