"use client";

import dynamic from "next/dynamic";
import type { ChartSpec } from "@/lib/types";

const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

interface Props {
  chart: ChartSpec;
}

export default function ChartEmbed({ chart }: Props) {
  const layout = {
    ...chart.plotly_json?.layout,
    paper_bgcolor: "#141414",
    plot_bgcolor: "#1e1e1e",
    font: { color: "#ededed", size: 12 },
    autosize: true,
    margin: { l: 50, r: 30, t: 50, b: 50 },
  };

  return (
    <div className="my-6 bg-[#141414] rounded-lg border border-[#333] overflow-hidden">
      <div className="px-4 py-2 border-b border-[#333] flex items-center justify-between">
        <h4 className="text-sm font-medium text-gray-300">{chart.title}</h4>
        <span className="text-xs text-gray-500">{chart.chart_type}</span>
      </div>
      <div className="p-2">
        <Plot
          data={chart.plotly_json?.data || []}
          layout={layout}
          config={{ responsive: true, displayModeBar: false }}
          style={{ width: "100%", height: "350px" }}
        />
      </div>
      {chart.caption && (
        <div className="px-4 py-2 border-t border-[#333] text-xs text-gray-500">
          {chart.caption}
        </div>
      )}
    </div>
  );
}
