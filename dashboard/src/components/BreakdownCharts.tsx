"use client";

import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

interface LabelCount {
  label: string;
  count: number;
}

interface Props {
  employmentType: LabelCount[];
  experienceLevel: LabelCount[];
  sourceSite: LabelCount[];
}

const PALETTE = [
  "#10b981",
  "#3b82f6",
  "#f59e0b",
  "#8b5cf6",
  "#ef4444",
  "#06b6d4",
  "#f97316",
];

function MiniPie({ title, data }: { title: string; data: LabelCount[] }) {
  const pieData = data.map((d) => ({ name: d.label, value: d.count }));

  if (pieData.length === 0) {
    return (
      <div className="bg-slate-800 border border-slate-700 rounded-xl p-4">
        <h3 className="text-sm font-medium text-slate-300 mb-3">{title}</h3>
        <div className="flex items-center justify-center h-32 text-slate-500 text-xs">
          No data
        </div>
      </div>
    );
  }

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-xl p-4">
      <h3 className="text-sm font-medium text-slate-300 mb-1">{title}</h3>
      <ResponsiveContainer width="100%" height={200}>
        <PieChart>
          <Pie
            data={pieData}
            cx="50%"
            cy="50%"
            innerRadius={50}
            outerRadius={75}
            paddingAngle={2}
            dataKey="value"
          >
            {pieData.map((_, i) => (
              <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              backgroundColor: "#1e293b",
              border: "1px solid #334155",
              borderRadius: "8px",
              color: "#e2e8f0",
              fontSize: 12,
            }}
          />
          <Legend
            wrapperStyle={{ color: "#94a3b8", fontSize: 11 }}
            iconType="circle"
            iconSize={8}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}

export default function BreakdownCharts({
  employmentType,
  experienceLevel,
  sourceSite,
}: Props) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      <MiniPie title="Employment Type" data={employmentType} />
      <MiniPie title="Experience Level" data={experienceLevel} />
      <MiniPie title="Source Site" data={sourceSite} />
    </div>
  );
}
