"use client";

import type { CriticReport } from "@/lib/types";

interface Props {
  report: CriticReport;
}

function ScoreGauge({ label, value, threshold }: { label: string; value: number; threshold: number }) {
  const percentage = Math.round(value * 100);
  const passed = value >= threshold;
  const color = passed ? "#22c55e" : value >= threshold * 0.8 ? "#f97316" : "#ef4444";

  return (
    <div className="flex items-center gap-3">
      <div className="w-32 text-xs text-gray-400">{label}</div>
      <div className="flex-1 h-2 bg-[#1e1e1e] rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${percentage}%`, backgroundColor: color }}
        />
      </div>
      <div className="w-12 text-xs text-right font-mono" style={{ color }}>
        {percentage}%
      </div>
    </div>
  );
}

export default function QualityScores({ report }: Props) {
  return (
    <div className="bg-[#141414] rounded-lg border border-[#333] p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-300">Quality Evaluation</h3>
        <span
          className={`text-xs px-2 py-0.5 rounded-full font-medium ${
            report.passed
              ? "bg-green-900/50 text-green-400"
              : "bg-red-900/50 text-red-400"
          }`}
        >
          {report.passed ? "PASSED" : "BELOW THRESHOLD"}
        </span>
      </div>

      <div className="space-y-2">
        <ScoreGauge label="Citation Accuracy" value={report.citation_accuracy} threshold={0.85} />
        <ScoreGauge label="Claim Grounding" value={report.claim_grounding_score} threshold={0.80} />
        <ScoreGauge label="Consistency" value={report.internal_consistency} threshold={1.0} />
        <ScoreGauge label="Audience Fit" value={report.audience_alignment} threshold={0.70} />
        <ScoreGauge label="Completeness" value={report.completeness} threshold={0.60} />
      </div>

      <div className="border-t border-[#333] pt-2">
        <ScoreGauge label="Overall" value={report.overall_score} threshold={0.80} />
      </div>

      {report.issues.length > 0 && (
        <details className="text-xs">
          <summary className="text-gray-500 cursor-pointer hover:text-gray-300">
            {report.issues.length} issue(s) found
          </summary>
          <div className="mt-2 space-y-1">
            {report.issues.map((issue, i) => (
              <div
                key={i}
                className={`p-2 rounded text-gray-400 ${
                  issue.severity === "error" ? "bg-red-900/20" : "bg-yellow-900/20"
                }`}
              >
                <span className="font-medium">[{issue.severity}]</span> {issue.description}
              </div>
            ))}
          </div>
        </details>
      )}
    </div>
  );
}
