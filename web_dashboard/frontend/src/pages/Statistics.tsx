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
  type PeopleTrendResponse,
  type PeopleDistributionResponse,
  type TimePeriodStatsResponse,
} from "../services/api";

export const Statistics: React.FC = () => {
  const [sessionId, setSessionId] = useState("604_windowside");
  const [interval, setInterval] = useState<"hour" | "day">("hour");
  const [startTime, setStartTime] = useState<string>("");
  const [endTime, setEndTime] = useState<string>("");

  const [trendData, setTrendData] = useState<PeopleTrendResponse | null>(null);
  const [distributionData, setDistributionData] = useState<PeopleDistributionResponse | null>(null);
  const [statsData, setStatsData] = useState<TimePeriodStatsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toUtcIso = (local: string | null): string | undefined => {
    if (!local) return undefined;
    const d = new Date(local + "Z"); // Add 'Z' to force UTC interpretation
    if (Number.isNaN(d.getTime())) return undefined;
    return d.toISOString();
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

      const [trend, distribution, stats] = await Promise.all([
        fetchPeopleTrend(params),
        fetchPeopleDistribution(params),
        fetchTimePeriodStats(params),
      ]);

      setTrendData(trend);
      setDistributionData(distribution);
      setStatsData(stats);
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

  return (
    <div className="container mx-auto px-4 py-6 space-y-6">
      <h1 className="text-2xl font-bold mb-6">統計分析</h1>

      {/* Filters */}
      <div className="bg-slate-900 rounded-lg p-4 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
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
        <div className="bg-slate-900 rounded-lg p-6 text-center text-slate-400">
          沒有資料，請調整查詢條件後重試
        </div>
      )}
    </div>
  );
};

