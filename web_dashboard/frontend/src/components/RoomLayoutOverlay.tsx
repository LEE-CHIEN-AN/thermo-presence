import React from "react";

interface RoomLayoutOverlayProps {
  cols: number;
  rows: number;
  strokeWidth?: number;
  opacity?: number;
}

/**
 * Draws a wireframe of the 604 classroom on top of the thermal/density map.
 *
 * Coordinate system is aligned with the grid:
 *   x ∈ [0, cols], y ∈ [0, rows]
 *
 * The mapping from real-world centimeters to grid coordinates matches
 * `supabase_integration/frame_processor_mlx90641.py` → `_draw_room_layout`.
 */
export const RoomLayoutOverlay: React.FC<RoomLayoutOverlayProps> = ({
  cols,
  rows,
  strokeWidth = 0.35,
  opacity = 0.7,
}) => {
  // Real-world coordinate range (cm) for the detectable area
  const X_MIN = 120.0;
  const X_MAX = 600.0;
  const Y_MIN = 40.0;
  const Y_MAX = 340.0;

  const toPx = (xCm: number, yCm: number) => {
    const xNorm = (xCm - X_MIN) / (X_MAX - X_MIN);
    const yNorm = (yCm - Y_MIN) / (Y_MAX - Y_MIN);
    // 熱圖/密度圖的網格在容器上有水平翻轉（scaleX(-1)），
    // 為了讓線框方向與後端 Python 圖一致，X 先做一次鏡像，
    // 之後再一起被 scaleX(-1) 翻轉回正向。
    // Y 則要以右下角為 (0,0)、向上為正，所以也需要做一次垂直鏡像。
    return {
      x: (1 - xNorm) * cols,
      y: (1 - yNorm) * rows,
    };
  };

  const rect = (x0: number, y0: number, x1: number, y1: number) => {
    const p0 = toPx(x0, y0);
    const p1 = toPx(x1, y1);
    const x = Math.min(p0.x, p1.x);
    const y = Math.min(p0.y, p1.y);
    const w = Math.abs(p1.x - p0.x);
    const h = Math.abs(p1.y - p0.y);
    return { x, y, w, h };
  };

  const line = (x0: number, y0: number, x1: number, y1: number) => {
    const p0 = toPx(x0, y0);
    const p1 = toPx(x1, y1);
    return { x1: p0.x, y1: p0.y, x2: p1.x, y2: p1.y };
  };

  // Shapes based on the same coordinates used in Python `_draw_room_layout`
  const midLeft = rect(210, 180, 390, 240);
  const midRight = rect(390, 180, 570, 240);

  const upLeft = line(210, 240, 210, 340);
  const upRight = line(270, 240, 270, 340);

  const bottomHoriz = line(120, 80, 524, 80);
  const bottomVert = line(524, 80, 524, 40);

  return (
    <svg
      className="pointer-events-none absolute inset-0"
      viewBox={`0 0 ${cols} ${rows}`}
      preserveAspectRatio="none"
    >
      <g stroke="white" strokeWidth={strokeWidth} fill="none" strokeOpacity={opacity}>
        {/* Middle horizontal blocks */}
        <rect x={midLeft.x} y={midLeft.y} width={midLeft.w} height={midLeft.h} />
        <rect x={midRight.x} y={midRight.y} width={midRight.w} height={midRight.h} />

        {/* Vertical lines from middle block upwards */}
        <line x1={upLeft.x1} y1={upLeft.y1} x2={upLeft.x2} y2={upLeft.y2} />
        <line x1={upRight.x1} y1={upRight.y1} x2={upRight.x2} y2={upRight.y2} />

        {/* Bottom horizontal and vertical lines */}
        <line x1={bottomHoriz.x1} y1={bottomHoriz.y1} x2={bottomHoriz.x2} y2={bottomHoriz.y2} />
        <line x1={bottomVert.x1} y1={bottomVert.y1} x2={bottomVert.x2} y2={bottomVert.y2} />
      </g>
    </svg>
  );
};
