import React, { useState, useRef, useEffect } from "react";

interface TimePickerProps {
  value: string | null; // HH:mm format
  onChange: (value: string | null) => void;
  className?: string;
  interval?: number; // minutes interval (default: 15)
}

export const TimePicker: React.FC<TimePickerProps> = ({
  value,
  onChange,
  className = "",
  interval = 15,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [hour, setHour] = useState(() => {
    if (value) {
      const [h] = value.split(":");
      return parseInt(h) || 0;
    }
    return new Date().getHours();
  });
  const [minute, setMinute] = useState(() => {
    if (value) {
      const [, m] = value.split(":");
      return parseInt(m) || 0;
    }
    return 0;
  });
  const [isAM, setIsAM] = useState(() => {
    if (value) {
      const [h] = value.split(":");
      return parseInt(h) < 12;
    }
    return new Date().getHours() < 12;
  });
  const [activeField, setActiveField] = useState<"hour" | "minute">("hour");
  const containerRef = useRef<HTMLDivElement>(null);
  const clockRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [isOpen]);

  useEffect(() => {
    if (value) {
      const [h, m] = value.split(":");
      const hNum = parseInt(h) || 0;
      setHour(hNum % 12 || 12);
      setMinute(parseInt(m) || 0);
      setIsAM(hNum < 12);
    }
  }, [value]);

  const handleHourChange = (newHour: number) => {
    setHour(newHour);
    setActiveField("hour");
    const hour24 = isAM ? (newHour === 12 ? 0 : newHour) : (newHour === 12 ? 12 : newHour + 12);
    onChange(`${String(hour24).padStart(2, "0")}:${String(minute).padStart(2, "0")}`);
  };

  const handleMinuteChange = (newMinute: number) => {
    setMinute(newMinute);
    setActiveField("minute");
    const hour24 = isAM ? (hour === 12 ? 0 : hour) : (hour === 12 ? 12 : hour + 12);
    onChange(`${String(hour24).padStart(2, "0")}:${String(newMinute).padStart(2, "0")}`);
  };

  const handleAMPMToggle = (am: boolean) => {
    setIsAM(am);
    const hour24 = am ? (hour === 12 ? 0 : hour) : (hour === 12 ? 12 : hour + 12);
    onChange(`${String(hour24).padStart(2, "0")}:${String(minute).padStart(2, "0")}`);
  };

  const getClockAngle = (value: number, max: number, isHour: boolean) => {
    if (isHour) {
      // For hours, map 12 to top (0°), 3 to right (90°), etc.
      return ((value % 12) * 30 - 90) * (Math.PI / 180);
    } else {
      // For minutes, map 0 to top (0°), 15 to right (90°), etc.
      return (value * 6 - 90) * (Math.PI / 180);
    }
  };

  const getClockPosition = (value: number, max: number, isHour: boolean) => {
    const angle = getClockAngle(value, max, isHour);
    const radius = 80; // clock radius in pixels
    const centerX = 100;
    const centerY = 100;
    const x = centerX + radius * Math.cos(angle);
    const y = centerY + radius * Math.sin(angle);
    return { x, y };
  };

  const handleClockClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!clockRef.current) return;
    const rect = clockRef.current.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;
    const clickX = e.clientX - centerX;
    const clickY = e.clientY - centerY;
    const distance = Math.sqrt(clickX * clickX + clickY * clickY);
    const radius = rect.width / 2;

    if (distance < radius * 0.3 || distance > radius * 0.9) return; // ignore clicks too close to center or outside

    const angle = Math.atan2(clickY, clickX) * (180 / Math.PI) + 90; // adjust for 12 o'clock = 0°
    const normalizedAngle = angle < 0 ? angle + 360 : angle;

    if (activeField === "hour") {
      let newHour = Math.round(normalizedAngle / 30);
      if (newHour === 0) newHour = 12;
      if (newHour > 12) newHour = newHour - 12;
      handleHourChange(newHour);
    } else {
      let newMinute = Math.round(normalizedAngle / 6);
      if (newMinute >= 60) newMinute = 0;
      // Round to nearest interval
      newMinute = Math.round(newMinute / interval) * interval;
      if (newMinute >= 60) newMinute = 0;
      handleMinuteChange(newMinute);
    }
  };

  const generateTimeOptions = () => {
    const options: number[] = [];
    for (let i = 0; i < 60; i += interval) {
      options.push(i);
    }
    return options;
  };

  const timeOptions = generateTimeOptions();

  const displayValue = value || "Select time";

  const hour24 = isAM ? (hour === 12 ? 0 : hour) : (hour === 12 ? 12 : hour + 12);
  const hourPos = getClockPosition(hour, 12, true);
  const minutePos = getClockPosition(minute, 60, false);

  return (
    <div ref={containerRef} className={`relative ${className}`}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-2 py-1 rounded-md bg-slate-900 border border-slate-700 text-sm text-left flex items-center justify-between hover:border-slate-500"
      >
        <span className={value ? "text-slate-100" : "text-slate-500"}>
          {displayValue}
        </span>
        <svg
          className="w-4 h-4 text-slate-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
      </button>

      {isOpen && (
        <div className="absolute z-50 mt-1 bg-slate-900 border border-slate-700 rounded-lg shadow-xl p-4 w-80">
          <div className="text-xs text-slate-400 mb-3">SELECT TIME</div>

          <div className="flex gap-4">
            {/* Digital Time Display */}
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-3">
                <button
                  type="button"
                  onClick={() => setActiveField("hour")}
                  className={`
                    text-3xl font-bold px-3 py-2 rounded
                    ${
                      activeField === "hour"
                        ? "bg-purple-500 text-white"
                        : "bg-slate-800 text-slate-200"
                    }
                  `}
                >
                  {hour}
                </button>
                <span className="text-2xl text-slate-400">:</span>
                <button
                  type="button"
                  onClick={() => setActiveField("minute")}
                  className={`
                    text-3xl font-bold px-3 py-2 rounded
                    ${
                      activeField === "minute"
                        ? "bg-purple-500 text-white"
                        : "bg-slate-800 text-slate-200"
                    }
                  `}
                >
                  {String(minute).padStart(2, "0")}
                </button>
              </div>

              {/* AM/PM Toggle */}
              <div className="flex gap-2 mb-4">
                <button
                  type="button"
                  onClick={() => handleAMPMToggle(true)}
                  className={`
                    flex-1 px-3 py-2 rounded text-sm font-medium
                    ${
                      isAM
                        ? "bg-purple-500 text-white"
                        : "bg-slate-800 text-slate-400"
                    }
                  `}
                >
                  AM
                </button>
                <button
                  type="button"
                  onClick={() => handleAMPMToggle(false)}
                  className={`
                    flex-1 px-3 py-2 rounded text-sm font-medium
                    ${
                      !isAM
                        ? "bg-purple-500 text-white"
                        : "bg-slate-800 text-slate-400"
                    }
                  `}
                >
                  PM
                </button>
              </div>

              {/* Time List (Scrollable) */}
              <div className="max-h-48 overflow-y-auto border border-slate-700 rounded">
                {timeOptions.map((m) => {
                  const isSelected = activeField === "minute" && minute === m;
                  return (
                    <button
                      key={m}
                      type="button"
                      onClick={() => handleMinuteChange(m)}
                      className={`
                        w-full px-3 py-2 text-left text-sm
                        ${
                          isSelected
                            ? "bg-purple-500 text-white"
                            : "text-slate-200 hover:bg-slate-800"
                        }
                      `}
                    >
                      {String(m).padStart(2, "0")}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Analog Clock */}
            <div className="flex-1 flex items-center justify-center">
              <div
                ref={clockRef}
                className="relative w-48 h-48 cursor-pointer"
                onClick={handleClockClick}
              >
                {/* Clock face circle */}
                <svg className="w-full h-full" viewBox="0 0 200 200">
                  <circle
                    cx="100"
                    cy="100"
                    r="90"
                    fill="none"
                    stroke="#374151"
                    strokeWidth="2"
                  />
                  {/* Hour markers */}
                  {Array.from({ length: 12 }, (_, i) => {
                    const angle = (i * 30 - 90) * (Math.PI / 180);
                    const x1 = 100 + 70 * Math.cos(angle);
                    const y1 = 100 + 70 * Math.sin(angle);
                    const x2 = 100 + 80 * Math.cos(angle);
                    const y2 = 100 + 80 * Math.sin(angle);
                    return (
                      <line
                        key={i}
                        x1={x1}
                        y1={y1}
                        x2={x2}
                        y2={y2}
                        stroke="#6B7280"
                        strokeWidth="2"
                      />
                    );
                  })}
                  {/* Hour numbers */}
                  {Array.from({ length: 12 }, (_, i) => {
                    const hour = i === 0 ? 12 : i;
                    const angle = (i * 30 - 90) * (Math.PI / 180);
                    const x = 100 + 60 * Math.cos(angle);
                    const y = 100 + 60 * Math.sin(angle);
                    return (
                      <text
                        key={i}
                        x={x}
                        y={y}
                        textAnchor="middle"
                        dominantBaseline="middle"
                        fill="#9CA3AF"
                        fontSize="14"
                        fontWeight="500"
                      >
                        {hour}
                      </text>
                    );
                  })}
                  {/* Hour hand */}
                  {activeField === "hour" && (
                    <g>
                      <line
                        x1="100"
                        y1="100"
                        x2={hourPos.x}
                        y2={hourPos.y}
                        stroke="#9333EA"
                        strokeWidth="4"
                        strokeLinecap="round"
                      />
                      <circle
                        cx={hourPos.x}
                        cy={hourPos.y}
                        r="12"
                        fill="#9333EA"
                      />
                      <text
                        x={hourPos.x}
                        y={hourPos.y}
                        textAnchor="middle"
                        dominantBaseline="middle"
                        fill="white"
                        fontSize="12"
                        fontWeight="bold"
                      >
                        {hour}
                      </text>
                    </g>
                  )}
                  {/* Minute hand */}
                  {activeField === "minute" && (
                    <g>
                      <line
                        x1="100"
                        y1="100"
                        x2={minutePos.x}
                        y2={minutePos.y}
                        stroke="#9333EA"
                        strokeWidth="3"
                        strokeLinecap="round"
                      />
                      <circle
                        cx={minutePos.x}
                        cy={minutePos.y}
                        r="8"
                        fill="#9333EA"
                      />
                    </g>
                  )}
                </svg>
              </div>
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex justify-end gap-2 mt-4">
            <button
              type="button"
              onClick={() => setIsOpen(false)}
              className="px-4 py-2 text-sm text-purple-400 hover:text-purple-300"
            >
              CANCEL
            </button>
            <button
              type="button"
              onClick={() => setIsOpen(false)}
              className="px-4 py-2 text-sm bg-purple-500 text-white rounded hover:bg-purple-600 font-medium"
            >
              OK
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

