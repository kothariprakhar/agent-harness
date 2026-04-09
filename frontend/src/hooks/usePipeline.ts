"use client";

import { useState, useCallback } from "react";
import { generateArticle } from "@/lib/api";
import type { PipelineResult } from "@/lib/types";

export type PipelineStatus = "idle" | "running" | "completed" | "error";

export function usePipeline() {
  const [status, setStatus] = useState<PipelineStatus>("idle");
  const [result, setResult] = useState<PipelineResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(
    async (
      prompt: string,
      audience: string,
      tone: string,
      useKnowledgeBase: boolean = false,
      kbTags: string[] = [],
    ) => {
      setStatus("running");
      setError(null);
      setResult(null);

      try {
        const response = await generateArticle(prompt, audience, tone, useKnowledgeBase, kbTags);
        setResult(response.result);
        setStatus("completed");
      } catch (err: any) {
        setError(err.message || "Pipeline failed");
        setStatus("error");
      }
    },
    []
  );

  const reset = useCallback(() => {
    setStatus("idle");
    setResult(null);
    setError(null);
  }, []);

  return { status, result, error, run, reset };
}
