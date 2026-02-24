"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";

interface DataPoint {
  skill: string;
  count: number;
}

interface Props {
  data: DataPoint[];
}

export default function TopSkillsChart({ data }: Props) {
  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-slate-500 text-sm">
        No data for this period
      </div>
    );
  }

  const chartData = [...data].reverse();

  return (
    <ResponsiveContainer width="100%" height={Math.max(300, chartData.length * 26)}>
      <BarChart data={chartData} layout="vertical" margin={{ left: 8, right: 24 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" horizontal={false} />
        <XAxis
          type="number"
          tick={{ fill: "#94a3b8", fontSize: 11 }}
          tickLine={false}
          axisLine={{ stroke: "#334155" }}
          allowDecimals={false}
        />
        <YAxis
          type="category"
          dataKey="skill"
          width={140}
          tick={{ fill: "#94a3b8", fontSize: 11 }}
          tickLine={false}
          axisLine={false}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: "#1e293b",
            border: "1px solid #334155",
            borderRadius: "8px",
            color: "#e2e8f0",
          }}
          cursor={{ fill: "#1e293b" }}
        />
        <Bar dataKey="count" radius={[0, 4, 4, 0]}>
          {chartData.map((_, i) => (
            <Cell
              key={i}
              fill={`hsl(${210 + i * 5}, 70%, ${50 + i * 1}%)`}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
