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

Then start FastAPI:

```bash
cd web_dashboard/backend
uvicorn app.main:app --reload --port 8000
```

The API root will be available at:

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/docs` (Swagger UI)

Key endpoints for the first phase (thermal only):

- `GET /api/realtime/thermal-latest?session_id=604_windowside`
- `GET /api/realtime/thermal-by-id?frame_id=123`
- `GET /api/history/thermal?session_id=604_windowside&limit=100`

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
        ThermalImageViewer.tsx
        DensityMapViewer.tsx
      pages/
        Dashboard.tsx       # Realtime people count + density map
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
  - a 24×32 **density map**
- **Left**: density map rendered as a colored grid (`DensityMapViewer`)
- **Right**: people count card (big integer, small float value, timestamp)
- A placeholder block for the thermal raw frame (to be wired once a raw-frame API is added)

---

## 3. Next steps

Planned future work (as per the high-level plan):

- Add a raw thermal frame API and connect it to a proper `ThermalImageViewer`
- Add environment sensor integration from `wiolink` table (CO₂, TVOC, PM, light, window state)
- Add IAQI / PMV / PPD badges and long-term trend charts (Recharts)
- Add heatmaps (temperature, humidity, PMV, PPD) over the classroom floor plan



