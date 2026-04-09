import { API_BASE_URL } from "./constants";
import type { PipelineResult, KBArticle, CompositeStyleGuide } from "./types";

export async function generateArticle(
  prompt: string,
  audience: string = "general",
  tone: string = "informative",
  useKnowledgeBase: boolean = false,
  kbTags: string[] = [],
): Promise<{ status: string; message: string; result: PipelineResult & { id: string } }> {
  const res = await fetch(`${API_BASE_URL}/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      prompt,
      audience,
      tone,
      use_knowledge_base: useKnowledgeBase,
      kb_tags: kbTags,
    }),
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

// ── Knowledge Base API ────────────────────────────────────────────────────

export async function kbUploadArticle(
  file: File,
  title: string = "",
  tags: string = "",
): Promise<{ status: string; article: KBArticle }> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("title", title);
  formData.append("tags", tags);

  const res = await fetch(`${API_BASE_URL}/kb/upload`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
  return res.json();
}

export async function kbListArticles(
  tags?: string,
): Promise<{ articles: KBArticle[] }> {
  const url = tags
    ? `${API_BASE_URL}/kb/articles?tags=${encodeURIComponent(tags)}`
    : `${API_BASE_URL}/kb/articles`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to list KB articles: ${res.status}`);
  return res.json();
}

export async function kbGetArticle(
  id: string,
): Promise<{ article: KBArticle }> {
  const res = await fetch(`${API_BASE_URL}/kb/articles/${id}`);
  if (!res.ok) throw new Error(`Failed to get KB article: ${res.status}`);
  return res.json();
}

export async function kbDeleteArticle(id: string): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/kb/articles/${id}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error(`Failed to delete KB article: ${res.status}`);
}

export async function kbUpdateTags(
  id: string,
  tags: string[],
): Promise<{ article: KBArticle }> {
  const res = await fetch(`${API_BASE_URL}/kb/articles/${id}/tags`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(tags),
  });
  if (!res.ok) throw new Error(`Failed to update tags: ${res.status}`);
  return res.json();
}

export async function kbGetStyleGuide(
  tags?: string,
): Promise<{ guide: CompositeStyleGuide }> {
  const url = tags
    ? `${API_BASE_URL}/kb/style-guide?tags=${encodeURIComponent(tags)}`
    : `${API_BASE_URL}/kb/style-guide`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to get style guide: ${res.status}`);
  return res.json();
}
