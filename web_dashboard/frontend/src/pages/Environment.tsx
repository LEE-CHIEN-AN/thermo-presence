import React, { useEffect, useState } from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import { api } from "../services/api";

interface AirQualityPoint {
  time: string;
  name: string;
  co2eq: number | null;
  total_voc: number | null;
}

interface PMPoint {
  time: string;
  name: string;
  pm1_0_atm: number | null;
  pm2_5_atm: number | null;
  pm10_atm: number | null;
}

interface TempHumidityPoint {
  time: string;
  name: string;
  celsius_degree: number | null;
  humidity: number | null;
}

export const Environment: React.FC = () => {
  const [days, setDays] = useState<number>(10);
  const [data, setData] = useState<AirQualityPoint[]>([]);
  const [pmData, setPmData] = useState<PMPoint[]>([]);
  const [tempHumidityData, setTempHumidityData] = useState<TempHumidityPoint[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadTrend = async () => {
    setLoading(true);
    setError(null);
    try {
      const [airRes, pmRes, tempHumRes] = await Promise.all([
        api.get<AirQualityPoint[]>("/environment/air-quality-trend", { params: { days } }),
        api.get<PMPoint[]>("/environment/pm-trend", { params: { days } }),
        api.get<TempHumidityPoint[]>("/environment/temp-humidity-trend", { params: { days, sensor_name: "604_center" } }),
      ]);
      setData(airRes.data || []);
      setPmData(pmRes.data || []);
      setTempHumidityData(tempHumRes.data || []);
    } catch (err) {
      console.error("Failed to load air quality trend", err);
      setError("載入空氣品質趨勢失敗");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTrend();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const chartData = data.map((p) => {
    const d = new Date(p.time);
    return {
      time: d.toLocaleString("zh-TW", { hour12: false }),
      co2eq: p.co2eq,
      total_voc: p.total_voc,
    };
  });

  const pmChartData = pmData.map((p) => {
    const d = new Date(p.time);
    return {
      time: d.toLocaleString("zh-TW", { hour12: false }),
      pm1_0: p.pm1_0_atm,
      pm2_5: p.pm2_5_atm,
      pm10: p.pm10_atm,
    };
  });

  const tempHumidityChartData = tempHumidityData.map((p) => {
    const d = new Date(p.time);
    return {
      time: d.toLocaleString("zh-TW", { hour12: false }),
      temperature: p.celsius_degree,
      humidity: p.humidity,
    };
  });

  return (
    <div className="container mx-auto px-4 py-6 space-y-6">
      <h1 className="text-2xl font-bold mb-6">環境感測 / 空氣品質</h1>

      <div className="bg-slate-900 rounded-lg p-4 space-y-4">
        <div className="flex flex-wrap items-center gap-3">
          <span className="text-sm text-slate-300">CO₂ / VOC 長期趨勢（604_air_quality）</span>
          <label className="flex items-center gap-2 text-sm text-slate-300">
            最近天數：
            <input
              type="number"
              min={1}
              max={60}
              value={days}
              onChange={(e) => setDays(Number(e.target.value) || 1)}
              className="w-20 px-2 py-1 bg-slate-800 border border-slate-700 rounded-md text-slate-50 text-sm"
            />
          </label>
          <button
            type="button"
            onClick={loadTrend}
            disabled={loading}
            className="px-3 py-1.5 rounded-md bg-sky-600 hover:bg-sky-700 disabled:bg-slate-700 disabled:cursor-not-allowed text-sm font-medium"
          >
            {loading ? "載入中..." : "重新載入"}
          </button>
        </div>
        {error && (
          <div className="bg-red-900/50 border border-red-700 rounded-lg p-3 text-sm text-red-200">{error}</div>
        )}
      </div>

      {chartData.length > 0 ? (
        <>
          {/* CO2 trend */}
          <div className="bg-slate-900 rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">CO₂ 濃度變化趨勢</h2>
            <ResponsiveContainer width="100%" height={400}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#475569" />
                <XAxis dataKey="time" stroke="#94a3b8" />
                <YAxis
                  stroke="#94a3b8"
                  label={{ value: "CO₂ (ppm)", angle: -90, position: "insideLeft", fill: "#94a3b8" }}
                />
                <Tooltip
                  contentStyle={{ backgroundColor: "#1e293b", border: "1px solid #475569" }}
                  labelStyle={{ color: "#e2e8f0" }}
                />
                <Legend />
                <Line type="monotone" dataKey="co2eq" stroke="#0ea5e9" strokeWidth={2} name="CO₂ (ppm)" dot={false} />
              </LineChart>
            </ResponsiveContainer>
            <div className="mt-2 text-xs text-slate-400">虛線 1000 ppm 可作為室內空氣品質警戒線。</div>
          </div>

          {/* VOC trend */}
          <div className="bg-slate-900 rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">VOC 濃度變化趨勢</h2>
            <ResponsiveContainer width="100%" height={400}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#475569" />
                <XAxis dataKey="time" stroke="#94a3b8" />
                <YAxis
                  stroke="#94a3b8"
                  label={{ value: "VOC (ppb)", angle: -90, position: "insideLeft", fill: "#94a3b8" }}
                />
                <Tooltip
                  contentStyle={{ backgroundColor: "#1e293b", border: "1px solid #475569" }}
                  labelStyle={{ color: "#e2e8f0" }}
                />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="total_voc"
                  stroke="#f97316"
                  strokeWidth={2}
                  name="VOC (ppb)"
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
            <div className="mt-2 text-xs text-slate-400">可依 560 ppb 等級作為警戒參考（約 0.56 ppm）。</div>
          </div>
        </>
      ) : (
        !loading && (
          <div className="bg-slate-900 rounded-lg p-6 text-center text-slate-400">
            目前查詢區間內沒有 604_air_quality 的 CO₂ / VOC 資料。
          </div>
        )
      )}

      {/* PM trend */}
      {pmChartData.length > 0 ? (
        <div className="bg-slate-900 rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">懸浮微粒 PM1.0 / PM2.5 / PM10 變化趨勢（604_window）</h2>
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={pmChartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#475569" />
              <XAxis dataKey="time" stroke="#94a3b8" />
              <YAxis
                stroke="#94a3b8"
                label={{ value: "濃度 (μg/m³)", angle: -90, position: "insideLeft", fill: "#94a3b8" }}
              />
              <Tooltip
                contentStyle={{ backgroundColor: "#1e293b", border: "1px solid #475569" }}
                labelStyle={{ color: "#e2e8f0" }}
              />
              <Legend />
              <Line type="monotone" dataKey="pm1_0" stroke="#22c55e" strokeWidth={2} name="PM1.0" dot={false} />
              <Line type="monotone" dataKey="pm2_5" stroke="#eab308" strokeWidth={2} name="PM2.5" dot={false} />
              <Line type="monotone" dataKey="pm10" stroke="#ef4444" strokeWidth={2} name="PM10" dot={false} />
            </LineChart>
          </ResponsiveContainer>
          <div className="mt-2 text-xs text-slate-400">
            PM2.5 警戒標準：35 μg/m³（24小時平均），PM10 警戒標準：100 μg/m³（24小時平均）。
          </div>
        </div>
      ) : (
        !loading && (
          <div className="bg-slate-900 rounded-lg p-6 text-center text-slate-400">
            目前查詢區間內沒有 604_window 的 PM 資料。
          </div>
        )
      )}

      {/* Temperature & Humidity trend */}
      {tempHumidityChartData.length > 0 ? (
        <div className="bg-slate-900 rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">溫度 / 濕度 變化趨勢（604_center）</h2>
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={tempHumidityChartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#475569" />
              <XAxis dataKey="time" stroke="#94a3b8" />
              <YAxis
                yAxisId="temp"
                stroke="#f97316"
                label={{ value: "溫度 (°C)", angle: -90, position: "insideLeft", fill: "#f97316" }}
              />
              <YAxis
                yAxisId="humidity"
                orientation="right"
                stroke="#0ea5e9"
                label={{ value: "濕度 (%)", angle: 90, position: "insideRight", fill: "#0ea5e9" }}
              />
              <Tooltip
                contentStyle={{ backgroundColor: "#1e293b", border: "1px solid #475569" }}
                labelStyle={{ color: "#e2e8f0" }}
              />
              <Legend />
              <Line yAxisId="temp" type="monotone" dataKey="temperature" stroke="#f97316" strokeWidth={2} name="溫度 (°C)" dot={false} />
              <Line yAxisId="humidity" type="monotone" dataKey="humidity" stroke="#0ea5e9" strokeWidth={2} name="濕度 (%)" dot={false} />
            </LineChart>
          </ResponsiveContainer>
          <div className="mt-2 text-xs text-slate-400">
            舒適溫度範圍：20-26°C，舒適濕度範圍：40-60%。
          </div>
        </div>
      ) : (
        !loading && (
          <div className="bg-slate-900 rounded-lg p-6 text-center text-slate-400">
            目前查詢區間內沒有 604_center 的溫濕度資料。
          </div>
        )
      )}

      {/* 預留：未來教室平面溫度/濕度/PMV/PPD 熱力圖區塊 */}
      <div className="bg-slate-900 rounded-lg p-6 border border-dashed border-slate-700">
        <h2 className="text-xl font-semibold mb-2">教室平面熱力圖（溫度 / 濕度 / PMV / PPD）</h2>
        <p className="text-sm text-slate-400">
          未來會在這裡加入基於 wiolink 多個感測器位置的教室平面熱力圖，對應溫度、濕度與 PMV/PPD 分佈。
        </p>
      </div>
    </div>
  );
}

