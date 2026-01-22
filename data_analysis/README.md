# 數據分析模組

本目錄包含用於分析 Supabase 中熱影像人數偵測和環境感測器數據的 Jupyter Notebook。

## 目錄結構

```
data_analysis/
├── notebooks/
│   └── data_analysis.ipynb    # 主要分析 Notebook
├── requirements.txt            # Python 依賴套件
└── README.md                   # 本檔案
```

## 功能

本 Notebook 提供以下分析功能：

1. **時間序列分析**
   - 人數隨時間的變化趨勢
   - 環境參數（溫度、濕度、CO2、VOC、PM）隨時間的變化
   - 多變數時間序列對比

2. **相關性分析**
   - 人數與各環境參數的相關係數矩陣
   - 散點圖矩陣
   - 熱力圖顯示相關性強度

3. **統計分析**
   - 人數和環境參數的統計摘要
   - 異常值檢測
   - 分時段統計（按小時）

4. **進階分析**
   - 人數與環境參數的迴歸分析
   - 預測模型評估

## 安裝與設置

### 1. 安裝依賴套件

```bash
# 在專案根目錄
cd data_analysis
pip install -r requirements.txt
```

### 2. 設置環境變數

確保專案根目錄有 `.env` 檔案，包含：

```env
SUPABASE_URL=your-supabase-url
SUPABASE_KEY=your-supabase-key
```

### 3. 啟動 Jupyter Notebook

```bash
# 在 data_analysis 目錄下
jupyter notebook notebooks/data_analysis.ipynb
```

或使用 Jupyter Lab：

```bash
jupyter lab notebooks/data_analysis.ipynb
```

## 數據來源

Notebook 從 Supabase 讀取兩張表：

### `people_count_results` 表
- `id`: 記錄 ID
- `frame_id`: 對應的熱影像 frame ID
- `session_id`: 會話 ID（例如：'604_windowside'）
- `timestamp`: 時間戳記
- `people_count`: 偵測到的人數（浮點數）
- `people_count_rounded`: 四捨五入後的人數（整數）
- `density_map_sum`: 密度圖總和
- `density_map`: 密度圖數據（可選）
- `has_density_map`: 是否包含密度圖
- `created_at`: 記錄創建時間

### `wiolink` 表（環境感測器）
- `id`: 記錄 ID
- `time`: 時間戳記
- `name`: 感測器名稱（例如：'604_air_quality', '604_window', '604_center', '604_wall', '604_door'）
- `humidity`: 濕度 (%)
- `light_intensity`: 光強度
- `celsius_degree`: 溫度 (°C)
- `mag_approach`: 磁感應（窗戶開關狀態）
- `dust`: 灰塵
- `total_voc`: 總揮發性有機化合物 (ppb)
- `co2eq`: CO2 等效濃度 (ppm)
- `pm1_0_atm`: PM1.0 (μg/m³)
- `pm2_5_atm`: PM2.5 (μg/m³)
- `pm10_atm`: PM10 (μg/m³)
- `touch_add`: 觸控增加
- `touch_minus`: 觸控減少

## 使用說明

1. **執行所有 Cells**：按順序執行 Notebook 中的所有 cells
2. **自訂分析**：可以修改 cells 來調整分析參數或添加新的分析
3. **導出結果**：圖表可以手動儲存，或使用 `plt.savefig()` 導出

## 注意事項

- **時區**：Supabase 使用 UTC 時區，如需本地時區請自行轉換
- **缺失值**：某些環境感測器欄位可能為空，Notebook 會自動處理
- **數據量**：如果數據量很大，可能需要添加時間範圍篩選
- **感測器名稱**：不同感測器有不同的名稱，Notebook 會自動識別

## 擴展

可以添加以下功能：

- 更多視覺化類型（互動式圖表、3D 圖表等）
- 機器學習預測模型
- 時間序列預測（ARIMA、LSTM 等）
- 聚類分析
- 異常檢測的進階方法

## 授權

與主專案相同。
