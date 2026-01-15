import React, { useState, useEffect } from "react";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import {
  fetchPeopleTrend,
  fetchPeopleDistribution,
  fetchTimePeriodStats,
  fetchPeopleEnvTimeseries,
  type PeopleTrendResponse,
  type PeopleDistributionResponse,
  type TimePeriodStatsResponse,
  type PeopleEnvTimeseriesResponse,
} from "../services/api";

export const Statistics: React.FC = () => {
  const [sessionId, setSessionId] = useState("604_windowside");
  const [interval, setInterval] = useState<"hour" | "day">("hour");
  const [startTime, setStartTime] = useState<string>("");
  const [endTime, setEndTime] = useState<string>("");
  const [sensorName, setSensorName] = useState<string>("");
  const [envMetric, setEnvMetric] = useState<"celsius_degree" | "co2eq" | "pm2_5_atm" | "humidity">("celsius_degree");

  const [trendData, setTrendData] = useState<PeopleTrendResponse | null>(null);
  const [distributionData, setDistributionData] = useState<PeopleDistributionResponse | null>(null);
  const [statsData, setStatsData] = useState<TimePeriodStatsResponse | null>(null);
  const [peopleEnvData, setPeopleEnvData] = useState<PeopleEnvTimeseriesResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toUtcIso = (local: string | null): string | undefined => {
    if (!local) return undefined;
    const d = new Date(local + "Z"); // Add 'Z' to force UTC interpretation
    if (Number.isNaN(d.getTime())) return undefined;
    return d.toISOString();
  };

  // 將 UTC Date 轉成 datetime-local 用的字串 (YYYY-MM-DDTHH:mm)，直接以 UTC 為基準
  const formatUtcForInput = (d: Date): string => {
    const pad2 = (n: number) => n.toString().padStart(2, "0");
    const year = d.getUTCFullYear();
    const month = pad2(d.getUTCMonth() + 1);
    const day = pad2(d.getUTCDate());
    const hours = pad2(d.getUTCHours());
    const minutes = pad2(d.getUTCMinutes());
    return `${year}-${month}-${day}T${hours}:${minutes}`;
  };

  const applyRangePreset = (range: "today" | "week" | "month") => {
    const now = new Date();

    if (range === "today") {
      // 當天：UTC 今日 00:00 ~ 現在 UTC
      const start = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate(), 0, 0, 0, 0));
      const end = new Date(
        Date.UTC(
          now.getUTCFullYear(),
          now.getUTCMonth(),
          now.getUTCDate(),
          now.getUTCHours(),
          now.getUTCMinutes(),
          0,
          0
        )
      );
      setStartTime(formatUtcForInput(start));
      setEndTime(formatUtcForInput(end));
      return;
    }

    if (range === "week") {
      // 當周：以星期一為一周開始 (UTC)
      const dow = now.getUTCDay(); // 0: Sunday, 1: Monday, ...
      const offset = dow === 0 ? 6 : dow - 1; // Monday-based
      const monday = new Date(
        Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() - offset, 0, 0, 0, 0)
      );
      const end = new Date(
        Date.UTC(
          now.getUTCFullYear(),
          now.getUTCMonth(),
          now.getUTCDate(),
          now.getUTCHours(),
          now.getUTCMinutes(),
          0,
          0
        )
      );
      setStartTime(formatUtcForInput(monday));
      setEndTime(formatUtcForInput(end));
      return;
    }

    if (range === "month") {
      // 當月：當月 1 號 00:00 ~ 現在 UTC
      const firstDay = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), 1, 0, 0, 0, 0));
      const end = new Date(
        Date.UTC(
          now.getUTCFullYear(),
          now.getUTCMonth(),
          now.getUTCDate(),
          now.getUTCHours(),
          now.getUTCMinutes(),
          0,
          0
        )
      );
      setStartTime(formatUtcForInput(firstDay));
      setEndTime(formatUtcForInput(end));
    }
  };

  const loadStatistics = async () => {
    if (!sessionId) {
      setError("請輸入 Session ID");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const params = {
        session_id: sessionId,
        interval,
        start_time: toUtcIso(startTime),
        end_time: toUtcIso(endTime),
      };

      const [trend, distribution, stats, peopleEnv] = await Promise.all([
        fetchPeopleTrend(params),
        fetchPeopleDistribution(params),
        fetchTimePeriodStats(params),
        fetchPeopleEnvTimeseries({
          session_id: sessionId,
          start_time: params.start_time,
          end_time: params.end_time,
          sensor_name: sensorName || undefined,
        }),
      ]);

      setTrendData(trend);
      setDistributionData(distribution);
      setStatsData(stats);
      setPeopleEnvData(peopleEnv);
    } catch (err) {
      setError(err instanceof Error ? err.message : "載入統計資料時發生錯誤");
      console.error("Error loading statistics:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Auto-load on mount with default session
    if (sessionId) {
      loadStatistics();
    }
  }, []);

  // Prepare distribution chart data
  const distributionChartData = distributionData
    ? Object.entries(distributionData.distribution)
        .map(([count, freq]) => ({
          people_count: parseInt(count),
          frequency: freq,
        }))
        .sort((a, b) => a.people_count - b.people_count)
    : [];

  // Prepare trend chart data
  const trendChartData = trendData
    ? trendData.points.map((point) => {
        const date = new Date(point.time);
        // Format as UTC time to avoid timezone offset
        let timeStr = "";
        if (interval === "hour") {
          timeStr = `${date.getUTCMonth() + 1}/${date.getUTCDate()} ${date.getUTCHours()}:00`;
        } else {
          timeStr = `${date.getUTCMonth() + 1}/${date.getUTCDate()}`;
        }
        return {
          time: timeStr,
          avg: point.avg_people,
          max: point.max_people,
          min: point.min_people,
        };
      })
    : [];

  // Prepare people vs environment timeseries data
  const peopleEnvChartData =
    peopleEnvData && peopleEnvData.points.length > 0
      ? peopleEnvData.points.map((point) => {
          const date = new Date(point.time);
          const timeStr = `${date.getUTCMonth() + 1}/${date.getUTCDate()} ${date.getUTCHours()}:${date
            .getUTCMinutes()
            .toString()
            .padStart(2, "0")}`;

          const envValue =
            envMetric === "celsius_degree"
              ? point.celsius_degree
              : envMetric === "co2eq"
              ? point.co2eq
              : envMetric === "pm2_5_atm"
              ? point.pm2_5_atm
              : point.humidity;

          return {
            time: timeStr,
            people: point.people_count,
            env: envValue,
            sensor_name: point.sensor_name,
          };
        })
      : [];

  return (
    <div className="container mx-auto px-4 py-6 space-y-6">
      <h1 className="text-2xl font-bold mb-6">統計分析</h1>

      {/* Filters */}
      <div className="bg-slate-900 rounded-lg p-4 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">Session ID</label>
            <input
              type="text"
              value={sessionId}
              onChange={(e) => setSessionId(e.target.value)}
              className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-md text-slate-50"
              placeholder="604_windowside"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">時間間隔</label>
            <select
              value={interval}
              onChange={(e) => setInterval(e.target.value as "hour" | "day")}
              className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-md text-slate-50"
            >
              <option value="hour">小時</option>
              <option value="day">天</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">開始時間 (UTC)</label>
            <input
              type="datetime-local"
              value={startTime}
              onChange={(e) => setStartTime(e.target.value)}
              className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-md text-slate-50 [&::-webkit-calendar-picker-indicator]:invert [&::-webkit-calendar-picker-indicator]:cursor-pointer"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">結束時間 (UTC)</label>
            <input
              type="datetime-local"
              value={endTime}
              onChange={(e) => setEndTime(e.target.value)}
              className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-md text-slate-50 [&::-webkit-calendar-picker-indicator]:invert [&::-webkit-calendar-picker-indicator]:cursor-pointer"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">環境感測器名稱 (選填)</label>
            <input
              type="text"
              value={sensorName}
              onChange={(e) => setSensorName(e.target.value)}
              className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-md text-slate-50"
              placeholder="例如：604_air_quality"
            />
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <span className="text-sm text-slate-400 mr-2">快速區間：</span>
          <button
            type="button"
            onClick={() => applyRangePreset("today")}
            className="px-3 py-1.5 rounded-md bg-slate-800 hover:bg-slate-700 text-sm text-slate-100 border border-slate-700"
          >
            當天 (UTC)
          </button>
          <button
            type="button"
            onClick={() => applyRangePreset("week")}
            className="px-3 py-1.5 rounded-md bg-slate-800 hover:bg-slate-700 text-sm text-slate-100 border border-slate-700"
          >
            當周 (UTC)
          </button>
          <button
            type="button"
            onClick={() => applyRangePreset("month")}
            className="px-3 py-1.5 rounded-md bg-slate-800 hover:bg-slate-700 text-sm text-slate-100 border border-slate-700"
          >
            當月 (UTC)
          </button>
        </div>
        <button
          onClick={loadStatistics}
          disabled={loading}
          className="px-4 py-2 bg-sky-600 hover:bg-sky-700 disabled:bg-slate-700 disabled:cursor-not-allowed rounded-md text-sm font-medium"
        >
          {loading ? "載入中..." : "查詢統計"}
        </button>
      </div>

      {error && (
        <div className="bg-red-900/50 border border-red-700 rounded-lg p-4 text-red-200">
          {error}
        </div>
      )}

      {/* Summary Statistics */}
      {statsData && (
        <div className="bg-slate-900 rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">摘要統計</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            <div className="bg-slate-800 rounded-lg p-4">
              <div className="text-sm text-slate-400">總幀數</div>
              <div className="text-2xl font-bold">{statsData.total_frames}</div>
            </div>
            <div className="bg-slate-800 rounded-lg p-4">
              <div className="text-sm text-slate-400">平均人數</div>
              <div className="text-2xl font-bold">{statsData.avg_people.toFixed(2)}</div>
            </div>
            <div className="bg-slate-800 rounded-lg p-4">
              <div className="text-sm text-slate-400">中位數</div>
              <div className="text-2xl font-bold">{statsData.median_people.toFixed(2)}</div>
            </div>
            <div className="bg-slate-800 rounded-lg p-4">
              <div className="text-sm text-slate-400">最大值</div>
              <div className="text-2xl font-bold">{statsData.max_people}</div>
            </div>
            <div className="bg-slate-800 rounded-lg p-4">
              <div className="text-sm text-slate-400">最小值</div>
              <div className="text-2xl font-bold">{statsData.min_people}</div>
            </div>
            <div className="bg-slate-800 rounded-lg p-4">
              <div className="text-sm text-slate-400">標準差</div>
              <div className="text-2xl font-bold">{statsData.std_people.toFixed(2)}</div>
            </div>
          </div>
        </div>
      )}

      {/* Trend Chart */}
      {trendData && trendChartData.length > 0 && (
        <div className="bg-slate-900 rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">人數趨勢</h2>
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={trendChartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#475569" />
              <XAxis dataKey="time" stroke="#94a3b8" />
              <YAxis stroke="#94a3b8" />
              <Tooltip
                contentStyle={{ backgroundColor: "#1e293b", border: "1px solid #475569" }}
                labelStyle={{ color: "#e2e8f0" }}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey="avg"
                stroke="#0ea5e9"
                strokeWidth={2}
                name="平均人數"
                dot={{ r: 4 }}
              />
              <Line
                type="monotone"
                dataKey="max"
                stroke="#f59e0b"
                strokeWidth={2}
                name="最大人數"
                dot={{ r: 4 }}
              />
              <Line
                type="monotone"
                dataKey="min"
                stroke="#10b981"
                strokeWidth={2}
                name="最小人數"
                dot={{ r: 4 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* People vs Environment Timeseries */}
      {peopleEnvData && peopleEnvChartData.length > 0 && (
        <div className="bg-slate-900 rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold">人數 vs 環境感測器時序</h2>
            <div className="flex items-center gap-3">
              <span className="text-sm text-slate-400">環境指標</span>
              <select
                value={envMetric}
                onChange={(e) =>
                  setEnvMetric(e.target.value as "celsius_degree" | "co2eq" | "pm2_5_atm" | "humidity")
                }
                className="px-3 py-1.5 bg-slate-800 border border-slate-700 rounded-md text-slate-50 text-sm"
              >
                <option value="celsius_degree">溫度 (°C)</option>
                <option value="co2eq">CO₂ 等效濃度</option>
                <option value="pm2_5_atm">PM2.5</option>
                <option value="humidity">相對濕度 (%)</option>
              </select>
            </div>
          </div>

          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={peopleEnvChartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#475569" />
              <XAxis dataKey="time" stroke="#94a3b8" />
              <YAxis
                yAxisId="left"
                stroke="#0ea5e9"
                label={{ value: "人數", angle: -90, position: "insideLeft", fill: "#0ea5e9" }}
              />
              <YAxis
                yAxisId="right"
                orientation="right"
                stroke="#f97316"
                label={{
                  value:
                    envMetric === "celsius_degree"
                      ? "溫度 (°C)"
                      : envMetric === "co2eq"
                      ? "CO₂ 等效濃度"
                      : envMetric === "pm2_5_atm"
                      ? "PM2.5"
                      : "相對濕度 (%)",
                  angle: -90,
                  position: "insideRight",
                  fill: "#f97316",
                }}
              />
              <Tooltip
                contentStyle={{ backgroundColor: "#1e293b", border: "1px solid #475569" }}
                labelStyle={{ color: "#e2e8f0" }}
              />
              <Legend />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="people"
                stroke="#0ea5e9"
                strokeWidth={2}
                name="人數"
                dot={{ r: 3 }}
              />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="env"
                stroke="#f97316"
                strokeWidth={2}
                name="環境指標"
                dot={{ r: 3 }}
                connectNulls
              />
            </LineChart>
          </ResponsiveContainer>

          {/* Simple note about sensor name */}
          <div className="mt-3 text-sm text-slate-400">
            感測器：
            {sensorName
              ? sensorName
              : peopleEnvData.points[0]?.sensor_name || "（沒有指定名稱，顯示最近的 wiolink 資料）"}
          </div>
        </div>
      )}

      {/* Distribution Chart */}
      {distributionData && distributionChartData.length > 0 && (
        <div className="bg-slate-900 rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">人數分佈</h2>
          <ResponsiveContainer width="100%" height={400}>
            <BarChart data={distributionChartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#475569" />
              <XAxis dataKey="people_count" stroke="#94a3b8" label={{ value: "人數", position: "insideBottom", offset: -5, fill: "#94a3b8" }} />
              <YAxis stroke="#94a3b8" label={{ value: "出現次數", angle: -90, position: "insideLeft", fill: "#94a3b8" }} />
              <Tooltip
                contentStyle={{ backgroundColor: "#1e293b", border: "1px solid #475569" }}
                labelStyle={{ color: "#e2e8f0" }}
              />
              <Bar dataKey="frequency" fill="#0ea5e9" name="出現次數" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {!loading && !error && (!trendData || trendData.points.length === 0) && (
        <div className="bg-slate-900 rounded-lg p-6 text-center text-slate-400 space-y-2">
          <div>人數統計沒有資料，請調整查詢條件後重試。</div>
          {peopleEnvData && peopleEnvData.points.length === 0 && (
            <div>環境感測器配對資料也為空，可能該時段沒有 wiolink 紀錄。</div>
          )}
        </div>
      )}
    </div>
  );
};

