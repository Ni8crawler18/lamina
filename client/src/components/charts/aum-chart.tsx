"use client";

import dynamic from "next/dynamic";

const AreaChart = dynamic(
  () => import("recharts").then((mod) => mod.AreaChart),
  { ssr: false }
);
const Area = dynamic(
  () => import("recharts").then((mod) => mod.Area),
  { ssr: false }
);
const XAxis = dynamic(
  () => import("recharts").then((mod) => mod.XAxis),
  { ssr: false }
);
const YAxis = dynamic(
  () => import("recharts").then((mod) => mod.YAxis),
  { ssr: false }
);
const Tooltip = dynamic(
  () => import("recharts").then((mod) => mod.Tooltip),
  { ssr: false }
);
const ResponsiveContainer = dynamic(
  () => import("recharts").then((mod) => mod.ResponsiveContainer),
  { ssr: false }
);

interface AUMDataPoint {
  date: string;
  aum: number;
}

export default function AUMChart({ data }: { data: AUMDataPoint[] }) {
  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-[200px] text-sm text-muted-foreground">
        No data yet
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={200}>
      <AreaChart data={data} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
        <defs>
          <linearGradient id="aumGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#8259ef" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#8259ef" stopOpacity={0} />
          </linearGradient>
        </defs>
        <XAxis
          dataKey="date"
          tick={{ fontSize: 10, fill: "#888" }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={{ fontSize: 10, fill: "#888" }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v: number) => `$${(v / 1000000).toFixed(1)}M`}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: "hsl(226, 20%, 7%)",
            border: "1px solid hsl(226, 15%, 13%)",
            borderRadius: "8px",
            fontSize: "12px",
          }}
          formatter={(value) => [`$${Number(value).toLocaleString()}`, "AUM"]}
        />
        <Area
          type="monotone"
          dataKey="aum"
          stroke="#8259ef"
          strokeWidth={2}
          fill="url(#aumGradient)"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
