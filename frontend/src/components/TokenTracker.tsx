"use client";

import type { TokenUsage } from "@/lib/types";
import { AGENT_COLORS, AGENT_LABELS } from "@/lib/constants";

interface Props {
  usage: TokenUsage[];
  totalTime?: number;
  revisionCount?: number;
}

export default function TokenTracker({ usage, totalTime, revisionCount }: Props) {
  const byAgent: Record<string, { input: number; output: number; calls: number }> = {};
  let totalInput = 0;
  let totalOutput = 0;

  for (const u of usage) {
    if (!byAgent[u.agent]) {
      byAgent[u.agent] = { input: 0, output: 0, calls: 0 };
    }
    byAgent[u.agent].input += u.input_tokens;
    byAgent[u.agent].output += u.output_tokens;
    byAgent[u.agent].calls += 1;
    totalInput += u.input_tokens;
    totalOutput += u.output_tokens;
  }

  // Estimated cost at paid rates
  const estimatedCost = (totalInput / 1e6) * 0.15 + (totalOutput / 1e6) * 0.60;

  return (
    <div className="bg-[#141414] rounded-lg border border-[#333] p-4 space-y-3">
      <h3 className="text-sm font-semibold text-gray-300">Token Usage</h3>

      <div className="grid grid-cols-3 gap-2 text-center">
        <div className="bg-[#1e1e1e] rounded-lg p-2">
          <div className="text-lg font-bold text-blue-400">{totalInput.toLocaleString()}</div>
          <div className="text-xs text-gray-500">Input tokens</div>
        </div>
        <div className="bg-[#1e1e1e] rounded-lg p-2">
          <div className="text-lg font-bold text-green-400">{totalOutput.toLocaleString()}</div>
          <div className="text-xs text-gray-500">Output tokens</div>
        </div>
        <div className="bg-[#1e1e1e] rounded-lg p-2">
          <div className="text-lg font-bold text-yellow-400">${estimatedCost.toFixed(4)}</div>
          <div className="text-xs text-gray-500">Est. cost</div>
        </div>
      </div>

      {totalTime !== undefined && (
        <div className="flex justify-between text-xs text-gray-500">
          <span>Time: {totalTime.toFixed(1)}s</span>
          {revisionCount !== undefined && <span>Revisions: {revisionCount}</span>}
        </div>
      )}

      <div className="space-y-1">
        {Object.entries(byAgent).map(([agent, data]) => (
          <div key={agent} className="flex items-center gap-2 text-xs">
            <span
              className="w-2 h-2 rounded-full"
              style={{ backgroundColor: AGENT_COLORS[agent] || "#666" }}
            />
            <span className="text-gray-400 w-24">
              {AGENT_LABELS[agent] || agent}
            </span>
            <span className="text-gray-500">
              {data.input.toLocaleString()} in / {data.output.toLocaleString()} out ({data.calls} calls)
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
