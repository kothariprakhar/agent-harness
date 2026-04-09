"use client";

import { useState, useEffect, useCallback } from "react";
import { kbListArticles, kbUploadArticle, kbDeleteArticle } from "@/lib/api";
import type { KBArticle } from "@/lib/types";
import StyleProfileViewer from "./StyleProfileViewer";

interface Props {
  onKBStateChange?: (hasArticles: boolean, tags: string[]) => void;
}

export default function KnowledgeBasePanel({ onKBStateChange }: Props) {
  const [expanded, setExpanded] = useState(false);
  const [articles, setArticles] = useState<KBArticle[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [selectedArticle, setSelectedArticle] = useState<KBArticle | null>(null);
  const [tagInput, setTagInput] = useState("");
  const [titleInput, setTitleInput] = useState("");
  const [dragOver, setDragOver] = useState(false);

  const loadArticles = useCallback(async () => {
    try {
      const { articles: list } = await kbListArticles();
      setArticles(list);
      const allTags = Array.from(new Set(list.flatMap((a) => a.tags)));
      onKBStateChange?.(list.length > 0, allTags);
    } catch {
      // Gateway may not be running yet
    }
  }, [onKBStateChange]);

  useEffect(() => {
    if (expanded) loadArticles();
  }, [expanded, loadArticles]);

  const handleUpload = async (file: File) => {
    setUploading(true);
    setUploadError(null);
    try {
      await kbUploadArticle(file, titleInput, tagInput);
      setTitleInput("");
      setTagInput("");
      await loadArticles();
    } catch (err: any) {
      setUploadError(err.message);
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await kbDeleteArticle(id);
      if (selectedArticle?.id === id) setSelectedArticle(null);
      await loadArticles();
    } catch {
      // ignore
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleUpload(file);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleUpload(file);
    e.target.value = "";
  };

  return (
    <div className="bg-[#141414] rounded-lg border border-[#333] overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-[#1a1a1a] transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-gray-300">
            Knowledge Base
          </span>
          {articles.length > 0 && (
            <span className="text-xs px-1.5 py-0.5 bg-blue-900/50 text-blue-400 rounded-full">
              {articles.length}
            </span>
          )}
        </div>
        <span className="text-gray-500 text-xs">
          {expanded ? "▲" : "▼"}
        </span>
      </button>

      {expanded && (
        <div className="px-4 pb-4 space-y-3 border-t border-[#333]">
          {/* Upload area */}
          <div
            className={`mt-3 border-2 border-dashed rounded-lg p-4 text-center transition-colors ${
              dragOver
                ? "border-blue-500 bg-blue-900/20"
                : "border-[#444] hover:border-[#555]"
            }`}
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
          >
            <div className="space-y-2">
              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="Title (optional)"
                  value={titleInput}
                  onChange={(e) => setTitleInput(e.target.value)}
                  className="flex-1 px-2 py-1 bg-[#1e1e1e] border border-[#333] rounded text-xs text-white"
                />
                <input
                  type="text"
                  placeholder="Tags (comma-separated)"
                  value={tagInput}
                  onChange={(e) => setTagInput(e.target.value)}
                  className="flex-1 px-2 py-1 bg-[#1e1e1e] border border-[#333] rounded text-xs text-white"
                />
              </div>
              <label className="cursor-pointer">
                <span className="text-xs text-gray-400">
                  {uploading
                    ? "Uploading & analyzing..."
                    : "Drop a file here or click to upload (MD, TXT, HTML, PDF, DOCX)"}
                </span>
                <input
                  type="file"
                  className="hidden"
                  accept=".md,.txt,.html,.htm,.pdf,.docx"
                  onChange={handleFileSelect}
                  disabled={uploading}
                />
              </label>
            </div>
          </div>

          {uploadError && (
            <div className="text-xs text-red-400">{uploadError}</div>
          )}

          {/* Article list */}
          {articles.length > 0 && (
            <div className="space-y-1">
              <div className="text-xs text-gray-500 font-medium">
                Reference Articles
              </div>
              {articles.map((a) => (
                <div
                  key={a.id}
                  className={`flex items-center justify-between p-2 rounded text-xs transition-colors cursor-pointer ${
                    selectedArticle?.id === a.id
                      ? "bg-blue-900/30 border border-blue-800"
                      : "bg-[#1e1e1e] hover:bg-[#252525]"
                  }`}
                  onClick={() =>
                    setSelectedArticle(
                      selectedArticle?.id === a.id ? null : a
                    )
                  }
                >
                  <div className="flex-1 min-w-0">
                    <div className="text-gray-300 truncate">{a.title}</div>
                    <div className="flex gap-1 mt-0.5">
                      <span className="text-gray-600">
                        {a.word_count} words
                      </span>
                      <span className="text-gray-700">|</span>
                      <span className="text-gray-600 uppercase">
                        {a.format}
                      </span>
                      {a.tags.map((t) => (
                        <span
                          key={t}
                          className="px-1 bg-[#333] text-gray-400 rounded"
                        >
                          {t}
                        </span>
                      ))}
                    </div>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDelete(a.id);
                    }}
                    className="ml-2 text-gray-600 hover:text-red-400 transition-colors"
                    title="Delete"
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Style profile viewer */}
          {selectedArticle?.style_profile && (
            <StyleProfileViewer profile={selectedArticle.style_profile} />
          )}
        </div>
      )}
    </div>
  );
}
