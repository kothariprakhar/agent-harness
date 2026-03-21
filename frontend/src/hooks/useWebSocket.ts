"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { io, Socket } from "socket.io-client";
import type { PipelineEvent } from "@/lib/types";

export function useWebSocket(url: string = "http://localhost:8000") {
  const socketRef = useRef<Socket | null>(null);
  const [connected, setConnected] = useState(false);
  const [events, setEvents] = useState<PipelineEvent[]>([]);

  useEffect(() => {
    const socket = io(url, { transports: ["websocket", "polling"] });
    socketRef.current = socket;

    socket.on("connect", () => setConnected(true));
    socket.on("disconnect", () => setConnected(false));

    socket.on("pipeline_event", (event: PipelineEvent) => {
      setEvents((prev) => [...prev, event]);
    });

    return () => {
      socket.disconnect();
    };
  }, [url]);

  const clearEvents = useCallback(() => setEvents([]), []);

  return { connected, events, clearEvents };
}
