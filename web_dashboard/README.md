# Thermal Presence Web Dashboard

This directory contains a new web dashboard for the `thermo-presence` project:

- **Backend**: FastAPI (Python)
- **Frontend**: React + TypeScript + Vite + Tailwind CSS
- **Data source**: Supabase (`thermal_frames`, `people_count_results`, `wiolink`) via the existing `supabase_integration` code

The goal is to show **people count, density maps, and (later) environmental sensor data** in a browser.

---

## 1. Backend (FastAPI)

### 1.1. Project layout

```text
web_dashboard/
  backend/
    app/
      __init__.py
      main.py              # FastAPI entrypoint (app)
      api/
        realtime.py        # /api/realtime/*
        history.py         # /api/history/*
        statistics.py      # /api/statistics/*
        environment.py     # /api/environment/*
        integrated.py      # /api/integrated/*
        heatmap.py         # /api/heatmap/*
      services/
        thermal_service.py       # wraps SupabaseThermalProcessor
        environment_service.py   # reads from wiolink (will be extended later)
        integrated_service.py    # combines thermal + environment data
        visualization_service.py # statistics / analytics (placeholder)
      utils/
        image_converter.py # helpers for normalizing frames/density to uint8
    requirements.txt
```

The backend **reuses** the existing `supabase_integration` package from the repo root, so it assumes this directory structure:

```text
thermo-presence/
  supabase_integration/
  web_dashboard/
    backend/
      app/...
```

### 1.2. Setup & run

From the repository root:

```bash
cd web_dashboard/backend
python -m venv .venv
.venv\Scripts\activate  # Windows PowerShell
# 或 source .venv/bin/activate 在 Linux/macOS

pip install -r requirements.txt
```

Make sure you already have a `.env` file at the **repo root** (or somewhere that `supabase_integration` expects) containing:

```env
SUPABASE_URL=...
SUPABASE_KEY=...
```

**For production deployment (Render/Zeabur):**

If deploying the frontend separately, you may need to set environment variables:

```env
FRONTEND_URL=https://your-frontend-domain.com  # Optional, defaults to localhost:5173
ZEABUR_URL=https://your-zeabur-domain.com       # Optional, for Zeabur deployments
```

The backend CORS configuration automatically allows:
- `http://localhost:5173` (development)
- `https://604thermalcamera.zeabur.app` (production frontend)
- Any URL set via `FRONTEND_URL` or `ZEABUR_URL` environment variables

Then start FastAPI:

```bash
cd web_dashboard/backend
uvicorn app.main:app --reload --port 8000
```

The API root will be available at:

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/docs` (Swagger UI)

Key endpoints:

- `GET /api/realtime/thermal-latest?session_id=604_windowside` - Latest thermal frame with U-Net and YOLO detection
- `GET /api/realtime/thermal-by-id?frame_id=123` - Specific thermal frame by ID
- `GET /api/history/thermal?session_id=604_windowside&limit=100` - Historical thermal frames
- `GET /api/realtime/pmv-ppd-heatmaps` - PMV/PPD heatmaps

**YOLO Detection**: The backend automatically runs YOLO detection on thermal images if:
- `ultralytics` package is installed
- YOLO model weights exist at `yolo_training/runs/train/weights/best.pt` or `last.pt`
- Returns `yolo_detection` (bounding boxes) and `yolo_thermal_image` (192×256 upsampled image) in the API response

---

## 2. Frontend (React + Vite)

### 2.1. Project layout

```text
web_dashboard/
  frontend/
    index.html
    package.json
    tsconfig.json
    vite.config.ts
    tailwind.config.cjs
    postcss.config.cjs
    src/
      main.tsx
      App.tsx
      index.css
      services/
        api.ts              # Axios client for backend APIs
      components/
        ThermalImageViewer.tsx      # IR frame visualization
        DensityMapViewer.tsx        # U-Net density map visualization
        YOLODetectionViewer.tsx    # YOLO detection with bounding boxes
        Colorbar.tsx               # Color scale legend
        RoomLayoutOverlay.tsx      # Room layout overlay
      pages/
        Dashboard.tsx               # Realtime people count + IR frame + density map + YOLO
```

### 2.2. Setup & run

From the repository root:

```bash
cd web_dashboard/frontend
npm install
npm run dev
```

This starts Vite dev server at:

- `http://127.0.0.1:5173/`

The Vite config proxies `/api` to the FastAPI backend at `http://127.0.0.1:8000`, so make sure the backend is running first.

### 2.3. What the Dashboard currently shows

On the `Dashboard` page (`/`):

- A session ID input (default: `604_windowside`)
- Every 10 seconds it calls `GET /api/realtime/thermal-latest` to fetch:
  - `frame_id`, `timestamp`
  - `people_count` (float) and `people_count_rounded` (int)
  - a 24×32 **thermal image** (IR frame)
  - a 24×32 **density map** (Network output)
  - YOLO detection results with bounding boxes (if YOLO model is available)
- **Top**: Predicted people count with frame details (Frame ID, raw count, timestamp)
- **Main panels** (3 columns):
  - **Left**: IR frame (24×32 thermal image with viridis colormap)
  - **Middle**: Network output (24×32 density map from U-Net)
  - **Right**: YOLO detection (192×256 upsampled thermal image with YOLO bounding boxes overlay)
- **Bottom**: PMV/PPD heatmaps (if available)

---

## 3. YOLO Integration

The dashboard now includes YOLO-based people detection alongside the existing U-Net density estimation:

- **Backend**: `thermal_service.py` automatically runs YOLO detection on thermal images
- **Frontend**: `YOLODetectionViewer` component displays upsampled thermal images (192×256) with YOLO bounding boxes
- **Requirements**: 
  - `ultralytics>=8.0.0` must be installed in the backend virtual environment
  - YOLO model weights must exist at `yolo_training/runs/train/weights/best.pt` or `last.pt`
- **Visualization**: YOLO panel shows the same thermal image as IR frame but upsampled to match YOLO's detection resolution (192×256)

## 4. Next steps

Planned future work:

- Add environment sensor integration from `wiolink` table (CO₂, TVOC, PM, light, window state)
- Add IAQI / PMV / PPD badges and long-term trend charts (Recharts)
- Add heatmaps (temperature, humidity, PMV, PPD) over the classroom floor plan
- Compare U-Net vs YOLO detection accuracy metrics



