"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import ChartEmbed from "./ChartEmbed";
import ArtifactEmbed from "./ArtifactEmbed";
import type { ArticleDraft, ChartSpec, ConceptArtifact, Citation } from "@/lib/types";

interface Props {
  article: ArticleDraft;
  charts: ChartSpec[];
  artifacts: ConceptArtifact[];
}

export default function ArticleRenderer({ article, charts, artifacts }: Props) {
  // Split markdown by chart/artifact placeholders and render them inline
  const chartMap = Object.fromEntries(charts.map((c) => [c.chart_id, c]));
  const artifactMap = Object.fromEntries(artifacts.map((a) => [a.artifact_id, a]));

  // Split on {{chart:id}} and {{artifact:id}} patterns
  const parts = article.markdown.split(/({{(?:chart|artifact):[^}]+}})/g);

  return (
    <div className="article-content max-w-3xl mx-auto">
      {parts.map((part, i) => {
        // Check for chart placeholder
        const chartMatch = part.match(/{{chart:([^}]+)}}/);
        if (chartMatch) {
          const chart = chartMap[chartMatch[1]];
          if (chart) return <ChartEmbed key={i} chart={chart} />;
          return null;
        }

        // Check for artifact placeholder
        const artifactMatch = part.match(/{{artifact:([^}]+)}}/);
        if (artifactMatch) {
          const artifact = artifactMap[artifactMatch[1]];
          if (artifact) return <ArtifactEmbed key={i} artifact={artifact} />;
          return null;
        }

        // Regular markdown
        if (part.trim()) {
          return (
            <ReactMarkdown key={i} remarkPlugins={[remarkGfm]}>
              {part}
            </ReactMarkdown>
          );
        }
        return null;
      })}

      {/* Sources section */}
      {article.citations.length > 0 && (
        <div className="mt-8 pt-4 border-t border-[#333]">
          <h3 className="text-lg font-semibold mb-3">Sources</h3>
          <ol className="list-decimal list-inside space-y-1 text-sm text-gray-400">
            {article.citations.map((c, i) => (
              <li key={i}>
                <a
                  href={c.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-400 hover:underline"
                >
                  {c.source_title || c.source_url}
                </a>
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}
