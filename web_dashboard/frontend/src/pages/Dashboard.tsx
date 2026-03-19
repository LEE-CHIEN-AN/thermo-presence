import React, { useEffect, useState } from "react";
import { fetchLatestThermal, ThermalLatestResponse, fetchPmvPpdHeatmaps, PmvPpdHeatmapsResponse } from "../services/api";
import { ThermalImageViewer } from "../components/ThermalImageViewer";
import { DensityMapViewer } from "../components/DensityMapViewer";

export const Dashboard: React.FC = () => {
  const [sessionId, setSessionId] = useState("604_windowside");
  const [data, setData] = useState<ThermalLatestResponse | null>(null);
  const [heatmaps, setHeatmaps] = useState<PmvPpdHeatmapsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingHeatmaps, setLoadingHeatmaps] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetchLatestThermal(sessionId);
      setData(res);
    } catch (e: any) {
      console.error(e);
      setError(e?.message ?? "Failed to load data");
    } finally {
      setLoading(false);
    }
  };

  const loadHeatmaps = async () => {
    try {
      setLoadingHeatmaps(true);
      const res = await fetchPmvPpdHeatmaps();
      setHeatmaps(res);
    } catch (e: any) {
      console.error("Failed to load PMV/PPD heatmaps", e);
    } finally {
      setLoadingHeatmaps(false);
    }
  };

  useEffect(() => {
    load();
    loadHeatmaps();
    const id = setInterval(() => {
      load();
      loadHeatmaps();
    }, 10_000);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  const predictedCount = data?.people_count_rounded ?? "-";

  return (
    <div className="min-h-screen flex flex-col gap-6 px-4 py-6 md:px-8 bg-black">
      {/* Top: Predicted people count (like example image) */}
      <header className="flex flex-col gap-4 items-center text-center">
        <h1 className="text-3xl md:text-4xl font-semibold tracking-tight">
          Predicted people count: {predictedCount}
        </h1>
        <div className="flex flex-wrap items-center justify-center gap-2 text-xs text-slate-400">
          <span>Session ID:</span>
          <input
            className="px-3 py-1.5 rounded-md bg-slate-900 border border-slate-700 text-sm"
            value={sessionId}
            onChange={(e) => setSessionId(e.target.value)}
          />
          <button
            onClick={load}
            className="px-3 py-1.5 rounded-md bg-sky-600 hover:bg-sky-500 text-sm font-medium"
          >
            Refresh
          </button>
        </div>
      </header>

      {error && (
        <div className="rounded-md border border-red-500/40 bg-red-950/40 px-3 py-2 text-sm text-red-200">
          {error}
        </div>
      )}

      {/* Main row: IR frame | Network output | People count info */}
      <main className="grid gap-4 md:grid-cols-[2fr_2fr_1fr] items-start">
        {/* IR frame */}
        <section className="space-y-2 min-w-0">
          <h2 className="text-lg font-semibold text-center">IR frame</h2>
          <div className="rounded-lg bg-slate-900 p-2 flex items-center justify-center overflow-hidden">
            {data?.thermal_image ? (
              <ThermalImageViewer
                data={data.thermal_image.data}
                shape={data.thermal_image.shape}
              />
            ) : (
              <div className="text-sm text-slate-500 text-center py-8">
                No thermal image data
              </div>
            )}
          </div>
        </section>

        {/* Network output (density map) */}
        <section className="space-y-2 min-w-0">
          <h2 className="text-lg font-semibold text-center">Network output</h2>
          <div className="rounded-lg bg-slate-900 p-2 flex flex-col items-center justify-center gap-2 overflow-visible">
            {data?.density_map ? (
              <DensityMapViewer
                data={data.density_map.data}
                shape={data.density_map.shape}
              />
            ) : (
              <div className="text-sm text-slate-500 text-center py-8">
                No density map data
              </div>
            )}
          </div>
        </section>

        {/* People count details - smaller */}
        <section className="space-y-2">
          <h2 className="text-base font-semibold text-center">Details</h2>
          <div className="rounded-lg bg-slate-900 p-3 flex flex-col items-center justify-center gap-2">
            <div className="text-xs text-slate-400">
              Frame ID: {data?.frame_id ?? "-"}
            </div>
            <div className="text-3xl font-bold">
              {data?.people_count_rounded ?? "-"}
            </div>
            {data && (
              <div className="text-xs text-slate-400">
                ({data.people_count.toFixed(2)})
              </div>
            )}
            <div className="text-xs text-slate-500 text-center">
              {data
                ? (() => {
                    // Parse ISO string and display in UTC (no timezone conversion)
                    const date = new Date(data.timestamp);
                    // Format as UTC time to avoid timezone offset
                    const year = date.getUTCFullYear();
                    const month = date.getUTCMonth() + 1;
                    const day = date.getUTCDate();
                    const hour = date.getUTCHours();
                    const minute = date.getUTCMinutes().toString().padStart(2, "0");
                    const second = date.getUTCSeconds().toString().padStart(2, "0");
                    const ampm = hour >= 12 ? "PM" : "AM";
                    const hour12 = hour % 12 || 12;
                    return `${month}/${day}/${year}, ${hour12}:${minute}:${second} ${ampm}`;
                  })()
                : "No timestamp"}
            </div>
          </div>
        </section>
      </main>

      {/* PMV/PPD Heatmaps Section */}
      <section className="space-y-4">
        <h2 className="text-xl font-semibold text-center">教室即時 PMV / PPD 熱力圖</h2>
        
        {loadingHeatmaps && (
          <div className="text-sm text-slate-400 text-center py-4">載入熱力圖中...</div>
        )}

        {heatmaps && (
          <div className="grid gap-4 md:grid-cols-2">
            {/* PMV Heatmap */}
            <div className="space-y-2">
              <h3 className="text-lg font-semibold text-center">PMV 熱力圖</h3>
              <div className="rounded-lg bg-slate-900 p-2 flex items-center justify-center overflow-hidden">
                <img
                  src={`data:image/png;base64,${heatmaps.pmv_image}`}
                  alt="PMV Heatmap"
                  className="max-w-full h-auto"
                />
              </div>
              <div className="text-xs text-slate-400 text-center px-2">
                預測平均表決 (Predicted Mean Vote，PMV)，是由丹麥學者P.O. Fanger教授於1972年所發表人體熱平衡模型，該模型用來表示人體對於環境中冷、熱的感受。
              </div>
            </div>

            {/* PPD Heatmap */}
            <div className="space-y-2">
              <h3 className="text-lg font-semibold text-center">PPD 熱力圖</h3>
              <div className="rounded-lg bg-slate-900 p-2 flex items-center justify-center overflow-hidden">
                <img
                  src={`data:image/png;base64,${heatmaps.ppd_image}`}
                  alt="PPD Heatmap"
                  className="max-w-full h-auto"
                />
              </div>
              <div className="text-xs text-slate-400 text-center px-2">
                預測不滿意百分率(Predicted Percentage of Dissatisfied, PPD)，表示在該PMV舒適指標中，空間內有多少百分比的人感到不舒適。為了確保符合已知標準（ASHRAE 55 和 ISO 7730）的熱舒適度，空間內所有佔用區域的 PPD 值應保持在 20% 以下。
              </div>
            </div>
          </div>
        )}

        {heatmaps?.timestamp && (
          <div className="text-xs text-slate-500 text-center">
            資料時間：{(() => {
              // Parse UTC timestamp and convert to local time (UTC+8)
              const date = new Date(heatmaps.timestamp);
              // Add 8 hours for UTC+8 timezone
              const localTime = new Date(date.getTime() + 8 * 60 * 60 * 1000);
              const year = localTime.getUTCFullYear();
              const month = localTime.getUTCMonth() + 1;
              const day = localTime.getUTCDate();
              const hour = localTime.getUTCHours();
              const minute = localTime.getUTCMinutes().toString().padStart(2, "0");
              const second = localTime.getUTCSeconds().toString().padStart(2, "0");
              return `${year}/${month}/${day} ${hour}:${minute}:${second}`;
            })()}
          </div>
        )}

        {!heatmaps && !loadingHeatmaps && (
          <div className="text-sm text-slate-500 text-center py-8">
            無法載入 PMV/PPD 熱力圖
          </div>
        )}
      </section>

      {loading && (
        <div className="fixed bottom-4 right-4 text-xs text-slate-400">
          Loading...
        </div>
      )}
    </div>
  );
};


