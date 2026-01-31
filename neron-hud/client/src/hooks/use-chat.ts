import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, type ChatResponse, type MetricsResponse } from "@shared/routes";

// ============================================
// CHAT HOOKS
// ============================================

export function useChatHistory() {
  return useQuery({
    queryKey: [api.chat.history.path],
    queryFn: async () => {
      const res = await fetch(api.chat.history.path);
      if (!res.ok) throw new Error("Failed to fetch history");
      return api.chat.history.responses[200].parse(await res.json());
    },
  });
}

export function useSendMessage() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (message: string) => {
      const res = await fetch(api.chat.send.path, {
        method: api.chat.send.method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message }),
      });
      if (!res.ok) throw new Error("Failed to send message");
      return api.chat.send.responses[200].parse(await res.json());
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [api.chat.history.path] });
    },
  });
}

// ============================================
// SYSTEM METRICS HOOKS
// ============================================

export function useSystemMetrics() {
  return useQuery({
    queryKey: [api.system.metrics.path],
    queryFn: async () => {
      const res = await fetch(api.system.metrics.path);
      if (!res.ok) throw new Error("Failed to fetch metrics");
      return api.system.metrics.responses[200].parse(await res.json());
    },
    refetchInterval: 2000, // Poll every 2 seconds
  });
}
