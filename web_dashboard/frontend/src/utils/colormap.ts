/**
 * Viridis colormap implementation for thermal and density visualization
 * Based on matplotlib's viridis colormap
 */

export function viridisColorMap(value: number, min: number, max: number): string {
  // Normalize value to [0, 1]
  const normalized = Math.max(0, Math.min(1, (value - min) / (max - min || 1)));

  // Viridis colormap RGB values (interpolated from key points)
  // Dark purple -> Blue -> Green -> Yellow
  let r: number, g: number, b: number;

  if (normalized < 0.25) {
    // Dark purple to blue
    const t = normalized / 0.25;
    r = Math.round(68 + (72 - 68) * t);
    g = Math.round(1 + (40 - 1) * t);
    b = Math.round(84 + (110 - 84) * t);
  } else if (normalized < 0.5) {
    // Blue to cyan
    const t = (normalized - 0.25) / 0.25;
    r = Math.round(72 + (62 - 72) * t);
    g = Math.round(40 + (149 - 40) * t);
    b = Math.round(110 + (152 - 110) * t);
  } else if (normalized < 0.75) {
    // Cyan to green
    const t = (normalized - 0.5) / 0.25;
    r = Math.round(62 + (29 - 62) * t);
    g = Math.round(149 + (105 - 149) * t);
    b = Math.round(152 + (150 - 152) * t);
  } else {
    // Green to yellow
    const t = (normalized - 0.75) / 0.25;
    r = Math.round(29 + (253 - 29) * t);
    g = Math.round(105 + (231 - 105) * t);
    b = Math.round(150 + (37 - 150) * t);
  }

  return `rgb(${r}, ${g}, ${b})`;
}

/**
 * Simplified viridis colormap using smooth interpolation
 * This version provides smoother color transitions
 */
export function viridisColorMapSmooth(value: number, min: number, max: number): string {
  const normalized = Math.max(0, Math.min(1, (value - min) / (max - min || 1)));

  // Key points in viridis colormap (normalized to 0-1)
  const keyPoints = [
    [0.0, [68, 1, 84]],      // Dark purple
    [0.25, [72, 40, 110]],   // Purple-blue
    [0.5, [62, 149, 152]],   // Cyan
    [0.75, [29, 105, 150]],  // Green
    [1.0, [253, 231, 37]],   // Yellow
  ];

  // Find the two key points to interpolate between
  let idx = 0;
  for (let i = 0; i < keyPoints.length - 1; i++) {
    if (normalized >= keyPoints[i][0] && normalized <= keyPoints[i + 1][0]) {
      idx = i;
      break;
    }
  }

  const [t0, [r0, g0, b0]] = keyPoints[idx];
  const [t1, [r1, g1, b1]] = keyPoints[idx + 1];

  // Interpolate
  const t = (normalized - t0) / (t1 - t0);
  const r = Math.round(r0 + (r1 - r0) * t);
  const g = Math.round(g0 + (g1 - g0) * t);
  const b = Math.round(b0 + (b1 - b0) * t);

  return `rgb(${r}, ${g}, ${b})`;
}


