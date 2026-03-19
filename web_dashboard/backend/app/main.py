import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


# Ensure the repository root is on sys.path so we can import supabase_integration.*
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.append(REPO_ROOT)


app = FastAPI(
    title="Thermal Presence Dashboard API",
    description="Backend API for thermal presence detection and visualization.",
    version="0.1.0",
)


# CORS configuration
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
ZEABUR_URL = os.getenv("ZEABUR_URL", "")

# 收集所有允許的來源，過濾掉空字串
allowed_origins = [
    FRONTEND_URL,
    "http://localhost:5173",  # 開發環境
    "https://604thermalcamera.zeabur.app",  # Zeabur 前端部署 URL
]

# 如果環境變數有設定，也加入
if ZEABUR_URL:
    allowed_origins.append(ZEABUR_URL)

# 過濾掉空字串
allowed_origins = [origin for origin in allowed_origins if origin]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Routers
from .api import realtime, history, statistics, environment, integrated, heatmap  # noqa: E402

app.include_router(realtime.router, prefix="/api/realtime", tags=["realtime"])
app.include_router(history.router, prefix="/api/history", tags=["history"])
app.include_router(statistics.router, prefix="/api/statistics", tags=["statistics"])
app.include_router(environment.router, prefix="/api/environment", tags=["environment"])
app.include_router(integrated.router, prefix="/api/integrated", tags=["integrated"])
app.include_router(heatmap.router, prefix="/api/heatmap", tags=["heatmap"])


@app.get("/")
def read_root():
    return {"message": "Thermal Presence Dashboard API is running"}



