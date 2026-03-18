import React from "react";
import { BarChart2, LineChart as LineChartIcon, PieChart as PieChartIcon } from "lucide-react";
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import type { ChartSuggestion } from "@/types";

interface ChartDisplayProps {
  chart: ChartSuggestion;
  colNames: string[];
  rows: any[][];
}

const COLORS = [
  "#acbe57", "#808b34", "#99aa42",
  "#c0cf7e", "#585b28", "#686e2b",
];

const chartTypes = [
  { type: "bar", Icon: BarChart2 },
  { type: "line", Icon: LineChartIcon },
  { type: "pie", Icon: PieChartIcon },
];

const ChartDisplay: React.FC<ChartDisplayProps> = ({ chart, colNames, rows }) => {
  const xIdx = colNames.indexOf(chart.x_axis);
  const yIdx = colNames.indexOf(chart.y_axis);

  const data = rows.map((row) => {
    const obj: any = {};
    colNames.forEach((col, i) => { obj[col] = row[i]; });
    return obj;
  });

  const commonProps = { data, margin: { top: 10, right: 20, left: 10, bottom: 10 } };

  const tickStyle = { fill: "#99a870", fontSize: 11 };
  const tooltipStyle = { background: "#4c4e27", border: "1px solid #585b28", borderRadius: 4, color: "#e8edcc" };
  const gridStroke = "#585b28";

  return (
    <div className="relative">
      {/* Chart type indicators */}
      <div className="absolute top-0 right-0 flex items-center gap-1 z-10">
        {chartTypes.map(({ type, Icon }) => (
          <div
            key={type}
            className={`p-1 rounded-[2px] ${chart.type === type ? "text-primary" : "text-muted-foreground"}`}
          >
            <Icon size={14} />
          </div>
        ))}
      </div>

      {chart.type === "bar" && (
        <ResponsiveContainer width="100%" height={300}>
          <BarChart {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} />
            <XAxis dataKey={chart.x_axis} tick={tickStyle} />
            <YAxis tick={tickStyle} />
            <Tooltip contentStyle={tooltipStyle} />
            <Bar dataKey={chart.y_axis} fill="#acbe57" radius={[2, 2, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      )}

      {chart.type === "line" && (
        <ResponsiveContainer width="100%" height={300}>
          <LineChart {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} />
            <XAxis dataKey={chart.x_axis} tick={tickStyle} />
            <YAxis tick={tickStyle} />
            <Tooltip contentStyle={tooltipStyle} />
            <Line type="monotone" dataKey={chart.y_axis} stroke="#acbe57" strokeWidth={2} dot={{ fill: "#acbe57" }} />
          </LineChart>
        </ResponsiveContainer>
      )}

      {chart.type === "pie" && (
        <ResponsiveContainer width="100%" height={300}>
          <PieChart>
            <Pie data={data} dataKey={colNames[1]} nameKey={colNames[0]} cx="50%" cy="50%" outerRadius={100} label>
              {data.map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip contentStyle={tooltipStyle} />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      )}
    </div>
  );
};

export default ChartDisplay;
