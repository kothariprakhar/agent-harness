"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import PromptInput from "@/components/PromptInput";
import MessageStream from "@/components/MessageStream";
import TokenTracker from "@/components/TokenTracker";
import QualityScores from "@/components/QualityScores";
import ArticleRenderer from "@/components/ArticleRenderer";
import { usePipeline } from "@/hooks/usePipeline";
import { useWebSocket } from "@/hooks/useWebSocket";

const PipelineDAG = dynamic(() => import("@/components/PipelineDAG"), {
  ssr: false,
});

type Tab = "pipeline" | "article" | "evaluation";

export default function Home() {
  const [activeTab, setActiveTab] = useState<Tab>("pipeline");
  const { status, result, error, run, reset } = usePipeline();
  const { connected, events, clearEvents } = useWebSocket();

  const handleSubmit = (prompt: string, audience: string, tone: string) => {
    clearEvents();
    run(prompt, audience, tone);
  };

  const handleReset = () => {
    reset();
    clearEvents();
    setActiveTab("pipeline");
  };

  return (
    <main className="min-h-screen p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold">
          AgentHarness
          <span className="text-gray-500 text-lg font-normal ml-2">
            Deep Research Pipeline
          </span>
        </h1>
        <div className="flex items-center gap-3 mt-1">
          <span
            className={`w-2 h-2 rounded-full ${
              connected ? "bg-green-500" : "bg-red-500"
            }`}
          />
          <span className="text-xs text-gray-500">
            {connected ? "Connected" : "Disconnected"}
          </span>
          {status === "completed" && (
            <button
              onClick={handleReset}
              className="text-xs text-blue-400 hover:text-blue-300"
            >
              New Article
            </button>
          )}
        </div>
      </div>

      {/* Prompt Input */}
      <div className="mb-6">
        <PromptInput
          onSubmit={handleSubmit}
          disabled={status === "running"}
        />
      </div>

      {/* Error display */}
      {error && (
        <div className="mb-4 p-3 bg-red-900/30 border border-red-700 rounded-lg text-red-300 text-sm">
          {error}
        </div>
      )}

      {/* Loading state */}
      {status === "running" && (
        <div className="mb-4 p-3 bg-blue-900/30 border border-blue-700 rounded-lg text-blue-300 text-sm flex items-center gap-2">
          <div className="w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
          Generating article... This may take a few minutes.
        </div>
      )}

      {/* Tabs */}
      {(status !== "idle" || result) && (
        <>
          <div className="flex gap-1 mb-4 border-b border-[#333]">
            {(["pipeline", "article", "evaluation"] as Tab[]).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-2 text-sm font-medium capitalize transition-colors ${
                  activeTab === tab
                    ? "text-blue-400 border-b-2 border-blue-400"
                    : "text-gray-500 hover:text-gray-300"
                }`}
                disabled={
                  (tab === "article" || tab === "evaluation") && !result
                }
              >
                {tab}
              </button>
            ))}
          </div>

          {/* Pipeline View */}
          {activeTab === "pipeline" && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              <div className="lg:col-span-2 space-y-4">
                <PipelineDAG events={events} />
                <MessageStream events={events} />
              </div>
              <div className="space-y-4">
                {result && (
                  <>
                    <TokenTracker
                      usage={result.token_usage}
                      totalTime={result.total_time_seconds}
                      revisionCount={result.revision_count}
                    />
                    <QualityScores report={result.evaluation} />
                  </>
                )}
              </div>
            </div>
          )}

          {/* Article View */}
          {activeTab === "article" && result && (
            <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
              <div className="lg:col-span-3">
                <ArticleRenderer
                  article={result.article}
                  charts={result.charts}
                  artifacts={result.artifacts}
                />
              </div>
              <div className="space-y-4">
                <QualityScores report={result.evaluation} />
                <TokenTracker
                  usage={result.token_usage}
                  totalTime={result.total_time_seconds}
                  revisionCount={result.revision_count}
                />
              </div>
            </div>
          )}

          {/* Evaluation View */}
          {activeTab === "evaluation" && result && (
            <div className="max-w-3xl mx-auto space-y-6">
              <QualityScores report={result.evaluation} />

              {/* Research findings used */}
              <div className="bg-[#141414] rounded-lg border border-[#333] p-4">
                <h3 className="text-sm font-semibold text-gray-300 mb-3">
                  Research Findings ({result.research.findings.length})
                </h3>
                <div className="space-y-2 max-h-96 overflow-y-auto">
                  {result.research.findings.map((f, i) => (
                    <div
                      key={i}
                      className="p-2 bg-[#1e1e1e] rounded text-xs space-y-1"
                    >
                      <div className="text-gray-300">{f.claim}</div>
                      <div className="text-gray-500 italic">
                        &ldquo;{f.supporting_quote.slice(0, 150)}
                        {f.supporting_quote.length > 150 ? "..." : ""}&rdquo;
                      </div>
                      <div className="flex justify-between text-gray-600">
                        <a
                          href={f.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-400 hover:underline truncate max-w-xs"
                        >
                          {f.source_title || f.source_url}
                        </a>
                        <span>Confidence: {(f.confidence * 100).toFixed(0)}%</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Suggestions */}
              {result.evaluation.suggestions.length > 0 && (
                <div className="bg-[#141414] rounded-lg border border-[#333] p-4">
                  <h3 className="text-sm font-semibold text-gray-300 mb-2">
                    Improvement Suggestions
                  </h3>
                  <ul className="list-disc list-inside text-sm text-gray-400 space-y-1">
                    {result.evaluation.suggestions.map((s, i) => (
                      <li key={i}>{s}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </>
      )}

      {/* Empty state */}
      {status === "idle" && !result && (
        <div className="text-center py-20 text-gray-600">
          <div className="text-4xl mb-4">&#x1F50D;</div>
          <p className="text-lg">Enter a research topic to generate a well-researched article</p>
          <p className="text-sm mt-2">
            Multi-agent pipeline: Researcher → Data Analyst → Writer → Critic (with feedback loop)
          </p>
        </div>
      )}
    </main>
  );
}
