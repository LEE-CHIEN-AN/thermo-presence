import React, { useEffect, useState } from "react";
import {
  fetchThermalHistory,
  fetchThermalById,
  HistoryFrameSummary,
  ThermalLatestResponse,
} from "../services/api";
import { ThermalImageViewer } from "../components/ThermalImageViewer";
import { DensityMapViewer } from "../components/DensityMapViewer";

function pad2(n: number) {
  return n.toString().padStart(2, "0");
}

// format Date to datetime-local string (YYYY-MM-DDTHH:MM) in LOCAL TIME (Taiwan UTC+8)
function toLocalInputValue(d: Date) {
  // Use local time for display (e.g. Taiwan UTC+8)
  const year = d.getFullYear();
  const month = pad2(d.getMonth() + 1);
  const day = pad2(d.getDate());
  const hours = pad2(d.getHours());
  const minutes = pad2(d.getMinutes());
  return `${year}-${month}-${day}T${hours}:${minutes}`;
}

function toUtcIso(local: string | null): string | undefined {
  if (!local) return undefined;
  // datetime-local input format: "YYYY-MM-DDTHH:mm"
  // Treat input as LOCAL time, convert to UTC ISO for backend
  const d = new Date(local);
  if (Number.isNaN(d.getTime())) return undefined;
  return d.toISOString();
}

export const History: React.FC = () => {
  const [sessionId, setSessionId] = useState("604_windowside");
  // Combined date and time for start/end (datetime-local format: YYYY-MM-DDTHH:mm)
  const [startDateTime, setStartDateTime] = useState<string>("");
  const [endDateTime, setEndDateTime] = useState<string>("");
  const [items, setItems] = useState<HistoryFrameSummary[]>([]);
  const [selected, setSelected] = useState<ThermalLatestResponse | null>(null);
  const [loadingList, setLoadingList] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Auto-play state
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [playSpeed, setPlaySpeed] = useState(1000); // milliseconds per frame

  // Validate time range: end time must be after start time
  const timeValidationError = (() => {
    if (!startDateTime || !endDateTime) return null;
    // Interpret as local time for validation
    const start = new Date(startDateTime);
    const end = new Date(endDateTime);
    if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) return "Invalid time range";
    if (start >= end) {
      return "End time must be after start time";
    }
    return null;
  })();

  const applyPreset = (minsAgo: number) => {
    const end = new Date();
    const start = new Date(end.getTime() - minsAgo * 60 * 1000);
    setStartDateTime(toLocalInputValue(start));
    setEndDateTime(toLocalInputValue(end));
  };

  const clearRange = () => {
    setStartDateTime("");
    setEndDateTime("");
  };

  const loadList = async () => {
    if (timeValidationError) {
      setError(timeValidationError);
      return;
    }
    try {
      setLoadingList(true);
      setError(null);
      setIsPlaying(false); // Stop auto-play when loading new data
      setCurrentIndex(0);
      const startIso = toUtcIso(startDateTime);
      const endIso = toUtcIso(endDateTime);
      const data = await fetchThermalHistory({
        session_id: sessionId,
        start_time: startIso,
        end_time: endIso,
        limit: 200,
      });
      // Sort by timestamp ascending (oldest first) for proper playback order
      const sortedData = [...data].sort((a, b) => {
        return new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime();
      });
      setItems(sortedData);
      setSelected(null);
    } catch (e: any) {
      console.error(e);
      setError(e?.message ?? "Failed to load history");
    } finally {
      setLoadingList(false);
    }
  };

  const loadDetail = async (frameId: number) => {
    try {
      setLoadingDetail(true);
      setError(null);
      const detail = await fetchThermalById(frameId);
      setSelected(detail);
    } catch (e: any) {
      console.error(e);
      setError(e?.message ?? "Failed to load frame detail");
    } finally {
      setLoadingDetail(false);
    }
  };

  // Auto-play effect
  useEffect(() => {
    if (!isPlaying || items.length === 0) return;

    const interval = setInterval(() => {
      setCurrentIndex((prev) => {
        const next = prev + 1;
        if (next >= items.length) {
          setIsPlaying(false);
          return prev;
        }
        return next;
      });
    }, playSpeed);

    return () => clearInterval(interval);
  }, [isPlaying, items.length, playSpeed]);

  // Load detail when currentIndex changes during auto-play
  useEffect(() => {
    if (isPlaying && items.length > 0 && currentIndex < items.length) {
      loadDetail(items[currentIndex].frame_id);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentIndex, isPlaying]);

  // Toggle auto-play
  const togglePlay = () => {
    if (items.length === 0) return;
    if (isPlaying) {
      setIsPlaying(false);
    } else {
      if (currentIndex >= items.length) {
        setCurrentIndex(0);
      }
      setIsPlaying(true);
    }
  };

  // Reset to first frame
  const resetPlay = () => {
    setIsPlaying(false);
    setCurrentIndex(0);
    if (items.length > 0) {
      loadDetail(items[0].frame_id);
    }
  };

  useEffect(() => {
    // 初次載入歷史列表
    loadList();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="min-h-screen flex flex-col gap-4 px-4 py-6 md:px-8 bg-black">
      <header className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-2xl md:text-3xl font-semibold tracking-tight">
            History
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            查詢指定 Session 與時間區間內的歷史熱影像、人數與密度圖。
          </p>
        </div>
        <div className="flex flex-wrap items-end gap-3 text-xs md:text-sm">
          <div className="flex flex-col gap-1">
            <span className="text-slate-400">Session ID</span>
            <input
              className="px-2 py-1 rounded-md bg-slate-900 border border-slate-700 text-sm"
              value={sessionId}
              onChange={(e) => setSessionId(e.target.value)}
            />
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-slate-400">Start time</span>
            <input
              type="datetime-local"
              value={startDateTime}
              onChange={(e) => setStartDateTime(e.target.value)}
              className="px-2 py-1 rounded-md bg-slate-900 border border-slate-700 text-sm [&::-webkit-calendar-picker-indicator]:invert [&::-webkit-calendar-picker-indicator]:cursor-pointer"
            />
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-slate-400">End time</span>
            <input
              type="datetime-local"
              value={endDateTime}
              onChange={(e) => setEndDateTime(e.target.value)}
              className="px-2 py-1 rounded-md bg-slate-900 border border-slate-700 text-sm [&::-webkit-calendar-picker-indicator]:invert [&::-webkit-calendar-picker-indicator]:cursor-pointer"
            />
          </div>
          <button
            onClick={loadList}
            disabled={!!timeValidationError}
            className="px-3 py-1.5 rounded-md bg-sky-600 hover:bg-sky-500 disabled:bg-slate-700 disabled:cursor-not-allowed text-sm font-medium"
          >
            Search
          </button>
          {timeValidationError && (
            <div className="text-xs text-red-400 col-span-full">
              {timeValidationError}
            </div>
          )}
          <div className="flex flex-wrap gap-2 text-[11px] text-slate-300">
            <span className="font-semibold text-slate-200">Presets:</span>
            <button
              className="px-2 py-1 rounded-md bg-slate-800 hover:bg-slate-700 border border-slate-700"
              onClick={() => applyPreset(10)}
            >
              Last 10 min
            </button>
            <button
              className="px-2 py-1 rounded-md bg-slate-800 hover:bg-slate-700 border border-slate-700"
              onClick={() => applyPreset(60)}
            >
              Last 1 hour
            </button>
            <button
              className="px-2 py-1 rounded-md bg-slate-800 hover:bg-slate-700 border border-slate-700"
              onClick={() => applyPreset(6 * 60)}
            >
              Last 6 hours
            </button>
            <button
              className="px-2 py-1 rounded-md bg-slate-900 hover:bg-slate-800 border border-slate-700"
              onClick={clearRange}
            >
              Clear
            </button>
          </div>
        </div>
      </header>

      {error && (
        <div className="rounded-md border border-red-500/40 bg-red-950/40 px-3 py-2 text-sm text-red-200">
          {error}
        </div>
      )}

      <main className="grid gap-4 md:grid-cols-3 items-start">
        {/* 左側：列表 */}
        <section className="space-y-2 md:col-span-1">
          <h2 className="text-lg font-semibold">Frames</h2>
          <div className="rounded-lg bg-slate-900 border border-slate-800 overflow-hidden max-h-[70vh] flex flex-col">
            <div className="px-3 py-2 text-xs text-slate-400 border-b border-slate-800 flex justify-between">
              <span>{items.length} items</span>
              {loadingList && <span>Loading…</span>}
            </div>
            <div className="flex-1 overflow-auto text-xs">
              {items.length === 0 ? (
                <div className="px-3 py-4 text-slate-500 text-center">
                  No data
                </div>
              ) : (
                <table className="w-full border-collapse">
                  <thead className="bg-slate-950 sticky top-0 z-10">
                    <tr>
                      <th className="px-2 py-2 text-left font-medium">ID</th>
                      <th className="px-2 py-2 text-left font-medium">
                        Timestamp (UTC)
                      </th>
                      <th className="px-2 py-2 text-right font-medium">
                        Count
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.map((it) => (
                      <tr
                        key={it.frame_id}
                        className={`cursor-pointer hover:bg-slate-800 ${
                          selected?.frame_id === it.frame_id
                            ? "bg-slate-800/80"
                            : ""
                        }`}
                        onClick={() => loadDetail(it.frame_id)}
                      >
                        <td className="px-2 py-1">{it.frame_id}</td>
                        <td className="px-2 py-1">
                          {new Date(it.timestamp).toISOString().replace("T", " ").replace("Z", "Z")}
                        </td>
                        <td className="px-2 py-1 text-right">
                          {it.people_count_rounded} (
                          {it.people_count.toFixed(2)})
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </section>

        {/* 右側：詳細視圖 */}
        <section className="space-y-3 md:col-span-2">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">Details</h2>
            {/* Auto-play controls */}
            {items.length > 0 && (
              <div className="flex items-center gap-2">
                <button
                  onClick={resetPlay}
                  className="px-2 py-1 rounded-md bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs"
                  title="Reset to first frame"
                >
                  ⏮
                </button>
                <button
                  onClick={togglePlay}
                  className="px-3 py-1 rounded-md bg-sky-600 hover:bg-sky-500 text-xs font-medium"
                >
                  {isPlaying ? "⏸ Pause" : "▶ Play"}
                </button>
                <select
                  value={playSpeed}
                  onChange={(e) => {
                    setPlaySpeed(Number(e.target.value));
                  }}
                  className="px-2 py-1 rounded-md bg-slate-800 border border-slate-700 text-xs"
                  disabled={isPlaying}
                >
                  <option value={500}>0.5s/frame</option>
                  <option value={1000}>1s/frame</option>
                  <option value={2000}>2s/frame</option>
                  <option value={3000}>3s/frame</option>
                </select>
                {isPlaying && (
                  <span className="text-xs text-slate-400">
                    {currentIndex + 1} / {items.length}
                  </span>
                )}
              </div>
            )}
          </div>
          {loadingDetail && (
            <div className="text-xs text-slate-400">Loading detail…</div>
          )}
          {!selected ? (
            <div className="rounded-lg bg-slate-900 border border-slate-800 px-4 py-8 text-sm text-slate-500 text-center">
              請在左側列表點選一筆資料。
            </div>
          ) : (
            <div className="space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-400">
                <div>
                  Frame ID: <span className="font-mono">{selected.frame_id}</span>
                </div>
                <div>
                  Timestamp (UTC):{" "}
                  <span className="font-mono">
                    {new Date(selected.timestamp)
                      .toISOString()
                      .replace("T", " ")
                      .replace("Z", "Z")}
                  </span>
                </div>
                <div>
                  People:{" "}
                  <span className="font-semibold text-slate-100">
                    {selected.people_count_rounded} (
                    {selected.people_count.toFixed(2)})
                  </span>
                </div>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <h3 className="text-md font-semibold text-center">
                    IR frame
                  </h3>
                  <div className="rounded-lg bg-slate-900 p-3 flex items-center justify-center">
                    {selected.thermal_image ? (
                      <ThermalImageViewer
                        data={selected.thermal_image.data}
                        shape={selected.thermal_image.shape}
                      />
                    ) : (
                      <div className="text-sm text-slate-500 text-center py-8">
                        No thermal image
                      </div>
                    )}
                  </div>
                </div>
                <div className="space-y-2">
                  <h3 className="text-md font-semibold text-center">
                    Network output
                  </h3>
                  <div className="rounded-lg bg-slate-900 p-3 flex items-center justify-center">
                    {selected.density_map ? (
                      <DensityMapViewer
                        data={selected.density_map.data}
                        shape={selected.density_map.shape}
                      />
                    ) : (
                      <div className="text-sm text-slate-500 text-center py-8">
                        No density map
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}
        </section>
      </main>
    </div>
  );
};


