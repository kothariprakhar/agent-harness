"use client";

import { useRef, useState } from "react";
import type { ConceptArtifact } from "@/lib/types";

interface Props {
  artifact: ConceptArtifact;
}

export default function ArtifactEmbed({ artifact }: Props) {
  const [expanded, setExpanded] = useState(false);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  return (
    <div className="my-6 bg-[#141414] rounded-lg border border-[#333] overflow-hidden">
      <div className="px-4 py-2 border-b border-[#333] flex items-center justify-between">
        <div>
          <h4 className="text-sm font-medium text-gray-300">{artifact.title}</h4>
          <p className="text-xs text-gray-500">{artifact.interactivity_description}</p>
        </div>
        <div className="flex gap-2">
          <span className="text-xs px-2 py-0.5 bg-purple-900/30 text-purple-400 rounded">
            Interactive
          </span>
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-xs text-gray-500 hover:text-gray-300"
          >
            {expanded ? "Collapse" : "Expand"}
          </button>
        </div>
      </div>
      <div className="artifact-frame">
        <iframe
          ref={iframeRef}
          srcDoc={artifact.html_content}
          sandbox="allow-scripts"
          className="w-full border-0"
          style={{ height: expanded ? "600px" : "400px" }}
          title={artifact.title}
        />
      </div>
    </div>
  );
}
