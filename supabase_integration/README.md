# Supabase 熱像儀人數偵測整合

這個模組提供從 Supabase 讀取 MLX90641 熱像儀資料並進行人數偵測的功能。

## 功能特點

- ✅ 支援 MLX90641 (12×16) 解析度
- ✅ 自動上採樣到模型所需的 24×32 解析度
- ✅ 從 Supabase 讀取資料
- ✅ 人數偵測與密度圖生成
- ✅ 可選的結果回寫到 Supabase

## 安裝

1. **（推薦）建立虛擬環境**：

**Windows:**
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows PowerShell
# 或 .venv\Scripts\activate.bat 在 CMD
```

**Linux/Mac:**
```bash
python -m venv .venv
source .venv/bin/activate
```

2. 安裝依賴套件：

**Windows:**
```bash
# 方法 1: 使用提供的批次檔（會抑制 PATH 警告）
install.bat

# 方法 2: 直接使用 pip（會顯示 PATH 警告，但不影響功能）
pip install -r requirements.txt
# 或使用 python -m pip 確保安裝到正確的環境
python -m pip install -r requirements.txt

# 方法 3: 抑制警告
pip install --no-warn-script-location -r requirements.txt
```

**Linux/Mac:**
```bash
# 方法 1: 使用提供的腳本（會抑制 PATH 警告）
chmod +x install.sh
./install.sh

# 方法 2: 直接使用 pip
pip install -r requirements.txt
# 或使用 python -m pip 確保安裝到正確的環境
python -m pip install -r requirements.txt

# 方法 3: 抑制警告
pip install --no-warn-script-location -r requirements.txt
```

**注意：** 如果看到 PATH 警告，這不會影響功能，只是提醒您某些腳本不在系統 PATH 中。您可以：
- 忽略警告（不影響使用）
- 使用 `--no-warn-script-location` 參數抑制警告
- 將 `C:\Users\a0903\AppData\Roaming\Python\Python313\Scripts` 添加到系統 PATH

3. 確保已安裝 PyTorch（如果尚未安裝）：

```bash
pip install torch
```

## 設定

### 環境變數設定（推薦）

創建 `.env` 檔案在 `supabase_integration` 目錄下：

```env
SUPABASE_URL=your-supabase-url
SUPABASE_KEY=your-supabase-key
```

**注意：** 如果設定了 `.env` 檔案，命令列參數 `--supabase-url` 和 `--supabase-key` 變為可選。

### Supabase 資料表結構

確保您的 Supabase 資料表 `thermal_frames` 有以下欄位：

- `id` (bigint): 主鍵
- `session_id` (text): 會話 ID，例如 '604_windowside'
- `ts` (timestamptz): 時間戳記
- `data` (float4[]): 192 個 float 的陣列（12×16 flatten）

## 使用方法

### 方法 1: 使用命令列工具

**使用 .env 檔案（推薦）：**

```bash
# 如果已設定 .env 檔案，只需要提供 session-id
python main.py --session-id "604_windowside" --limit 1
```

**或使用命令列參數：**

```bash
python main.py \
    --supabase-url "your-supabase-url" \
    --supabase-key "your-supabase-key" \
    --session-id "604_windowside" \
    --limit 1
```

處理特定 ID 的資料：

```bash
python main.py \
    --supabase-url "your-supabase-url" \
    --supabase-key "your-supabase-key" \
    --frame-id 20082
```

處理多筆資料並儲存結果：

```bash
python main.py \
    --session-id "604_windowside" \
    --limit 10 \
    --save-results \
    --results-table "people_count_results"
```

**儲存密度圖（可選）：**

```bash
# 儲存結果並包含密度圖（會增加儲存空間，但可加快後續查詢）
python main.py \
    --session-id "604_windowside" \
    --limit 1 \
    --save-results \
    --save-density-map
```

### 方法 3: YOLO 即時偵測測試

使用 `test_yolo_realtime.py` 腳本測試 YOLO 模型對 Supabase 即時資料的偵測效果：

```bash
# 測試最新一筆資料並視覺化
python test_yolo_realtime.py --session-id 604_windowside --limit 1 --visualize

# 測試指定 frame_id
python test_yolo_realtime.py --frame-id 244560 --visualize

# 調整 YOLO 參數
python test_yolo_realtime.py --session-id 604_windowside --conf 0.5 --iou 0.5 --max-det 20 --visualize

# 儲存視覺化結果
python test_yolo_realtime.py --session-id 604_windowside --visualize --save-images --output-dir output_images
```

**功能：**
- 從 Supabase 讀取熱影像資料
- 使用訓練好的 YOLO 模型進行人數偵測
- 與 U-Net 結果對比
- 視覺化顯示 YOLO bounding boxes 和 U-Net 密度圖
- 可選：將 YOLO 結果寫回 Supabase

**需求：**
- YOLO 模型權重檔案：`yolo_training/runs/train/weights/best.pt` 或 `last.pt`
- `ultralytics` 套件已安裝

### 方法 4: 批次處理所有資料

使用 `batch_process_all.py` 一次性處理所有 `thermal_frames` 資料：

```bash
# 處理所有資料（跳過已處理的）
python batch_process_all.py

# 處理指定 session 的資料
python batch_process_all.py --session-id "604_windowside"

# 處理所有資料並儲存密度圖
python batch_process_all.py --save-density-map

# 不跳過已處理的資料（重新處理）
python batch_process_all.py --no-skip-existing

# 限制批次數（用於測試）
python batch_process_all.py --max-batches 5
```

**參數說明：**
- `--session-id`: 只處理指定 session_id 的資料（可選）
- `--save-density-map`: 同時儲存密度圖到資料庫
- `--skip-existing`: 跳過已經處理過的資料（預設: True）
- `--no-skip-existing`: 不跳過已處理的資料（會重新處理）
- `--batch-size`: 每批處理的筆數（預設: 1000，Supabase 限制）
- `--max-batches`: 最多處理的批次數（可選，用於測試）

**注意：**
- 程式會自動分頁處理，每次最多載入 1000 筆（Supabase 限制）
- 預設會跳過已經處理過的資料，避免重複處理
- 處理過程中會顯示進度資訊

### 方法 2: 在 Python 程式中使用

```python
from dotenv import load_dotenv
from supabase_client import SupabaseThermalProcessor

# 載入 .env 檔案
load_dotenv()

# 初始化處理器（會自動從 .env 讀取 SUPABASE_URL 和 SUPABASE_KEY）
processor = SupabaseThermalProcessor()

# 處理最新的資料
result = processor.process_latest_frame("604_windowside")

if result:
    print(f"偵測到人數: {result['people_count']:.2f}")
    print(f"時間: {result['timestamp']}")
```

**儲存結果並包含密度圖：**

```python
from dotenv import load_dotenv
from supabase_client import SupabaseThermalProcessor

load_dotenv()
processor = SupabaseThermalProcessor()

# 處理資料
result = processor.process_latest_frame("604_windowside")

if result:
    # 儲存結果（包含密度圖）
    saved = processor.save_results_to_supabase(
        result,
        save_density_map=True  # 儲存密度圖
    )
```

**按需獲取密度圖：**

```python
# 獲取密度圖（會自動檢查是否有儲存，沒有則重新計算）
density_map = processor.get_density_map_for_frame(
    frame_id=31768,
    cache_if_missing=True  # 如果沒有儲存，計算後自動快取
)

if density_map is not None:
    print(f"密度圖形狀: {density_map.shape}")
    print(f"密度圖總和: {np.sum(density_map):.2f}")
```

**或手動指定：**

```python
from supabase_client import SupabaseThermalProcessor

# 手動指定 Supabase 連線資訊
processor = SupabaseThermalProcessor(
    supabase_url="your-supabase-url",
    supabase_key="your-supabase-key"
)
```

### 方法 3: 直接處理資料陣列

```python
from frame_processor_mlx90641 import FrameProcessorMLX90641
import json

# 初始化處理器
fp = FrameProcessorMLX90641()

# 您的資料（從 Supabase 或其他來源）
data_str = '["21.5853","21.1291",...]'  # 192 個值
data_array = json.loads(data_str)

# 處理
density_map = fp.process_frame(data_array)
people_count = fp.get_people_count_on_latest_frame()

print(f"偵測到人數: {people_count:.2f}")
```

## API 說明

### `SupabaseThermalProcessor`

#### `process_latest_frame(session_id: str, limit: int = 1)`

處理指定 session 的最新資料。

**參數：**
- `session_id`: 會話 ID
- `limit`: 要處理的記錄數量（預設為 1）

**返回：**
- 處理結果字典（如果 limit=1）或結果列表

#### `process_frame_by_id(frame_id: int)`

根據 ID 處理特定的資料。

**參數：**
- `frame_id`: 資料記錄的 ID

**返回：**
- 處理結果字典

#### `process_multiple_frames(session_id: str, limit: int = 10, start_time: str = None, end_time: str = None)`

處理多個資料。

**參數：**
- `session_id`: 會話 ID
- `limit`: 要處理的記錄數量上限
- `start_time`: 開始時間（ISO 格式，可選）
- `end_time`: 結束時間（ISO 格式，可選）

**返回：**
- 處理結果列表

#### `save_results_to_supabase(results, table_name='people_count_results', save_density_map=False)`

將處理結果儲存回 Supabase（混合方案）。

**參數：**
- `results`: 處理結果字典，應包含 'density_map' 和 'density_map_sum'
- `table_name`: 目標資料表名稱（預設: 'people_count_results'）
- `save_density_map`: 是否儲存密度圖（預設 False，節省空間）

**返回：**
- 儲存結果字典，如果失敗則返回 None

#### `get_density_map_for_frame(frame_id, cache_if_missing=False)`

獲取指定 frame 的密度圖（按需計算或讀取）。

**參數：**
- `frame_id`: 資料記錄的 ID
- `cache_if_missing`: 如果沒有儲存的密度圖，計算後是否儲存（預設 False）

**返回：**
- 24×32 的密度圖 numpy 陣列，如果找不到資料則返回 None

**使用範例：**

```python
# 獲取密度圖（會自動檢查是否有儲存）
density_map = processor.get_density_map_for_frame(
    frame_id=31768,
    cache_if_missing=True  # 如果沒有儲存，計算後自動快取
)
```

### `FrameProcessorMLX90641`

#### `process_frame(raw_frame)`

處理 12×16 的熱像儀資料。

**參數：**
- `raw_frame`: 192 個 float 的陣列（12×16 flatten）或 12×16 的 2D 陣列

**返回：**
- 24×32 的密度圖（numpy array）

#### `get_people_count_on_latest_frame()`

計算人數。

**返回：**
- 偵測到的人數（浮點數）

#### `save_results_to_supabase(results, table_name='people_count_results', save_density_map=False)`

將處理結果儲存回 Supabase（混合方案）。

**參數：**
- `results`: 處理結果字典，應包含 'density_map' 和 'density_map_sum'
- `table_name`: 目標資料表名稱
- `save_density_map`: 是否儲存密度圖（預設 False，節省空間）

**返回：**
- 儲存結果字典

#### `get_density_map_for_frame(frame_id, cache_if_missing=False)`

獲取指定 frame 的密度圖（按需計算或讀取）。

**參數：**
- `frame_id`: 資料記錄的 ID
- `cache_if_missing`: 如果沒有儲存的密度圖，計算後是否儲存（預設 False）

**返回：**
- 24×32 的密度圖 numpy 陣列，如果找不到資料則返回 None

## 注意事項

1. **解析度差異**：模型是針對 24×32 訓練的，而 MLX90641 是 12×16。程式會自動上採樣，但準確度可能會受到影響。

2. **模型檔案**：確保模型檔案存在於以下位置之一：
   - `../data_collection/src/trained_model/unet_v2_cpu1`
   - `../data_collection/src/trained_model/unet_gauss_model_cpu1`
   - `../data_collection/src/trained_model/unet_gauss_model_gpu1`

3. **溫度範圍**：模型期望輸入溫度範圍為 20-35°C，會自動正規化。

4. **Supabase 權限**：確保使用的 API key 有讀取 `thermal_frames` 資料表的權限。

## 範例輸出

```
==================================================
處理結果
==================================================
記錄 ID:        20082
會話 ID:        604_windowside
時間戳記:       2026-01-07 10:22:02.2732+00
偵測到人數:      0.85
偵測到人數(整數): 1
密度圖形狀:     (24, 32)
原始資料長度:   192
==================================================
```

## 疑難排解

### 找不到模型檔案

確保模型檔案存在，或使用 `--model-path` 參數指定路徑。

### Supabase 連線錯誤

檢查：
- Supabase URL 是否正確
- API key 是否有效
- 網路連線是否正常

### 資料格式錯誤

確保 Supabase 的 `data` 欄位包含正確的 192 個 float 值。

## 授權

與主專案相同。

