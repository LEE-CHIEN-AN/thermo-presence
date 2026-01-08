# 部署指南：Zeabur + Render

本指南說明如何使用 Zeabur 部署前端，Render 部署後端。

---

## 📋 前置準備

1. 確保所有代碼已推送到 GitHub
2. 準備 Supabase 憑證：
   - `SUPABASE_URL`
   - `SUPABASE_KEY`

---

## 🚀 第一部分：Render 部署後端

### 步驟 1: 註冊 Render 帳號
1. 前往 https://render.com
2. 使用 GitHub 帳號登入

### 步驟 2: 創建 Web Service
1. 點擊 "New +" → "Web Service"
2. 選擇 "Build and deploy from a Git repository"
3. 連接您的 GitHub 倉庫
4. 選擇 `feature/supabase-integration` 分支（或您要部署的分支）

### 步驟 3: 配置服務設置
- **Name**: `thermal-presence-backend`
- **Environment**: `Python 3`
- **Region**: 選擇離您最近的區域（如 `Singapore`）
- **Branch**: `feature/supabase-integration`（或您的主分支）
- **Root Directory**: 留空（使用倉庫根目錄）
- **Build Command**: 
  ```bash
  cd web_dashboard/backend && pip install -r requirements.txt
  ```
- **Start Command**: 
  ```bash
  cd web_dashboard/backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT
  ```

### 步驟 4: 設置環境變數
在 "Environment" 區塊添加以下環境變數：

```
SUPABASE_URL=your_supabase_url_here
SUPABASE_KEY=your_supabase_key_here
FRONTEND_URL=https://your-zeabur-frontend-url.zeabur.app
PYTHONPATH=/opt/render/project/src
```

**注意**：`FRONTEND_URL` 需要等前端部署完成後再更新。

### 步驟 5: 部署
1. 點擊 "Create Web Service"
2. 等待構建和部署完成（約 5-10 分鐘）
3. 記下後端 URL（例如：`https://thermal-presence-backend.onrender.com`）

---

## 🎨 第二部分：Zeabur 部署前端

### 步驟 1: 註冊 Zeabur 帳號
1. 前往 https://zeabur.com
2. 使用 GitHub 帳號登入

### 步驟 2: 創建新專案
1. 點擊 "New Project"
2. 選擇 "Import from GitHub"
3. 選擇您的倉庫

### 步驟 3: 添加前端服務
1. 在專案中點擊 "Add Service"
2. 選擇 "Static Site" 或 "Node.js"
3. 選擇您的 GitHub 倉庫

### 步驟 4: 配置服務設置
- **Root Directory**: `web_dashboard/frontend`
- **Build Command**: `npm install && npm run build`
- **Output Directory**: `dist`
- **Framework Preset**: `Vite`（如果可選）

### 步驟 5: 設置環境變數
在 "Environment Variables" 區塊添加：

```
VITE_API_URL=https://your-backend-url.onrender.com
```

**注意**：將 `your-backend-url.onrender.com` 替換為您在 Render 上獲得的後端 URL。

### 步驟 6: 部署
1. 點擊 "Deploy"
2. 等待構建和部署完成（約 3-5 分鐘）
3. 記下前端 URL（例如：`https://your-project.zeabur.app`）

### 步驟 7: 更新後端 CORS
回到 Render 後端設置：
1. 進入 "Environment" 區塊
2. 更新 `FRONTEND_URL` 環境變數為 Zeabur 前端 URL：
   ```
   FRONTEND_URL=https://your-project.zeabur.app
   ```
3. 點擊 "Save Changes"，Render 會自動重新部署

---

## ✅ 驗證部署

### 檢查後端
訪問後端 URL：
- `https://your-backend-url.onrender.com/` - 應該返回 `{"message": "Thermal Presence Dashboard API is running"}`
- `https://your-backend-url.onrender.com/docs` - 應該顯示 Swagger UI

### 檢查前端
訪問前端 URL：
- `https://your-project.zeabur.app` - 應該顯示 Dashboard 頁面

### 測試 API 連接
1. 打開前端頁面
2. 打開瀏覽器開發者工具（F12）
3. 切換到 "Network" 標籤
4. 檢查 API 請求是否成功（應該返回 200 狀態碼）

---

## 🔧 常見問題排除

### 問題 1: 前端構建失敗 - "Could not resolve entry module index.html"
**解決方案**：
- 確認 `index.html` 已提交到 Git
- 確認 Zeabur 的 Root Directory 設置為 `web_dashboard/frontend`

### 問題 2: CORS 錯誤
**解決方案**：
- 確認 Render 後端的 `FRONTEND_URL` 環境變數是正確的前端 URL
- 確認前端 URL 包含 `https://` 協議

### 問題 3: API 請求失敗
**解決方案**：
- 確認前端的 `VITE_API_URL` 環境變數指向正確的後端 URL
- 確認後端服務正在運行（檢查 Render 儀表板）

### 問題 4: 模型文件找不到
**解決方案**：
- 確認模型文件在 Git 倉庫中
- 檢查相對路徑是否正確（從 `web_dashboard/backend` 目錄）

### 問題 5: Render 後端構建失敗
**解決方案**：
- 檢查 `requirements.txt` 是否包含所有依賴
- 確認 Python 版本兼容（建議 Python 3.11+）
- 查看 Render 構建日誌中的錯誤訊息

---

## 📝 環境變數清單

### Render 後端環境變數
```
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
FRONTEND_URL=https://your-project.zeabur.app
PYTHONPATH=/opt/render/project/src
```

### Zeabur 前端環境變數
```
VITE_API_URL=https://your-backend-url.onrender.com
```

---

## 🔄 更新部署

當您推送新的代碼到 GitHub 時：
- **Render**: 會自動檢測變更並重新部署（可能需要手動觸發）
- **Zeabur**: 會自動檢測變更並重新部署

---

## 💡 提示

1. **免費方案限制**：
   - Render 免費方案在 15 分鐘無活動後會休眠，首次請求會較慢
   - Zeabur 免費方案有使用限制

2. **性能優化**：
   - 考慮使用 Render 的付費方案以獲得更好的性能
   - 可以設置健康檢查端點來保持服務活躍

3. **監控**：
   - 使用 Render 和 Zeabur 的內建監控功能
   - 設置錯誤通知

---

## 📚 相關文件

- [Render 文檔](https://render.com/docs)
- [Zeabur 文檔](https://zeabur.com/docs)
- [Vite 部署指南](https://vite.dev/guide/static-deploy.html)

