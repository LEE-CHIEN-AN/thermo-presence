from typing import Any, Dict, List, Optional
import os
import base64
import io
from datetime import datetime, timezone

import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from PIL import Image
from pythermalcomfort.models import pmv_ppd_ashrae
from pythermalcomfort.utilities import v_relative

from app.services.environment_service import EnvironmentService


class EnvironmentHeatmapService:
    """
    Service for generating PMV/PPD heatmaps from environmental sensor data.
    """

    # Sensor coordinates in cm (x, y)
    SENSOR_COORD_MAP = {
        "604_window": [180, 0],
        "604_wall": [688, 215],
        "604_door": [500, 678],
        "604_air_quality": [0, 305],
        "604_center": [300, 400]
    }

    SENSOR_SHORT_NAMES = {
        "604_window": "Window",
        "604_door": "Door",
        "604_wall": "Wall",
        "604_air_quality": "iMac",
        "604_center": "Center"
    }

    # Room dimensions in cm
    XMAX, YMAX = 688, 687

    # PMV/PPD calculation parameters
    MET = 1.1  # Metabolic rate (typing activity)
    CLO = 0.5  # Clothing insulation (summer light clothing)
    V = 0.1    # Air velocity (m/s)

    def __init__(self, env_service: Optional[EnvironmentService] = None):
        self.env_service = env_service or EnvironmentService()

    def _idw_interpolation(self, x: np.ndarray, y: np.ndarray, points: np.ndarray, values: np.ndarray, power: int = 2) -> np.ndarray:
        """
        Inverse Distance Weighting interpolation.
        """
        z = np.zeros_like(x)
        for i in range(x.shape[0]):
            for j in range(x.shape[1]):
                dists = np.sqrt((points[:, 0] - x[i, j])**2 + (points[:, 1] - y[i, j])**2)
                dists = np.where(dists == 0, 1e-10, dists)
                weights = 1 / dists**power
                z[i, j] = np.sum(weights * values) / np.sum(weights)
        return z

    def _get_latest_sensor_data(self) -> tuple[List[Dict[str, Any]], Optional[datetime]]:
        """
        Fetch latest temperature and humidity data for all sensors.
        Returns (data_list, latest_time).
        """
        sensor_names = list(self.SENSOR_COORD_MAP.keys())
        latest_data = []
        times = []

        for name in sensor_names:
            # Get latest data for this sensor
            latest = self.env_service.get_latest(sensor_name=name)
            if not latest:
                continue

            # Find first valid temperature reading
            for row in latest:
                temp = row.get("celsius_degree")
                humidity = row.get("humidity")
                if temp is not None and not np.isnan(temp):
                    coord = self.SENSOR_COORD_MAP[name]
                    latest_data.append({
                        "sensor_name": name,
                        "time": row["time"],
                        "temperature": float(temp),
                        "humidity": float(humidity) if humidity is not None and not np.isnan(humidity) else None,
                        "x": coord[0],
                        "y": coord[1]
                    })
                    try:
                        time_str = row["time"]
                        if time_str.endswith('Z'):
                            time_str = time_str.replace('Z', '+00:00')
                        times.append(datetime.fromisoformat(time_str))
                    except Exception:
                        # Skip invalid timestamps
                        pass
                    break

        if not latest_data:
            return [], None

        latest_time = min(times) if times else None
        # Keep UTC time - frontend will handle timezone conversion
        return latest_data, latest_time

    def _calculate_pmv_ppd(self, temperature: float, humidity: float) -> tuple[float, float]:
        """
        Calculate PMV and PPD for given temperature and humidity.
        """
        import warnings
        try:
            # Suppress cooling effect warnings from pythermalcomfort
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", message=".*Cooling effect.*")
                result = pmv_ppd_ashrae(
                    tdb=temperature,
                    tr=temperature,  # Assume radiant temperature equals air temperature
                    rh=humidity if humidity is not None else 50.0,
                    vr=v_relative(v=self.V, met=self.MET),
                    met=self.MET,
                    clo=self.CLO
                )
            return float(result.pmv), float(result.ppd)
        except Exception:
            # Return default values if calculation fails
            return 0.0, 5.0

    def _load_floor_plan(self) -> Optional[np.ndarray]:
        """
        Load and flip the floor plan image.
        """
        # Try to find floor plan image
        # __file__ is: web_dashboard/backend/app/services/environment_heatmap_service.py
        # We need to go up 4 levels to reach repo root: thermo-presence/
        current_dir = os.path.dirname(os.path.abspath(__file__))
        repo_root = os.path.abspath(os.path.join(current_dir, "..", "..", "..", ".."))
        
        # Try different possible paths (prioritize 604vlab-movebackground.png)
        possible_paths = [
            os.path.join(repo_root, "web_dashboard", "604vlab-movebackground.png"),
            os.path.join(repo_root, "web_dashboard", "604vlab-去背.png"),
            os.path.join(repo_root, "web_dashboard", "604vlab-2.png"),
            os.path.join(repo_root, "supabase_integration", "604vlab-2.png"),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                try:
                    floor_img = Image.open(path).convert("RGBA")
                    # Flip top-bottom (圖片原點通常在左上、熱力圖在左下)
                    floor_img = floor_img.transpose(Image.FLIP_TOP_BOTTOM)
                    floor_arr = np.array(floor_img)
                    print(f"[DEBUG] Successfully loaded floor plan from: {path}, shape: {floor_arr.shape}")
                    return floor_arr
                except Exception as e:
                    print(f"[DEBUG] Failed to load floor plan from {path}: {e}")
                    continue
        
        print("[DEBUG] No floor plan image found in any of the paths")
        return None

    def _generate_heatmap_image(
        self,
        grid_z: np.ndarray,
        data_points: List[Dict[str, Any]],
        cmap: str,
        vmin: float,
        vmax: float,
        title: str,
        label: str,
        show_pmv_ppd: bool = False,
        show_contour: bool = False,
        contour_level: Optional[float] = None
    ) -> str:
        """
        Generate a heatmap image and return as base64 string.
        """
        fig, ax = plt.subplots(figsize=(10, 7))
        
        # Draw heatmap (底：熱力圖)
        norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
        # Get colormap and reverse if it's Spectral (for PMV/PPD)
        if cmap == 'Spectral':
            cmap_obj = plt.get_cmap(cmap).reversed()
        else:
            cmap_obj = plt.get_cmap(cmap)
        img = ax.imshow(
            grid_z,
            extent=(0, self.XMAX, 0, self.YMAX),
            origin='lower',
            cmap=cmap_obj,
            norm=norm,
            aspect='equal',
            zorder=0
        )
        
        # Draw contour if requested (before floor plan)
        if show_contour and contour_level is not None:
            # Create grid matching the heatmap dimensions
            ny, nx = grid_z.shape
            grid_x_contour, grid_y_contour = np.meshgrid(
                np.linspace(0, self.XMAX, nx),
                np.linspace(0, self.YMAX, ny)
            )
            cs = ax.contour(
                grid_x_contour, grid_y_contour, grid_z,
                levels=[contour_level],
                colors="red",
                linewidths=1.8,
                zorder=2
            )
            # Format contour label
            if "PPD" in label:
                fmt_str = f"PPD={contour_level:.0f}%%"
            else:
                fmt_str = f"{label}={contour_level}"
            ax.clabel(cs, inline=True, fmt=fmt_str, fontsize=9)
        
        # Draw sensor points and labels (點與標註)
        scatter_handles = []
        for point in data_points:
            x, y = point["x"], point["y"]
            short_name = self.SENSOR_SHORT_NAMES.get(point["sensor_name"], point["sensor_name"])
            
            scatter = ax.scatter(x, y, c='white', edgecolors='black', s=50, zorder=3, label='Sensors')
            if not scatter_handles:
                scatter_handles.append(scatter)
            
            if show_pmv_ppd:
                pmv = point.get("pmv", 0.0)
                ppd = point.get("ppd", 0.0)
                # For PMV heatmap, show only PMV; for PPD heatmap, show both
                if point.get("show_pmv_only", False):
                    ax.text(
                        x - 35, y + 12,
                        f"{short_name}\nPMV={pmv:.2f}",
                        color="black",
                        fontsize=9,
                        weight="bold",
                        zorder=4
                    )
                else:
                    ax.text(
                        x - 35, y + 12,
                        f"{short_name}\nPMV={pmv:.2f}\nPPD={ppd:.1f}%",
                        color="black",
                        fontsize=9,
                        weight="bold",
                        zorder=4
                    )
            else:
                if "temperature" in point:
                    ax.text(
                        x - 15, y + 10,
                        f"{short_name}\n{point['temperature']:.1f}°C",
                        color='black',
                        fontsize=9,
                        weight='bold',
                        zorder=4
                    )
                elif "humidity" in point:
                    ax.text(
                        x - 15, y + 10,
                        f"{short_name}\n{point['humidity']:.0f}%",
                        color='black',
                        fontsize=9,
                        weight='bold',
                        zorder=4
                    )
        
        # Overlay floor plan (疊：平面圖，最後疊加)
        floor_arr = self._load_floor_plan()
        if floor_arr is not None:
            ax.imshow(
                floor_arr,
                extent=(0, self.XMAX, 0, self.YMAX),
                origin='lower',
                alpha=0.5,  # FLOOR_ALPHA = 0.5
                zorder=1  # 在熱力圖之上，但在點和標註之下
            )
        
        # Colorbar - use fig.colorbar to avoid warning
        cbar = fig.colorbar(img, ax=ax, label=label)
        if "PMV" in label:
            cbar.set_ticks(np.arange(-3, 4, 1))
        elif "PPD" in label:
            cbar.set_ticks(np.arange(5, 51, 5))
        elif "Temperature" in label:
            cbar.set_ticks(np.arange(20, 31, 1))
        elif "Humidity" in label:
            cbar.set_ticks(np.arange(0, 105, 5))
        
        ax.set_title(title, pad=20)
        ax.set_xlabel("X (cm)")
        ax.set_ylabel("Y (cm)")
        ax.set_aspect('equal', adjustable='box')
        # Only add legend if we have labeled artists
        if scatter_handles:
            ax.legend(handles=scatter_handles, loc='lower right')
        plt.tight_layout()
        
        # Convert to base64
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        plt.close(fig)
        
        return img_base64

    def get_pmv_ppd_heatmaps(self) -> Dict[str, Any]:
        """
        Generate PMV and PPD heatmaps from latest sensor data.
        Returns dict with 'pmv_image', 'ppd_image', and 'timestamp'.
        """
        # Get latest sensor data
        data_points, latest_time = self._get_latest_sensor_data()
        
        if not data_points:
            raise ValueError("No valid sensor data found")
        
        # Filter out points without humidity (needed for PMV/PPD calculation)
        valid_points = [p for p in data_points if p.get("humidity") is not None]
        if not valid_points:
            raise ValueError("No sensor data with humidity found")
        
        # Calculate PMV and PPD for each sensor
        for point in valid_points:
            pmv, ppd = self._calculate_pmv_ppd(
                point["temperature"],
                point["humidity"]
            )
            point["pmv"] = pmv
            point["ppd"] = ppd
        
        # Prepare interpolation grid
        grid_x, grid_y = np.meshgrid(
            np.linspace(0, self.XMAX, 200),
            np.linspace(0, self.YMAX, 200)
        )
        
        # Prepare points and values for IDW
        points_array = np.array([[p["x"], p["y"]] for p in valid_points])
        pmv_values = np.array([p["pmv"] for p in valid_points])
        ppd_values = np.array([p["ppd"] for p in valid_points])
        
        # Interpolate
        grid_z_pmv = self._idw_interpolation(grid_x, grid_y, points_array, pmv_values)
        grid_z_ppd = self._idw_interpolation(grid_x, grid_y, points_array, ppd_values)
        
        # Generate images
        # For PMV heatmap, show only PMV values
        pmv_points = [{**p, "show_pmv_only": True} for p in valid_points]
        pmv_image = self._generate_heatmap_image(
            grid_z_pmv,
            pmv_points,
            cmap='Spectral',
            vmin=-3,
            vmax=3,
            title="Classroom 604 PMV Heatmap over Floor Plan",
            label="PMV",
            show_pmv_ppd=True
        )
        
        ppd_image = self._generate_heatmap_image(
            grid_z_ppd,
            valid_points,
            cmap='Spectral',
            vmin=5,
            vmax=50,
            title="Classroom 604 PPD Heatmap over Floor Plan",
            label="PPD (%)",
            show_pmv_ppd=True,
            show_contour=True,
            contour_level=20.0
        )
        
        return {
            "pmv_image": pmv_image,
            "ppd_image": ppd_image,
            "timestamp": latest_time.isoformat() if latest_time else None
        }
