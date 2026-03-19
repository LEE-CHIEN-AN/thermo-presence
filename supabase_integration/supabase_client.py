"""
Supabase 客戶端整合模組
用於從 Supabase 讀取熱像儀資料並進行人數偵測
"""

import os
import sys
import json
import pickle
import gzip
import base64
import time
from typing import Optional, List, Dict, Any
from datetime import datetime
import numpy as np
from supabase import create_client, Client
from dotenv import load_dotenv
import httpx

# Ensure supabase_integration directory is on path for imports
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from frame_processor_mlx90641 import FrameProcessorMLX90641

# 載入 .env 檔案
load_dotenv()


def retry_supabase_query(max_retries: int = 3, delay: float = 1.0):
    """
    重試裝飾器，用於處理 Supabase 連接錯誤
    
    Args:
        max_retries: 最大重試次數
        delay: 重試延遲（秒）
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (httpx.ReadError, httpx.RemoteProtocolError, httpx.ConnectError, httpx.TimeoutException) as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        time.sleep(delay * (attempt + 1))  # 指數退避
                        continue
                    else:
                        raise RuntimeError(f"Supabase 連接失敗（已重試 {max_retries} 次）: {e}")
                except Exception as e:
                    # 非連接錯誤，直接拋出
                    raise
            if last_exception:
                raise last_exception
        return wrapper
    return decorator


class SupabaseThermalProcessor:
    """
    Supabase 熱像儀資料處理器
    """
    
    def __init__(
        self,
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None,
        model_path: Optional[str] = None
    ):
        """
        初始化 Supabase 處理器
        
        Args:
            supabase_url: Supabase 專案 URL（可選，會從環境變數或 .env 讀取）
            supabase_key: Supabase API key（可選，會從環境變數或 .env 讀取）
            model_path: 模型檔案路徑（可選）
        """
        # 從參數、環境變數或 .env 讀取設定
        supabase_url = supabase_url or os.getenv('SUPABASE_URL')
        supabase_key = supabase_key or os.getenv('SUPABASE_KEY')
        
        if not supabase_url:
            raise ValueError(
                "找不到 SUPABASE_URL。請提供參數、設定環境變數或在 .env 檔案中設定。"
            )
        
        if not supabase_key:
            raise ValueError(
                "找不到 SUPABASE_KEY。請提供參數、設定環境變數或在 .env 檔案中設定。"
            )
        
        # 初始化 Supabase 客戶端
        self.supabase: Client = create_client(supabase_url, supabase_key)
        
        # 初始化模型處理器
        self.frame_processor = FrameProcessorMLX90641(model_path=model_path)
    
    def parse_data_array(self, data_array_str: str) -> np.ndarray:
        """
        解析 Supabase 的 float4[] 字串格式
        
        Args:
            data_array_str: Supabase 返回的字串，例如 '["21.5853","21.1291",...]'
        
        Returns:
            numpy 陣列，192 個 float 值
        """
        try:
            # 解析 JSON 字串
            if isinstance(data_array_str, str):
                data_list = json.loads(data_array_str)
            else:
                # 如果已經是列表
                data_list = data_array_str
            
            # 轉換為 float 陣列
            data_array = np.array([float(x) for x in data_list], dtype=np.float32)
            
            if len(data_array) != 192:
                raise ValueError(
                    f"資料長度應為 192 (12×16)，但得到 {len(data_array)}"
                )
            
            return data_array
        
        except json.JSONDecodeError as e:
            raise ValueError(f"無法解析 JSON 字串: {e}")
        except Exception as e:
            raise ValueError(f"解析資料時發生錯誤: {e}")
    
    @retry_supabase_query(max_retries=3, delay=1.0)
    def process_latest_frame(
        self,
        session_id: str,
        limit: int = 1
    ) -> Optional[Dict[str, Any]]:
        """
        處理指定 session 的最新熱像儀資料
        
        Args:
            session_id: 會話 ID，例如 '604_windowside'
            limit: 要處理的記錄數量（預設為 1，只處理最新的）
        
        Returns:
            包含處理結果的字典，如果沒有資料則返回 None
        """
        try:
            # 查詢最新的資料
            response = self.supabase.table('thermal_frames')\
                .select('id, session_id, ts, data')\
                .eq('session_id', session_id)\
                .order('ts', desc=True)\
                .limit(limit)\
                .execute()
            
            if not response.data or len(response.data) == 0:
                return None
            
            results = []
            
            for record in response.data:
                # 解析資料陣列
                data_array = self.parse_data_array(record['data'])
                
                # 處理幀
                density_map = self.frame_processor.process_frame(data_array)
                people_count = self.frame_processor.get_people_count_on_latest_frame()
                
                results.append({
                    'id': record['id'],
                    'session_id': record['session_id'],
                    'timestamp': record['ts'],
                    'people_count': float(people_count),
                    'people_count_rounded': int(round(people_count)),
                    'density_map': density_map,  # 保存密度圖供後續使用
                    'density_map_sum': float(np.sum(density_map)),
                    'density_map_shape': density_map.shape,
                    'raw_data_length': len(data_array)
                })
            
            return results[0] if limit == 1 else results
        
        except RuntimeError:
            # 重試裝飾器已經處理了連接錯誤，直接重新拋出
            raise
        except Exception as e:
            raise RuntimeError(f"處理 Supabase 資料時發生錯誤: {e}")
    
    @retry_supabase_query(max_retries=3, delay=1.0)
    def process_frame_by_id(self, frame_id: int) -> Optional[Dict[str, Any]]:
        """
        根據 ID 處理特定的熱像儀資料
        
        Args:
            frame_id: 資料記錄的 ID
        
        Returns:
            包含處理結果的字典，如果沒有找到資料則返回 None
        """
        try:
            # 查詢指定 ID 的資料
            response = self.supabase.table('thermal_frames')\
                .select('id, session_id, ts, data')\
                .eq('id', frame_id)\
                .execute()
            
            if not response.data or len(response.data) == 0:
                return None
            
            record = response.data[0]
            
            # 解析資料陣列
            data_array = self.parse_data_array(record['data'])
            
            # 處理幀
            density_map = self.frame_processor.process_frame(data_array)
            people_count = self.frame_processor.get_people_count_on_latest_frame()
            
            return {
                'id': record['id'],
                'session_id': record['session_id'],
                'timestamp': record['ts'],
                'people_count': float(people_count),
                'people_count_rounded': int(round(people_count)),
                'density_map': density_map,  # 保存密度圖供後續使用
                'density_map_sum': float(np.sum(density_map)),
                'density_map_shape': density_map.shape,
                'raw_data_length': len(data_array)
            }
        
        except RuntimeError:
            # 重試裝飾器已經處理了連接錯誤，直接重新拋出
            raise
        except Exception as e:
            raise RuntimeError(f"處理 Supabase 資料時發生錯誤: {e}")
    
    def process_multiple_frames(
        self,
        session_id: str,
        limit: int = 10,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        處理多個熱像儀資料
        
        Args:
            session_id: 會話 ID
            limit: 要處理的記錄數量上限
            start_time: 開始時間（ISO 格式字串，可選）
            end_time: 結束時間（ISO 格式字串，可選）
        
        Returns:
            處理結果列表
        """
        try:
            query = self.supabase.table('thermal_frames')\
                .select('id, session_id, ts, data')\
                .eq('session_id', session_id)
            
            if start_time:
                query = query.gte('ts', start_time)
            if end_time:
                query = query.lte('ts', end_time)
            
            # Use range for basic offset-based pagination
            start_index = max(offset, 0)
            end_index = start_index + max(limit, 1) - 1
            response = query.order('ts', desc=True).range(start_index, end_index).execute()
            
            if not response.data:
                return []
            
            results = []
            
            for record in response.data:
                try:
                    # 解析資料陣列
                    data_array = self.parse_data_array(record['data'])
                    
                    # 處理幀
                    density_map = self.frame_processor.process_frame(data_array)
                    people_count = self.frame_processor.get_people_count_on_latest_frame()
                    
                    results.append({
                        'id': record['id'],
                        'session_id': record['session_id'],
                        'timestamp': record['ts'],
                        'people_count': float(people_count),
                        'people_count_rounded': int(round(people_count)),
                        'density_map': density_map,  # 保存密度圖供後續使用
                        'density_map_sum': float(np.sum(density_map)),
                        'density_map_shape': density_map.shape,
                        'raw_data_length': len(data_array)
                    })
                except Exception as e:
                    print(f"處理記錄 {record['id']} 時發生錯誤: {e}")
                    continue
            
            return results
        
        except Exception as e:
            raise RuntimeError(f"處理 Supabase 資料時發生錯誤: {e}")
    
    def save_results_to_supabase(
        self,
        results: Dict[str, Any],
        table_name: str = 'people_count_results',
        save_density_map: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        將處理結果儲存回 Supabase（混合方案）
        
        Args:
            results: 處理結果字典，應包含 'density_map' 和 'density_map_sum'
            table_name: 目標資料表名稱
            save_density_map: 是否儲存密度圖（預設 False，節省空間）
        
        Returns:
            儲存結果
        """
        try:
            # 基本資料（必存）
            data_to_insert = {
                'frame_id': results['id'],
                'session_id': results['session_id'],
                'timestamp': results['timestamp'],
                'people_count': results['people_count'],
                'people_count_rounded': results['people_count_rounded'],
                'density_map_sum': results.get('density_map_sum', 0.0),
                'has_density_map': False
            }
            
            # 可選：儲存密度圖
            if save_density_map and 'density_map' in results:
                density_map = results['density_map']
                if density_map is not None:
                    try:
                        # 壓縮密度圖（24×32 float32）
                        density_map_float32 = density_map.astype(np.float32)
                        density_map_bytes = gzip.compress(
                            pickle.dumps(density_map_float32)
                        )
                        # 轉換為 base64 字串以便儲存到資料庫
                        density_map_b64 = base64.b64encode(density_map_bytes).decode('utf-8')
                        
                        data_to_insert['density_map'] = density_map_b64
                        data_to_insert['has_density_map'] = True
                    except Exception as e:
                        print(f"警告: 無法壓縮密度圖: {e}")
                        # 繼續儲存其他資料
            
            response = self.supabase.table(table_name).insert(data_to_insert).execute()
            return response.data[0] if response.data else None
        
        except Exception as e:
            print(f"儲存結果到 Supabase 時發生錯誤: {e}")
            return None
    
    def get_density_map_for_frame(
        self,
        frame_id: int,
        cache_if_missing: bool = False
    ) -> Optional[np.ndarray]:
        """
        獲取指定 frame 的密度圖（按需計算或讀取）
        
        Args:
            frame_id: 資料記錄的 ID
            cache_if_missing: 如果沒有儲存的密度圖，計算後是否儲存（預設 False）
        
        Returns:
            24×32 的密度圖 numpy 陣列，如果找不到資料則返回 None
        """
        try:
            # 1. 先查詢是否有儲存的密度圖
            result_response = self.supabase.table('people_count_results')\
                .select('density_map, has_density_map')\
                .eq('frame_id', frame_id)\
                .execute()
            
            if result_response.data and result_response.data[0].get('has_density_map'):
                # 有儲存：解壓縮密度圖
                try:
                    density_map_b64 = result_response.data[0]['density_map']
                    density_map_bytes = base64.b64decode(density_map_b64)
                    density_map = pickle.loads(gzip.decompress(density_map_bytes))
                    return density_map.astype(np.float64)
                except Exception as e:
                    print(f"警告: 無法解壓縮儲存的密度圖: {e}")
                    # 繼續執行，重新計算
            
            # 2. 沒有儲存：從原始資料重新計算
            frame_response = self.supabase.table('thermal_frames')\
                .select('id, data')\
                .eq('id', frame_id)\
                .execute()
            
            if not frame_response.data:
                return None
            
            # 解析並處理原始資料
            data_array = self.parse_data_array(frame_response.data[0]['data'])
            density_map = self.frame_processor.process_frame(data_array)
            
            # 3. 可選：儲存到資料庫（供下次使用）
            if cache_if_missing:
                try:
                    # 更新現有記錄或創建新記錄
                    density_map_float32 = density_map.astype(np.float32)
                    density_map_bytes = gzip.compress(
                        pickle.dumps(density_map_float32)
                    )
                    density_map_b64 = base64.b64encode(density_map_bytes).decode('utf-8')
                    
                    # 檢查是否已有記錄
                    existing = self.supabase.table('people_count_results')\
                        .select('id')\
                        .eq('frame_id', frame_id)\
                        .execute()
                    
                    if existing.data:
                        # 更新現有記錄
                        self.supabase.table('people_count_results')\
                            .update({
                                'density_map': density_map_b64,
                                'has_density_map': True
                            })\
                            .eq('frame_id', frame_id)\
                            .execute()
                    else:
                        # 需要先處理並儲存結果（這裡只更新密度圖部分）
                        # 注意：這種情況下應該先調用 save_results_to_supabase
                        print("警告: 找不到對應的結果記錄，無法快取密度圖")
                except Exception as e:
                    print(f"警告: 無法快取密度圖: {e}")
            
            return density_map
        
        except Exception as e:
            raise RuntimeError(f"獲取密度圖時發生錯誤: {e}")

