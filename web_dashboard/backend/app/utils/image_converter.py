from typing import Literal

import numpy as np


def normalize_to_uint8(array: np.ndarray, vmin: float, vmax: float) -> np.ndarray:
    """
    Normalize a float array to uint8 in [0, 255].
    """
    clipped = np.clip(array, vmin, vmax)
    norm = (clipped - vmin) / (vmax - vmin) if vmax > vmin else clipped * 0
    return (norm * 255).astype(np.uint8)


def thermal_to_uint8_image(frame: np.ndarray, vmin: float = 20.0, vmax: float = 35.0) -> np.ndarray:
    """
    Convert a thermal frame (temperature values) to a uint8 grayscale image.
    The actual colormap is applied on the frontend.
    """
    return normalize_to_uint8(frame, vmin=vmin, vmax=vmax)


def density_to_uint8_image(density: np.ndarray, scale: float = 1.0) -> np.ndarray:
    """
    Convert a density map to uint8 grayscale image.
    """
    vmax = float(np.max(density)) if density.size > 0 else 1.0
    return normalize_to_uint8(density * scale, vmin=0.0, vmax=max(vmax * scale, 1e-6))



