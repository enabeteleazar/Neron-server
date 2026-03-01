import { useState, useEffect, useCallback } from "react";

export interface ChatMessage {
  id: number;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
}

export interface ServiceStatus {
  name: string;
  status: "up" | "down" | "unknown";
  latency_ms?: number;
}

export interface NeronMetrics {
  score: number;
  services: ServiceStatus[];
  timestamp: string;
}

export interface Anomaly {
  id: string;
  service: string;
  message: string;
  severity: "low" | "medium" | "high";
  timestamp: string;
}

async function apiFetch(url: string, options?: RequestInit) {
  const res = await fetch(url, options);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export function useChatHistory() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const data = await apiFetch("/api/chat/history");
      setMessages(Array.isArray(data) ? data : []);
    } catch {}
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  return { messages, loading, refresh };
}

export function useSendMessage(onSuccess: () => void) {
  const [pending, setPending] = useState(false);

  const send = useCallback(async (text: string) => {
    setPending(true);
    try {
      await apiFetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });
      onSuccess();
    } catch {}
    setPending(false);
  }, [onSuccess]);

  return { send, pending };
}

export function useSystemMetrics() {
  const [metrics, setMetrics] = useState<NeronMetrics>({ score: 0, services: [], timestamp: "" });

  useEffect(() => {
    const fetch_ = async () => {
      try {
        const data = await apiFetch("/api/system/metrics");
        setMetrics(data);
      } catch {}
    };
    fetch_();
    const id = setInterval(fetch_, 10000);
    return () => clearInterval(id);
  }, []);

  return metrics;
}

export function useAnomalies() {
  const [anomalies, setAnomalies] = useState<Anomaly[]>([]);

  useEffect(() => {
    const fetch_ = async () => {
      try {
        const data = await apiFetch("/api/system/anomalies");
        setAnomalies(Array.isArray(data) ? data : []);
      } catch {}
    };
    fetch_();
    const id = setInterval(fetch_, 15000);
    return () => clearInterval(id);
  }, []);

  return anomalies;
}
