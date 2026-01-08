"""
FrameProcessor for MLX90641 (12×16 resolution)
Adapted from the original FrameProcessor for MLX90640 (24×32)
"""

import os
import numpy as np
import torch
from torch import nn
from typing import Tuple
import cv2

# Import model architecture directly from original frame_processor.py
# This ensures we use the exact same architecture as the trained models
import sys
import importlib.util

def _import_model_architecture():
    """動態導入原始 frame_processor.py 中的模型架構類別"""
    frame_processor_path = os.path.join(
        os.path.dirname(__file__),
        '..',
        'data_collection',
        'src',
        'trained_model',
        'frame_processor.py'
    )
    
    if not os.path.exists(frame_processor_path):
        raise FileNotFoundError(
            f"找不到原始 frame_processor.py 檔案: {frame_processor_path}\n"
            "請確保檔案存在於正確的位置"
        )
    
    spec = importlib.util.spec_from_file_location("frame_processor", frame_processor_path)
    frame_processor_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(frame_processor_module)
    
    return (
        frame_processor_module.AutoEncoder,
        frame_processor_module.Encoder,
        frame_processor_module.ExpandBlock,
        frame_processor_module.ContractBlock,
        frame_processor_module.DoubleConv
    )

# 嘗試導入原始架構
# #region agent log
try:
    with open(r'c:\Users\a0903\Documents\CAE\thermo-presence\.cursor\debug.log', 'a', encoding='utf-8') as f:
        import json, time
        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"frame_processor_mlx90641.py:48","message":"開始導入模型架構","data":{},"timestamp":int(time.time()*1000)}) + '\n')
except:
    pass
# #endregion
try:
    AutoEncoder, Encoder, ExpandBlock, ContractBlock, DoubleConv = _import_model_architecture()
    # #region agent log
    try:
        with open(r'c:\Users\a0903\Documents\CAE\thermo-presence\.cursor\debug.log', 'a', encoding='utf-8') as f:
            import json, time
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"frame_processor_mlx90641.py:50","message":"模型架構導入成功","data":{"AutoEncoder":str(AutoEncoder)},"timestamp":int(time.time()*1000)}) + '\n')
    except:
        pass
    # #endregion
except Exception as e:
    # #region agent log
    try:
        with open(r'c:\Users\a0903\Documents\CAE\thermo-presence\.cursor\debug.log', 'a', encoding='utf-8') as f:
            import json, time
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"frame_processor_mlx90641.py:52","message":"模型架構導入失敗，使用備用定義","data":{"error":str(e)[:200]},"timestamp":int(time.time()*1000)}) + '\n')
    except:
        pass
    # #endregion
    # 如果導入失敗，使用備用定義（但這可能與模型檔案不匹配）
    print(f"警告: 無法從原始檔案導入模型架構: {e}")
    print("嘗試使用備用定義（可能與模型檔案不匹配）")
    
    # 備用定義（與原始 frame_processor.py 相同）
    class DoubleConv(nn.Sequential):
        def __init__(self, in_channels: int, out_channels: int, kernel_size: int, padding: int = 0):
            super().__init__(
                nn.Conv2d(in_channels, out_channels, kernel_size=kernel_size, stride=1, padding=padding),
                nn.BatchNorm2d(out_channels),
                nn.ReLU(inplace=True),
                nn.Conv2d(out_channels, out_channels, kernel_size=kernel_size, stride=1, padding=padding),
                nn.BatchNorm2d(out_channels),
                nn.ReLU(inplace=True),
            )

    class ContractBlock(nn.Module):
        def __init__(self, in_channels, out_channels, kernel_size, padding):
            super().__init__()
            self.conv = DoubleConv(in_channels, out_channels, kernel_size, padding=padding)
            self.pool = nn.MaxPool2d(kernel_size=2, stride=2)
        
        def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
            features = self.conv(x)
            x = self.pool(features)
            return x, features

    class Encoder(nn.Module):
        def __init__(self, in_channels: int):
            super().__init__()
            self.conv1 = ContractBlock(in_channels, 16, 3, 1)
            self.conv2 = ContractBlock(16, 32, 3, 1)
        
        def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
            x, conv1 = self.conv1(x)
            x, conv2 = self.conv2(x)
            return x, conv2, conv1

    class ExpandBlock(nn.Sequential):
        def __init__(self, in_channels: int, out_channels: int, kernel_size: int, padding: int):
            super().__init__()
            self.conv_transpose = nn.ConvTranspose2d(
                in_channels, in_channels // 2, kernel_size=3, stride=2, padding=1, output_padding=1
            )
            self.conv1 = nn.Conv2d(in_channels, out_channels, kernel_size, padding=padding)
            self.bn1 = nn.BatchNorm2d(out_channels)
            self.conv2 = nn.Conv2d(out_channels, out_channels, kernel_size, padding=padding)
            self.bn2 = nn.BatchNorm2d(out_channels)
            self.relu = nn.ReLU(inplace=True)
        
        def forward(self, x: torch.Tensor, encoder_features: torch.Tensor) -> torch.Tensor:
            x = self.conv_transpose(x)
            x = torch.cat((x, encoder_features), dim=1)
            x = self.conv1(x)
            x = self.bn1(x)
            x = self.relu(x)
            x = self.conv2(x)
            x = self.bn2(x)
            x = self.relu(x)
            return x

    class AutoEncoder(torch.nn.Module):
        def __init__(self, in_channels, out_channels):
            super().__init__()
            self.encoder = Encoder(in_channels)
            self.conv = DoubleConv(32, 64, 3, 1)
            self.upconv1 = ExpandBlock(64, 32, 3, 1)
            self.upconv2 = ExpandBlock(32, 16, 3, 1)
            self.out_conv = nn.Conv2d(16, out_channels, kernel_size=1)
        
        def forward(self, x):
            x, conv2, conv1 = self.encoder(x)
            x = self.conv(x)
            x = self.upconv1(x, conv2)
            x = self.upconv2(x, conv1)
            x = self.out_conv(x)
            x = x[:, 0, :, :]
            return x


class FrameProcessorMLX90641:
    """
    處理 MLX90641 熱像儀資料的 FrameProcessor
    
    將 12×16 的輸入上採樣到 24×32，以適配訓練好的模型
    """
    
    def __init__(self, model_path=None):
        """
        初始化 FrameProcessor
        
        Args:
            model_path: 模型檔案路徑。如果為 None，會嘗試使用預設路徑
        """
        self.latest_output_frame = None
        self.sum_of_values_for_one_person = 52
        
        # MLX90641 解析度
        self.INPUT_RESOLUTION = (12, 16)  # (height, width)
        # 模型期望的解析度 (MLX90640)
        self.MODEL_RESOLUTION = (24, 32)  # (height, width)
        
        # 溫度正規化參數
        self.TEMPERATURE_NORMALIZATION__MIN = 20
        self.TEMPERATURE_NORMALIZATION__MAX = 35
        
        # 設定模型路徑
        if model_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # 嘗試多個可能的模型檔案路徑
            possible_paths = [
                os.path.join(current_dir, '..', 'data_collection', 'src', 'trained_model', 'unet_v2_cpu1'),
                os.path.join(current_dir, '..', 'data_collection', 'src', 'trained_model', 'unet_gauss_model_cpu1'),
                os.path.join(current_dir, '..', 'data_collection', 'src', 'trained_model', 'unet_gauss_model_gpu1'),
            ]
            
            model_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    model_path = path
                    break
            
            if model_path is None:
                raise FileNotFoundError(
                    "找不到模型檔案。請指定 model_path 或確保模型檔案存在於以下位置之一：\n" +
                    "\n".join(possible_paths)
                )
        
        # 先載入模型權重來檢查架構
        # #region agent log
        with open(r'c:\Users\a0903\Documents\CAE\thermo-presence\.cursor\debug.log', 'a', encoding='utf-8') as f:
            import json, time
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"frame_processor_mlx90641.py:179","message":"開始載入模型","data":{"model_path":model_path},"timestamp":int(time.time()*1000)}) + '\n')
        # #endregion
        try:
            checkpoint = torch.load(model_path, map_location='cpu')
            # #region agent log
            with open(r'c:\Users\a0903\Documents\CAE\thermo-presence\.cursor\debug.log', 'a', encoding='utf-8') as f:
                import json, time
                checkpoint_keys = list(checkpoint.keys())[:5] if isinstance(checkpoint, dict) else "not_dict"
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"frame_processor_mlx90641.py:183","message":"模型權重載入成功","data":{"checkpoint_type":type(checkpoint).__name__,"has_keys":isinstance(checkpoint,dict),"sample_keys":checkpoint_keys},"timestamp":int(time.time()*1000)}) + '\n')
            # #endregion
            
            # 檢查模型架構（根據權重的鍵來推斷）
            if isinstance(checkpoint, dict) and 'encoder.conv1.conv.0.weight' in checkpoint:
                # 檢查第一層的輸出通道數
                first_conv_out = checkpoint['encoder.conv1.conv.0.weight'].shape[0]
                second_conv_out = checkpoint['encoder.conv2.conv.0.weight'].shape[0]
                middle_conv_out = checkpoint['conv.0.weight'].shape[0]
                # #region agent log
                with open(r'c:\Users\a0903\Documents\CAE\thermo-presence\.cursor\debug.log', 'a', encoding='utf-8') as f:
                    import json, time
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"frame_processor_mlx90641.py:191","message":"檢查模型架構","data":{"first_conv_out":int(first_conv_out),"second_conv_out":int(second_conv_out),"middle_conv_out":int(middle_conv_out)},"timestamp":int(time.time()*1000)}) + '\n')
                # #endregion
                
                # 根據檢查點推斷架構
                if first_conv_out == 32 and second_conv_out == 64:
                    # 使用更大的架構（32->64->128）
                    print(f"偵測到模型使用較大架構: {first_conv_out}->{second_conv_out}->{middle_conv_out}")
                    # #region agent log
                    with open(r'c:\Users\a0903\Documents\CAE\thermo-presence\.cursor\debug.log', 'a', encoding='utf-8') as f:
                        import json, time
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"frame_processor_mlx90641.py:195","message":"使用較大架構","data":{"architecture":"32->64->128"},"timestamp":int(time.time()*1000)}) + '\n')
                    # #endregion
                    # 動態創建正確的架構
                    self.model = FrameProcessorMLX90641._create_larger_architecture().double()
                else:
                    # 使用標準架構（16->32->64）
                    print(f"偵測到模型使用標準架構: {first_conv_out}->{second_conv_out}->{middle_conv_out}")
                    # #region agent log
                    with open(r'c:\Users\a0903\Documents\CAE\thermo-presence\.cursor\debug.log', 'a', encoding='utf-8') as f:
                        import json, time
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"frame_processor_mlx90641.py:199","message":"使用標準架構","data":{"architecture":"16->32->64"},"timestamp":int(time.time()*1000)}) + '\n')
                    # #endregion
                    self.model = AutoEncoder(1, 1).double()
            else:
                # 預設使用標準架構
                # #region agent log
                with open(r'c:\Users\a0903\Documents\CAE\thermo-presence\.cursor\debug.log', 'a', encoding='utf-8') as f:
                    import json, time
                    has_key = isinstance(checkpoint, dict) and 'encoder.conv1.conv.0.weight' in checkpoint
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"frame_processor_mlx90641.py:202","message":"使用預設標準架構","data":{"has_expected_key":has_key},"timestamp":int(time.time()*1000)}) + '\n')
                # #endregion
                self.model = AutoEncoder(1, 1).double()
            
            # 載入模型權重
            # #region agent log
            with open(r'c:\Users\a0903\Documents\CAE\thermo-presence\.cursor\debug.log', 'a', encoding='utf-8') as f:
                import json, time
                model_keys = list(self.model.state_dict().keys())[:5]
                checkpoint_keys = list(checkpoint.keys())[:5] if isinstance(checkpoint, dict) else []
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"frame_processor_mlx90641.py:205","message":"準備載入權重","data":{"model_keys_sample":model_keys,"checkpoint_keys_sample":checkpoint_keys},"timestamp":int(time.time()*1000)}) + '\n')
            # #endregion
            self.model.load_state_dict(checkpoint)
            # #region agent log
            with open(r'c:\Users\a0903\Documents\CAE\thermo-presence\.cursor\debug.log', 'a', encoding='utf-8') as f:
                import json, time
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"frame_processor_mlx90641.py:205","message":"權重載入成功","data":{},"timestamp":int(time.time()*1000)}) + '\n')
            # #endregion
            
        except RuntimeError as e:
            # #region agent log
            with open(r'c:\Users\a0903\Documents\CAE\thermo-presence\.cursor\debug.log', 'a', encoding='utf-8') as f:
                import json, time
                error_msg = str(e)[:200]
                is_size_mismatch = "size mismatch" in error_msg.lower()
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"frame_processor_mlx90641.py:207","message":"RuntimeError 發生","data":{"error_type":"RuntimeError","is_size_mismatch":is_size_mismatch,"error_preview":error_msg},"timestamp":int(time.time()*1000)}) + '\n')
            # #endregion
            # 如果載入失敗，可能是架構不匹配，嘗試使用較大的架構
            if "size mismatch" in str(e):
                print(f"標準架構載入失敗，嘗試使用較大架構...")
                # #region agent log
                with open(r'c:\Users\a0903\Documents\CAE\thermo-presence\.cursor\debug.log', 'a', encoding='utf-8') as f:
                    import json, time
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"frame_processor_mlx90641.py:211","message":"嘗試較大架構","data":{},"timestamp":int(time.time()*1000)}) + '\n')
                # #endregion
                try:
                    checkpoint = torch.load(model_path, map_location='cpu')
                    self.model = FrameProcessorMLX90641._create_larger_architecture().double()
                    # #region agent log
                    with open(r'c:\Users\a0903\Documents\CAE\thermo-presence\.cursor\debug.log', 'a', encoding='utf-8') as f:
                        import json, time
                        model_keys = list(self.model.state_dict().keys())[:5]
                        checkpoint_keys = list(checkpoint.keys())[:5] if isinstance(checkpoint, dict) else []
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"frame_processor_mlx90641.py:214","message":"較大架構創建完成，準備載入","data":{"model_keys_sample":model_keys,"checkpoint_keys_sample":checkpoint_keys},"timestamp":int(time.time()*1000)}) + '\n')
                    # #endregion
                    self.model.load_state_dict(checkpoint)
                    # #region agent log
                    with open(r'c:\Users\a0903\Documents\CAE\thermo-presence\.cursor\debug.log', 'a', encoding='utf-8') as f:
                        import json, time
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"frame_processor_mlx90641.py:214","message":"較大架構載入成功","data":{},"timestamp":int(time.time()*1000)}) + '\n')
                    # #endregion
                    print("✓ 使用較大架構成功載入模型")
                except Exception as e2:
                    # #region agent log
                    with open(r'c:\Users\a0903\Documents\CAE\thermo-presence\.cursor\debug.log', 'a', encoding='utf-8') as f:
                        import json, time
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"frame_processor_mlx90641.py:216","message":"較大架構也失敗","data":{"error":str(e2)[:200]},"timestamp":int(time.time()*1000)}) + '\n')
                    # #endregion
                    raise RuntimeError(
                        f"無法載入模型檔案 {model_path}。\n"
                        f"標準架構錯誤: {e}\n"
                        f"較大架構錯誤: {e2}\n"
                        "請確認模型檔案與架構定義匹配。"
                    )
            else:
                # #region agent log
                with open(r'c:\Users\a0903\Documents\CAE\thermo-presence\.cursor\debug.log', 'a', encoding='utf-8') as f:
                    import json, time
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"frame_processor_mlx90641.py:225","message":"非 size mismatch 錯誤，直接拋出","data":{"error":str(e)[:200]},"timestamp":int(time.time()*1000)}) + '\n')
                # #endregion
                raise RuntimeError(f"無法載入模型檔案 {model_path}: {e}")
        except Exception as e:
            # #region agent log
            with open(r'c:\Users\a0903\Documents\CAE\thermo-presence\.cursor\debug.log', 'a', encoding='utf-8') as f:
                import json, time
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"frame_processor_mlx90641.py:227","message":"其他異常","data":{"error_type":type(e).__name__,"error":str(e)[:200]},"timestamp":int(time.time()*1000)}) + '\n')
            # #endregion
            raise RuntimeError(f"無法載入模型檔案 {model_path}: {e}")
        
        self.model.eval()
        self.model.train(False)
    
    @staticmethod
    def _create_larger_architecture():
        """創建較大的模型架構（32->64->128），用於 unet_v2_cpu1 等模型"""
        # #region agent log
        try:
            with open(r'c:\Users\a0903\Documents\CAE\thermo-presence\.cursor\debug.log', 'a', encoding='utf-8') as f:
                import json, time
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"F","location":"frame_processor_mlx90641.py:310","message":"創建較大架構","data":{"ContractBlock":str(ContractBlock),"DoubleConv":str(DoubleConv),"ExpandBlock":str(ExpandBlock)},"timestamp":int(time.time()*1000)}) + '\n')
        except:
            pass
        # #endregion
        
        class LargeEncoder(nn.Module):
            def __init__(self, in_channels: int):
                super().__init__()
                self.conv1 = ContractBlock(in_channels, 32, 3, 1)
                self.conv2 = ContractBlock(32, 64, 3, 1)
            
            def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
                x, conv1 = self.conv1(x)
                x, conv2 = self.conv2(x)
                return x, conv2, conv1
        
        class LargeAutoEncoder(torch.nn.Module):
            def __init__(self, in_channels, out_channels):
                super().__init__()
                self.encoder = LargeEncoder(in_channels)
                self.conv = DoubleConv(64, 128, 3, 1)
                self.upconv1 = ExpandBlock(128, 64, 3, 1)
                self.upconv2 = ExpandBlock(64, 32, 3, 1)
                self.out_conv = nn.Conv2d(32, out_channels, kernel_size=1)
            
            def forward(self, x):
                x, conv2, conv1 = self.encoder(x)
                x = self.conv(x)
                x = self.upconv1(x, conv2)
                x = self.upconv2(x, conv1)
                x = self.out_conv(x)
                x = x[:, 0, :, :]
                return x
        
        # #region agent log
        try:
            with open(r'c:\Users\a0903\Documents\CAE\thermo-presence\.cursor\debug.log', 'a', encoding='utf-8') as f:
                import json, time
                model = LargeAutoEncoder(1, 1)
                model_keys = list(model.state_dict().keys())[:5]
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"F","location":"frame_processor_mlx90641.py:340","message":"較大架構創建完成","data":{"model_keys_sample":model_keys},"timestamp":int(time.time()*1000)}) + '\n')
        except Exception as e:
            try:
                with open(r'c:\Users\a0903\Documents\CAE\thermo-presence\.cursor\debug.log', 'a', encoding='utf-8') as f:
                    import json, time
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"F","location":"frame_processor_mlx90641.py:340","message":"較大架構創建失敗","data":{"error":str(e)[:200]},"timestamp":int(time.time()*1000)}) + '\n')
            except:
                pass
        # #endregion
        
        return LargeAutoEncoder(1, 1)
    
    def process_frame(self, raw_frame):
        """
        處理 MLX90641 的 12×16 資料
        
        Args:
            raw_frame: 192 個 float 的陣列（12×16 flatten），或已經是 12×16 的 2D 陣列
        
        Returns:
            24×32 的密度圖 (numpy array)
        """
        # 1. 確保輸入是正確的格式
        if isinstance(raw_frame, list):
            raw_frame = np.array(raw_frame, dtype=np.float32)
        elif not isinstance(raw_frame, np.ndarray):
            raw_frame = np.array(raw_frame, dtype=np.float32)
        
        # 2. 重塑為 12×16（如果是一維陣列）
        if raw_frame.ndim == 1:
            if len(raw_frame) != 192:
                raise ValueError(
                    f"輸入資料長度應為 192 (12×16)，但得到 {len(raw_frame)}"
                )
            frame_2d = np.reshape(raw_frame, self.INPUT_RESOLUTION)
        elif raw_frame.ndim == 2:
            if raw_frame.shape != self.INPUT_RESOLUTION:
                raise ValueError(
                    f"輸入資料形狀應為 {self.INPUT_RESOLUTION}，但得到 {raw_frame.shape}"
                )
            frame_2d = raw_frame.copy()
        else:
            raise ValueError(f"不支援的輸入維度: {raw_frame.ndim}")
        
        # 3. 上採樣到 24×32（使用雙三次插值以保持溫度資訊）
        frame_upsampled = cv2.resize(
            frame_2d,
            (self.MODEL_RESOLUTION[1], self.MODEL_RESOLUTION[0]),  # (width, height)
            interpolation=cv2.INTER_CUBIC
        )
        
        # 4. 溫度正規化（20-35°C 範圍）
        frame_normalized = (frame_upsampled - self.TEMPERATURE_NORMALIZATION__MIN) * \
                          (1 / (self.TEMPERATURE_NORMALIZATION__MAX - self.TEMPERATURE_NORMALIZATION__MIN))
        
        # 5. 轉換為模型輸入格式：(batch, channels, height, width) = (1, 1, 24, 32)
        frame_for_model = torch.tensor(
            frame_normalized,
            dtype=torch.float64
        )[np.newaxis, :, :][np.newaxis, :, :, :]
        
        # 6. 模型推論
        with torch.no_grad():
            model_out_frame = self.model(frame_for_model)[0]
        
        self.latest_output_frame = model_out_frame.numpy()
        return self.latest_output_frame
    
    def get_people_count_on_latest_frame(self):
        """
        計算人數
        
        Returns:
            偵測到的人數（浮點數）
        """
        if self.latest_output_frame is None:
            return -1
        return np.sum(self.latest_output_frame) / self.sum_of_values_for_one_person
    
    def get_density_map(self):
        """
        獲取最新的密度圖
        
        Returns:
            24×32 的密度圖，如果沒有處理過任何幀則返回 None
        """
        return self.latest_output_frame.copy() if self.latest_output_frame is not None else None

