import React from "react";
import { viridisColorMapSmooth } from "../utils/colormap";
import { Colorbar } from "./Colorbar";
import { RoomLayoutOverlay } from "./RoomLayoutOverlay";

interface DensityMapViewerProps {
  data: number[]; // flattened values
  shape: [number, number]; // [rows, cols]
}

/**
 * Density map viewer using viridis colormap (like Network output visualization)
 * Renders a grid of small divs with viridis color mapping based on density values.
 * Includes a colorbar on the right side showing density scale.
 */
export const DensityMapViewer: React.FC<DensityMapViewerProps> = ({ data, shape }) => {
  const [rows, cols] = shape;
  if (!data || data.length === 0) {
    return <div className="text-sm text-slate-400">No density map</div>;
  }

  const min = 0; // Density maps typically start from 0
  const max = Math.max(...data);

  // Calculate optimal size to fit container without scrolling
  // Use container width to determine image size, maintaining aspect ratio
  const imageAspectRatio = cols / rows;

  return (
    <div className="flex items-start gap-2 w-full max-w-full overflow-hidden">
      {/* Density map grid - fit to container with space for colorbar */}
      <div
        className="grid border border-slate-700 rounded-md overflow-hidden flex-shrink-0 gap-0 relative"
        style={{
          gridTemplateRows: `repeat(${rows}, minmax(0, 1fr))`, //
          gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))`,
          flex: "1 1 0",
          minWidth: 0, // 最小寬度
          aspectRatio: `${cols} / ${rows}`,
          transform: "scaleX(-1)", // 水平翻轉（左右翻轉）
        }}
      >
        {data.map((v, idx) => {
          const color = viridisColorMapSmooth(v, min, max);
          return (
            <div
              key={idx}
              style={{ backgroundColor: color }}
              className="w-full h-full"
            />
          );
        })}
        {/* Overlay room layout on top of the grid (inherits the same transform) */}
        <RoomLayoutOverlay cols={cols} rows={rows} />
      </div>
      
      {/* Colorbar - match image height, contained within flex container */}
      <div className="flex-shrink-0 self-stretch flex items-start overflow-visible" style={{ minWidth: "80px" }}>
        <Colorbar
          min={min}
          max={max}
          label="Density"
          unit=""
          height={0} // Will be calculated by flex-1
          numTicks={5}
        />
      </div>
    </div>
  );
};


