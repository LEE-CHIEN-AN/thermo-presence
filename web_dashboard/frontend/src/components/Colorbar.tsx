import React from "react";
import { viridisColorMapSmooth } from "../utils/colormap";

interface ColorbarProps {
  min: number;
  max: number;
  label?: string;
  unit?: string;
  height?: number; // height in pixels
  numTicks?: number; // number of tick marks
}

/**
 * Colorbar component displaying a color scale with value labels
 * Uses viridis colormap to match thermal and density map visualizations
 */
export const Colorbar: React.FC<ColorbarProps> = ({
  min,
  max,
  label = "Value",
  unit = "",
  height = 300,
  numTicks = 5,
}) => {
  const steps = 100; // Number of color gradient steps
  const tickValues: number[] = [];
  for (let i = 0; i < numTicks; i++) {
    tickValues.push(min + ((max - min) * i) / (numTicks - 1));
  }

  const formatValue = (val: number): string => {
    if (Math.abs(val) < 0.01 || Math.abs(val) > 1000) {
      return val.toExponential(2);
    }
    return val.toFixed(2);
  };

  return (
    <div className="flex flex-col items-center gap-2 h-full w-full">
      {label && (
        <div className="text-xs text-slate-400 font-medium text-center whitespace-nowrap">
          {label}
          {unit && <span className="ml-1">({unit})</span>}
        </div>
      )}
      <div className="relative flex-1 flex items-center w-full" style={{ minHeight: height > 0 ? `${height}px` : "100%" }}>
        {/* Color gradient */}
        <div
          className="w-8 border border-slate-700 rounded h-full flex-shrink-0"
          style={{ minHeight: height > 0 ? `${height}px` : "100%" }}
        >
          {Array.from({ length: steps }, (_, i) => {
            const value = max - ((max - min) * i) / (steps - 1);
            const color = viridisColorMapSmooth(value, min, max);
            return (
              <div
                key={i}
                style={{
                  backgroundColor: color,
                  height: `${100 / steps}%`,
                }}
                className="w-full"
              />
            );
          })}
        </div>

        {/* Tick marks and labels - contained within component */}
        <div className="relative ml-2 flex flex-col justify-between h-full flex-shrink-0 overflow-visible" style={{ minHeight: height > 0 ? `${height}px` : "100%" }}>
          {tickValues.map((val, idx) => {
            const position = ((max - val) / (max - min)) * 100;
            return (
              <div
                key={idx}
                className="absolute flex items-center gap-1"
                style={{
                  top: `${position}%`,
                  transform: "translateY(-50%)",
                  left: 0,
                }}
              >
                <div className="w-1.5 h-px bg-slate-500 flex-shrink-0" />
                <span className="text-xs text-slate-400 whitespace-nowrap">
                  {formatValue(val)}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

