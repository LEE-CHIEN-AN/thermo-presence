import React from "react";
import { viridisColorMapSmooth } from "../utils/colormap";
import { Colorbar } from "./Colorbar";
import { RoomLayoutOverlay } from "./RoomLayoutOverlay";
import { YOLODetection } from "../services/api";

interface YOLODetectionViewerProps {
  thermalData: number[]; // flattened thermal values
  thermalShape: [number, number]; // [rows, cols]
  yoloDetection: YOLODetection | null;
}

/**
 * YOLO detection viewer showing thermal image with bounding boxes overlay
 * Similar to ThermalImageViewer but with YOLO detection boxes drawn on top
 */
export const YOLODetectionViewer: React.FC<YOLODetectionViewerProps> = ({
  thermalData,
  thermalShape,
  yoloDetection,
}) => {
  const [rows, cols] = thermalShape;
  if (!thermalData || thermalData.length === 0) {
    return <div className="text-sm text-slate-400">No thermal data</div>;
  }

  const min = Math.min(...thermalData);
  const max = Math.max(...thermalData);

  // YOLO boxes are in normalized coordinates (0-1) for 192×256 image (training input size)
  // The thermal image should now be upsampled to 192×256 to match YOLO detection resolution
  // Display grid is cols × rows (should be 256 × 192 for upsampled image)
  const displayWidth = cols;  // Should be 256 for upsampled image
  const displayHeight = rows; // Should be 192 for upsampled image
  
  // YOLO training input size (same as display size now)
  const yoloInputWidth = 256;
  const yoloInputHeight = 192;
  
  // Since display size matches YOLO input size, coordinates are already in the correct scale
  // Just convert from normalized (0-1) to pixel coordinates
  const scaleX = displayWidth;  // 256 (no scaling needed)
  const scaleY = displayHeight; // 192 (no scaling needed)

  return (
    <div className="flex items-start gap-2 w-full max-w-full overflow-hidden">
      {/* Thermal image grid with YOLO boxes overlay */}
      <div
        className="grid border border-slate-700 rounded-md overflow-hidden flex-shrink-0 gap-0 relative"
        style={{
          gridTemplateRows: `repeat(${rows}, minmax(0, 1fr))`,
          gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))`,
          flex: "1 1 0",
          minWidth: 0,
          aspectRatio: `${cols} / ${rows}`,
          transform: "scaleX(-1)", // 水平翻轉（左右翻轉）
        }}
      >
        {/* Thermal image background */}
        {thermalData.map((v, idx) => {
          const color = viridisColorMapSmooth(v, min, max);
          return (
            <div
              key={`thermal-${idx}`}
              style={{ backgroundColor: color }}
              className="w-full h-full"
            />
          );
        })}
        
        {/* Room layout overlay */}
        <RoomLayoutOverlay cols={cols} rows={rows} />
        
        {/* YOLO bounding boxes overlay */}
        {yoloDetection && yoloDetection.boxes.length > 0 && (
          <div
            className="absolute inset-0 pointer-events-none"
            style={{
              transform: "scaleX(-1)", // Match the grid's horizontal flip
            }}
          >
            {yoloDetection.boxes.map((box, idx) => {
              // Convert normalized coordinates (0-1) to pixel coordinates
              // YOLO format: x_center, y_center, width, height (all normalized 0-1)
              // 
              // IMPORTANT: The thermal image is displayed with horizontal flip (scaleX(-1)),
              // so we need to flip the x-coordinate: flipped_x = 1 - x_center
              const flippedXCenter = 1 - box.x_center;
              
              // Convert normalized coordinates to pixel coordinates (display size = YOLO input size)
              const xCenter = flippedXCenter * scaleX;
              const yCenter = box.y_center * scaleY;
              const width = box.width * scaleX;
              const height = box.height * scaleY;
              
              // Calculate top-left corner (in display coordinates)
              const left = xCenter - width / 2;
              const top = yCenter - height / 2;
              
              return (
                <div
                  key={`box-${idx}`}
                  className="absolute border-2 border-blue-500 bg-blue-500/20"
                  style={{
                    left: `${(left / displayWidth) * 100}%`,
                    top: `${(top / displayHeight) * 100}%`,
                    width: `${(width / displayWidth) * 100}%`,
                    height: `${(height / displayHeight) * 100}%`,
                  }}
                >
                  {/* Confidence label */}
                  <div className="absolute -top-5 left-0 text-xs text-blue-400 font-semibold whitespace-nowrap">
                    {box.confidence.toFixed(2)}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
      
      {/* Colorbar */}
      <div className="flex-shrink-0 self-stretch flex items-start overflow-visible" style={{ minWidth: "80px" }}>
        <Colorbar
          min={min}
          max={max}
          label="Temp"
          unit="°C"
          height={0}
          numTicks={5}
        />
      </div>
    </div>
  );
};
