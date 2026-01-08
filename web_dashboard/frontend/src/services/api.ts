import axios from "axios";

export const api = axios.create({
  baseURL: "/api"
});

export interface ThermalLatestResponse {
  frame_id: number;
  session_id: string;
  timestamp: string;
  people_count: number;
  people_count_rounded: number;
  density_map: {
    data: number[];
    shape: [number, number];
  } | null;
  thermal_image: {
    data: number[];
    shape: [number, number];
  } | null;
}

export interface HistoryFrameSummary {
  frame_id: number;
  session_id: string;
  timestamp: string;
  people_count: number;
  people_count_rounded: number;
}

export async function fetchLatestThermal(sessionId: string): Promise<ThermalLatestResponse> {
  const res = await api.get<ThermalLatestResponse>("/realtime/thermal-latest", {
    params: { session_id: sessionId }
  });
  return res.data;
}

export async function fetchThermalHistory(params: {
  session_id: string;
  start_time?: string;
  end_time?: string;
  limit?: number;
  offset?: number;
}): Promise<HistoryFrameSummary[]> {
  const res = await api.get<HistoryFrameSummary[]>("/history/thermal", {
    params,
  });
  return res.data;
}

export async function fetchThermalById(frameId: number): Promise<ThermalLatestResponse> {
  const res = await api.get<ThermalLatestResponse>("/realtime/thermal-by-id", {
    params: { frame_id: frameId },
  });
  return res.data;
}

// Statistics API
export interface TrendPoint {
  time: string;
  avg_people: number;
  max_people: number;
  min_people: number;
  count: number;
}

export interface PeopleTrendResponse {
  session_id: string;
  interval: string;
  points: TrendPoint[];
}

export interface PeopleDistributionResponse {
  session_id: string;
  distribution: Record<number, number>;
  total_frames: number;
}

export interface TimePeriodStatsResponse {
  session_id: string;
  total_frames: number;
  avg_people: number;
  max_people: number;
  min_people: number;
  median_people: number;
  std_people: number;
}

export async function fetchPeopleTrend(params: {
  session_id: string;
  interval?: "hour" | "day";
  start_time?: string;
  end_time?: string;
}): Promise<PeopleTrendResponse> {
  const res = await api.get<PeopleTrendResponse>("/statistics/people-trend", {
    params,
  });
  return res.data;
}

export async function fetchPeopleDistribution(params: {
  session_id: string;
  start_time?: string;
  end_time?: string;
}): Promise<PeopleDistributionResponse> {
  const res = await api.get<PeopleDistributionResponse>("/statistics/people-distribution", {
    params,
  });
  return res.data;
}

export async function fetchTimePeriodStats(params: {
  session_id: string;
  start_time?: string;
  end_time?: string;
}): Promise<TimePeriodStatsResponse> {
  const res = await api.get<TimePeriodStatsResponse>("/statistics/time-period-stats", {
    params,
  });
  return res.data;
}


