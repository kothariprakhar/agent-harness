import { API_BASE_URL } from "./constants";
import type { PipelineResult } from "./types";

export async function generateArticle(
  prompt: string,
  audience: string = "general",
  tone: string = "informative"
): Promise<{ status: string; message: string; result: PipelineResult & { id: string } }> {
  const res = await fetch(`${API_BASE_URL}/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt, audience, tone }),
  });

  if (!res.ok) {
    const error = await res.text();
    throw new Error(`API error: ${res.status} - ${error}`);
  }

  return res.json();
}

export async function getResult(resultId: string): Promise<PipelineResult> {
  const res = await fetch(`${API_BASE_URL}/results/${resultId}`);
  if (!res.ok) throw new Error(`Failed to fetch result: ${res.status}`);
  return res.json();
}
