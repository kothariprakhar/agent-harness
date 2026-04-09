"use client";

import { useState } from "react";

interface Props {
  onSubmit: (
    prompt: string,
    audience: string,
    tone: string,
    useKnowledgeBase: boolean,
    kbTags: string[],
  ) => void;
  disabled?: boolean;
  kbAvailable?: boolean;
  availableTags?: string[];
}

export default function PromptInput({
  onSubmit,
  disabled,
  kbAvailable = false,
  availableTags = [],
}: Props) {
  const [prompt, setPrompt] = useState("");
  const [audience, setAudience] = useState("general");
  const [tone, setTone] = useState("informative");
  const [useKB, setUseKB] = useState(false);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (prompt.trim() && !disabled) {
      onSubmit(prompt.trim(), audience, tone, useKB, selectedTags);
    }
  };

  const toggleTag = (tag: string) => {
    setSelectedTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
    );
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Enter your research topic... e.g., 'Write a deep dive on how transformer attention mechanisms actually work, aimed at CS undergraduates'"
          className="w-full h-28 px-4 py-3 bg-[#1e1e1e] border border-[#333] rounded-lg text-white placeholder-gray-500 resize-none focus:outline-none focus:border-blue-500 transition-colors"
          disabled={disabled}
        />
      </div>
      <div className="flex gap-4 items-end">
        <div className="flex-1">
          <label className="block text-sm text-gray-400 mb-1">Audience</label>
          <input
            type="text"
            value={audience}
            onChange={(e) => setAudience(e.target.value)}
            className="w-full px-3 py-2 bg-[#1e1e1e] border border-[#333] rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
            disabled={disabled}
          />
        </div>
        <div className="flex-1">
          <label className="block text-sm text-gray-400 mb-1">Tone</label>
          <select
            value={tone}
            onChange={(e) => setTone(e.target.value)}
            className="w-full px-3 py-2 bg-[#1e1e1e] border border-[#333] rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
            disabled={disabled}
          >
            <option value="informative">Informative</option>
            <option value="conversational">Conversational</option>
            <option value="academic">Academic</option>
            <option value="technical">Technical</option>
          </select>
        </div>
        <button
          type="submit"
          disabled={disabled || !prompt.trim()}
          className="px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors"
        >
          {disabled ? "Generating..." : "Generate Article"}
        </button>
      </div>

      {/* Knowledge Base toggle */}
      {kbAvailable && (
        <div className="flex items-center gap-3 flex-wrap">
          <label className="flex items-center gap-2 text-sm text-gray-400 cursor-pointer">
            <input
              type="checkbox"
              checked={useKB}
              onChange={(e) => setUseKB(e.target.checked)}
              className="rounded border-gray-600 bg-[#1e1e1e]"
              disabled={disabled}
            />
            Use Knowledge Base style
          </label>
          {useKB && availableTags.length > 0 && (
            <div className="flex gap-1 flex-wrap">
              {availableTags.map((tag) => (
                <button
                  key={tag}
                  type="button"
                  onClick={() => toggleTag(tag)}
                  className={`px-2 py-0.5 text-xs rounded-full transition-colors ${
                    selectedTags.includes(tag)
                      ? "bg-blue-600 text-white"
                      : "bg-[#333] text-gray-400 hover:bg-[#444]"
                  }`}
                >
                  {tag}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </form>
  );
}
