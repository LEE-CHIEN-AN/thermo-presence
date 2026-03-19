# YOLO 人數辨識訓練系統

使用現有的標註資料（`dataset/hdfs/`）建立 YOLO 物件偵測模型，用於熱影像人數辨識。

## 目錄結構

```
yolo_training/
├── export_dataset.py      # 資料匯出腳本
├── preprocess.py           # 前處理工具
├── validate_labels.py     # 標註驗證工具
├── train.py               # 訓練腳本（本地使用）
├── train_colab.ipynb      # Colab 訓練 Notebook（GPU 加速）
├── data.yaml              # YOLO 資料配置
├── requirements.txt       # 依賴套件
├── README.md             # 本檔案
└── dataset/              # 轉換後的 YOLO 格式資料
    ├── images/
    │   ├── train/
    │   ├── val/
    │   └── test/
    └── labels/
        ├── train/
        ├── val/
        └── test/
```

## 安裝

1. **建立虛擬環境（推薦）**：

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows PowerShell
# 或 source .venv/bin/activate 在 Linux/macOS
```

2. **安裝依賴套件**：

```bash
pip install -r requirements.txt
```

## 使用流程

### 1. 匯出資料集

將 HDF5 格式的資料轉換為 YOLO 格式：

```bash
python export_dataset.py
```

這會：
- 從 `dataset/hdfs/` 讀取所有 HDF5 檔案
- 將 24×32 熱影像上採樣為 192×256 RGB
- 將點座標轉換為 YOLO 格式的 bounding boxes
- 按照 train/val/test 分割組織資料
- 輸出到 `dataset/` 目錄

### 2. 驗證標註

檢查轉換後的標註檔是否正確：

```bash
# 驗證所有標註
python validate_labels.py

# 驗證特定分割
python validate_labels.py --split train

# 顯示詳細錯誤訊息
python validate_labels.py --verbose

# 視覺化檢查（在影像上繪製 bounding boxes）
python validate_labels.py --visualize train/007__13_22_20_000000
```

### 3. 訓練模型

開始訓練 YOLOv8 模型：

```bash
# 使用預設參數訓練
python train.py

# 自訂參數
python train.py --epochs 300 --batch 64 --lr 0.0005
```

訓練參數（參考論文最佳配置）：
- **Model**: YOLOv8n（輕量級）
- **Image size**: 192×256
- **Rectangular Training**: 啟用（`rect=True`），避免將非正方形影像墊補成正方形，節省運算資源
- **Epochs**: 200-300
- **Batch size**: 32
- **Learning rate**: 0.001
- **Optimizer**: Adam

### 4. 恢復訓練

如果訓練被中斷（例如電腦休眠、手動停止等），可以使用恢復訓練腳本從檢查點繼續：

```bash
# 方法 1: 自動從最新的檢查點恢復（推薦）
python resume_train.py

# 方法 2: 從指定的檢查點恢復
python resume_train.py --checkpoint runs/train/weights/last.pt

# 方法 3: 從特定 epoch 恢復並設定目標 epochs
python resume_train.py --checkpoint runs/train/weights/epoch50.pt --epochs 200

# 方法 4: 列出所有可用的檢查點
python resume_train.py --list
```

**恢復訓練腳本功能**：
- ✅ 自動尋找最新的檢查點（優先使用 `last.pt`）
- ✅ 顯示當前訓練進度和剩餘 epochs
- ✅ 顯示最新的訓練指標（Precision, Recall, mAP）
- ✅ 自動從中斷的地方繼續訓練
- ✅ 保持所有訓練參數一致

**注意事項**：
- 訓練被中斷時，YOLO 會自動保存 `last.pt`（最後一個 epoch 的狀態）
- 每 10 個 epochs 會自動保存檢查點（`epoch10.pt`, `epoch20.pt`, ...）
- 如果 `last.pt` 損壞，可以從最近的 epoch 檢查點恢復
- **不要讓電腦休眠**：建議設定電腦不休眠，或使用恢復功能

### 5. 驗證模型

在測試集上驗證訓練好的模型：

```bash
python train.py --mode val --model runs/train/weights/best.pt
```

**快速測試（訓練中斷時）**：

如果訓練還沒完成但需要測試，可以使用當前已保存的模型：

```bash
# 快速驗證（使用 best.pt）
python quick_test.py --mode val

# 只測試測試集
python quick_test.py --mode test

# 測試單張影像
python quick_test.py --mode image --image dataset/images/test/008__13_26_20_000000.png
```

## 使用 Google Colab 訓練（GPU 加速）

如果本地電腦沒有 GPU 或想要更快的訓練速度，可以使用 Google Colab 的免費 GPU。

### 使用 Colab Notebook

1. **開啟 Notebook**：
   - 在 VS Code 中開啟 `train_colab.ipynb`
   - 或直接上傳到 Google Colab

2. **在 VS Code 中使用 Colab Extension**：
   - 安裝 "Google Colab" extension
   - 開啟 `train_colab.ipynb`
   - 點選右上角的 Colab 圖示連接到 Colab
   - 上傳必要的檔案到 Colab

3. **上傳資料集**：
   - 將整個 `yolo_training` 資料夾上傳到 Colab
   - 或使用 Google Drive 掛載（推薦，適合大檔案）：
     ```python
     from google.colab import drive
     drive.mount('/content/drive')
     # 然後修改 WORK_DIR 路徑
     ```

4. **啟用 GPU**：
   - 在 Colab 中，點選 `執行階段` → `變更執行階段類型`
   - 選擇 `GPU`（T4 或 V100）

5. **執行 Cells**：
   - 按順序執行所有 cells
   - 訓練過程可能需要數小時

6. **下載結果**：
   - 訓練完成後執行下載 cell
   - 或從 Colab 左側檔案瀏覽器下載

### Colab 注意事項

- **時間限制**：Colab 免費版 GPU 使用時間有限（約 12 小時）
- **定期儲存**：建議定期儲存檢查點（每 10 epochs 自動儲存）
- **Batch Size**：在 GPU 上可以增加 batch size（例如 64 或 128）以加快訓練
- **斷線處理**：如果訓練中斷，可以從最後的檢查點繼續訓練

## 資料格式

### 輸入格式（HDF5）

- **熱影像**: 24×32 numpy array（溫度值，單位：°C）
- **點座標**: List of (x, y) tuples（人頭部中心點）

### 輸出格式（YOLO）

- **影像**: 192×256 RGB PNG（使用 JET colormap 的彩色熱力圖）
- **標註**: YOLO 格式文字檔（每行一個 bounding box）
  ```
  class_id x_center y_center width height
  ```
  所有座標都是 normalized [0, 1]

## 資料轉換細節

### 影像轉換

1. **上採樣**: 24×32 → 192×256（保持 aspect ratio，8倍放大）
2. **正規化**: 溫度範圍 20-35°C → 0-255
3. **Grayscale → RGB**: 使用 JET colormap 轉換為彩色熱力圖（與論文中的圖片一致）
   - 低溫區域：藍色/紫色
   - 高溫區域：黃色/紅色
   - 這有助於 YOLO 模型更好地識別熱源特徵

### 標註轉換

- **點座標 → Bounding Box**: 
  - **自適應大小**（預設）：根據熱源區域自動檢測並調整 bounding box 大小
    - **每個熱點獨立檢測**：同一張圖中每個熱點會根據其實際熱源區域大小得到不同的 bounding box
    - **在原圖上檢測**：在原始 24×32 解析度的熱影像上檢測 bounding box 大小（更準確）
    - **區域生長方法**：使用區域生長（region growing）方法檢測每個熱源的實際範圍
    - **溫度閾值**：根據每個熱點中心溫度的 70% 作為閾值，確定該熱源的邊界
    - **大小範圍**：bounding box 大小範圍為 3×3 到 10×10 像素（在原始解析度下）
    - **座標轉換**：檢測到的大小轉換為 normalized [0, 1] 座標，應用到放大後的 192×256 影像
    - 自動調整大小，更符合實際熱源形狀（與論文中的可變大小 bounding boxes 一致）
  - **固定大小**（可選）：使用固定 6×6 像素的 bounding box
- **座標轉換**: 24×32 → normalized [0, 1]
- **自動裁剪**: 超出影像範圍的 bounding box 會自動裁剪到影像邊界

## 訓練結果

訓練完成後，結果會儲存在 `runs/train/` 目錄：

- `weights/best.pt`: 最佳模型（根據驗證集 mAP）
- `weights/last.pt`: 最後一個 epoch 的模型
- `results.png`: 訓練曲線圖
- `confusion_matrix.png`: 混淆矩陣
- `*.jpg`: 驗證結果視覺化

## 注意事項

1. **Bounding Box 大小**: 預設為 6×6 像素，可能需要根據實際人頭部熱訊號大小調整
2. **資料品質**: 確保 HDF5 檔案中的標註資料完整
3. **記憶體需求**: 訓練時需要足夠的記憶體（建議至少 8GB RAM）
4. **GPU 加速**: 如果有 GPU，YOLOv8 會自動使用 GPU 加速訓練

## 參考論文

- Mapping Thermal Footprints: Occupancy Estimation and Localization in Diverse Indoor Settings with Thermal Arrays
- 論文使用 YOLOv5s，本實作使用 YOLOv8n（更輕量級）

## 疑難排解

### 問題：找不到 HDF5 檔案

**解決**: 確保 `dataset/hdfs/` 目錄存在且包含 `.h5` 檔案

### 問題：記憶體不足

**解決**: 減少 batch size（例如 `--batch 16`）

### 問題：訓練 loss 不下降

**解決**: 
- 檢查資料品質和標註是否正確
- 調整 learning rate
- 增加訓練 epochs

### 問題：驗證時找不到模型

**解決**: 確保訓練已完成，模型檔案存在於 `runs/train/weights/best.pt`

## Web Dashboard 整合

訓練好的 YOLO 模型可以整合到 `web_dashboard` 中進行即時偵測：

- **後端** (`web_dashboard/backend/app/services/thermal_service.py`): 自動載入 YOLO 模型並執行偵測
- **前端** (`web_dashboard/frontend/src/components/YOLODetectionViewer.tsx`): 顯示 192×256 上採樣圖像與 YOLO bounding boxes
- **需求**: 
  - `ultralytics>=8.0.0` 必須安裝在後端虛擬環境中
  - 模型權重檔案必須存在於 `yolo_training/runs/train/weights/best.pt` 或 `last.pt`

詳細說明請參考 `web_dashboard/README.md`。
