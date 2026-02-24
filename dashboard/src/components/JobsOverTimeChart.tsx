"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { useMemo } from "react";

interface DataPoint {
  date: string;
  source_site: string;
  count: number;
}

interface Props {
  data: DataPoint[];
}

const SITE_COLORS: Record<string, string> = {
  irantalent: "#10b981",
  jobinja: "#3b82f6",
  jobvision: "#f59e0b",
};

export default function JobsOverTimeChart({ data }: Props) {
  const { chartData, sites } = useMemo(() => {
    const dateMap = new Map<string, Record<string, number>>();
    const siteSet = new Set<string>();

    for (const row of data) {
      siteSet.add(row.source_site);
      if (!dateMap.has(row.date)) {
        dateMap.set(row.date, {});
      }
      dateMap.get(row.date)![row.source_site] = row.count;
    }

    const chartData = Array.from(dateMap.entries())
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([date, counts]) => ({
        date: date.slice(5), // MM-DD
        ...counts,
      }));

    return { chartData, sites: Array.from(siteSet) };
  }, [data]);

  if (chartData.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-slate-500 text-sm">
        No data for this period
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
        <XAxis
          dataKey="date"
          tick={{ fill: "#94a3b8", fontSize: 11 }}
          tickLine={false}
          axisLine={{ stroke: "#334155" }}
          interval="preserveStartEnd"
        />
        <YAxis
          tick={{ fill: "#94a3b8", fontSize: 11 }}
          tickLine={false}
          axisLine={false}
          allowDecimals={false}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: "#1e293b",
            border: "1px solid #334155",
            borderRadius: "8px",
            color: "#e2e8f0",
          }}
        />
        <Legend
          wrapperStyle={{ color: "#94a3b8", fontSize: 12 }}
        />
        {sites.map((site) => (
          <Line
            key={site}
            type="monotone"
            dataKey={site}
            stroke={SITE_COLORS[site] || "#8b5cf6"}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
