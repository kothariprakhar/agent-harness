"use client";

import { useRef, useEffect } from "react";
import { AGENT_COLORS } from "@/lib/constants";
import type { PipelineEvent } from "@/lib/types";

interface Props {
  events: PipelineEvent[];
}

export default function MessageStream({ events }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events]);

  if (events.length === 0) {
    return (
      <div className="h-[300px] bg-[#141414] rounded-lg border border-[#333] flex items-center justify-center text-gray-500">
        Pipeline messages will appear here...
      </div>
    );
  }

  return (
    <div
      ref={scrollRef}
      className="h-[300px] bg-[#141414] rounded-lg border border-[#333] overflow-y-auto p-3 space-y-2"
    >
      {events.map((event, i) => {
        const agent = event.data?.agent_name || "system";
        const color = AGENT_COLORS[agent] || "#666";
        const message = event.data?.message || event.type;

        return (
          <div key={i} className="flex items-start gap-2 text-sm">
            <span
              className="inline-block w-2 h-2 rounded-full mt-1.5 flex-shrink-0"
              style={{ backgroundColor: color }}
            />
            <span className="font-medium text-gray-400" style={{ color }}>
              {agent}
            </span>
            <span className="text-gray-300">{message}</span>
          </div>
        );
      })}
    </div>
  );
}
