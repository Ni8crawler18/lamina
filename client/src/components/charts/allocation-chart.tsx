"use client";

import dynamic from "next/dynamic";

const PieChart = dynamic(
  () => import("recharts").then((mod) => mod.PieChart),
  { ssr: false }
);
const Pie = dynamic(
  () => import("recharts").then((mod) => mod.Pie),
  { ssr: false }
);
const Cell = dynamic(
  () => import("recharts").then((mod) => mod.Cell),
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

const COLORS = ["#8259ef", "#b47aff", "#6366f1", "#a78bfa", "#818cf8"];

interface AllocationData {
  name: string;
  value: number;
}

export default function AllocationChart({ data }: { data: AllocationData[] }) {
  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-[200px] text-sm text-muted-foreground">
        No data yet
      </div>
    );
  }

  return (
    <div className="flex items-center gap-6">
      <ResponsiveContainer width={160} height={160}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={45}
            outerRadius={70}
            paddingAngle={3}
            dataKey="value"
          >
            {data.map((_, i) => (
              <Cell key={i} fill={COLORS[i % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              backgroundColor: "hsl(226, 20%, 7%)",
              border: "1px solid hsl(226, 15%, 13%)",
              borderRadius: "8px",
              fontSize: "12px",
            }}
            formatter={(value) => [`$${Number(value).toLocaleString()}`, "Value"]}
          />
        </PieChart>
      </ResponsiveContainer>
      <div className="space-y-2">
        {data.map((item, i) => (
          <div key={i} className="flex items-center gap-2 text-xs">
            <span
              className="w-2.5 h-2.5 rounded-sm flex-shrink-0"
              style={{ backgroundColor: COLORS[i % COLORS.length] }}
            />
            <span className="text-muted-foreground">{item.name}</span>
            <span className="font-medium ml-auto">${item.value.toLocaleString()}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
