"use client";

import type { StyleProfile } from "@/lib/types";

interface Props {
  profile: StyleProfile;
}

export default function StyleProfileViewer({ profile }: Props) {
  return (
    <div className="bg-[#1a1a1a] rounded-lg border border-[#333] p-3 space-y-2">
      <h4 className="text-xs font-semibold text-gray-300">Style Profile</h4>

      <div className="grid grid-cols-2 gap-2 text-xs">
        <div>
          <span className="text-gray-500">Tone:</span>{" "}
          <span className="text-gray-300">
            {profile.tone_descriptors.join(", ") || "—"}
          </span>
        </div>
        <div>
          <span className="text-gray-500">Vocabulary:</span>{" "}
          <span className="text-gray-300">
            {profile.vocabulary_level || "—"}
          </span>
        </div>
        <div>
          <span className="text-gray-500">Avg Sentence:</span>{" "}
          <span className="text-gray-300">
            {profile.avg_sentence_length.toFixed(0)} words
          </span>
        </div>
        <div>
          <span className="text-gray-500">Sections:</span>{" "}
          <span className="text-gray-300">{profile.avg_section_count}</span>
        </div>
      </div>

      {profile.sentence_style && (
        <div className="text-xs">
          <span className="text-gray-500">Sentence Style:</span>{" "}
          <span className="text-gray-400">{profile.sentence_style}</span>
        </div>
      )}

      {profile.structural_template.length > 0 && (
        <div className="text-xs">
          <span className="text-gray-500">Structure:</span>{" "}
          <span className="text-gray-400">
            {profile.structural_template.join(" → ")}
          </span>
        </div>
      )}

      {profile.formatting_patterns.length > 0 && (
        <div className="text-xs">
          <span className="text-gray-500">Formatting:</span>{" "}
          <span className="text-gray-400">
            {profile.formatting_patterns.join("; ")}
          </span>
        </div>
      )}

      {profile.exemplary_passages.length > 0 && (
        <details className="text-xs">
          <summary className="text-gray-500 cursor-pointer hover:text-gray-300">
            {profile.exemplary_passages.length} exemplary passage(s)
          </summary>
          <div className="mt-1 space-y-1">
            {profile.exemplary_passages.map((p, i) => (
              <blockquote
                key={i}
                className="pl-2 border-l-2 border-[#444] text-gray-400 italic"
              >
                {p.length > 200 ? p.slice(0, 200) + "..." : p}
              </blockquote>
            ))}
          </div>
        </details>
      )}
    </div>
  );
}
