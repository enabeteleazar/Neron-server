import { z } from 'zod';
import { insertMessageSchema, messages } from './schema';

export const errorSchemas = {
  validation: z.object({
    message: z.string(),
    field: z.string().optional(),
  }),
  notFound: z.object({
    message: z.string(),
  }),
  internal: z.object({
    message: z.string(),
  }),
};

export const api = {
  chat: {
    send: {
      method: 'POST' as const,
      path: '/api/chat',
      input: z.object({
        message: z.string(),
      }),
      responses: {
        200: z.object({
          message: z.string(), // The assistant's response
        }),
        500: errorSchemas.internal,
      },
    },
    history: {
      method: 'GET' as const,
      path: '/api/chat/history',
      responses: {
        200: z.array(z.custom<typeof messages.$inferSelect>()),
      },
    },
  },
  system: {
    metrics: {
      method: 'GET' as const,
      path: '/api/system/metrics',
      responses: {
        200: z.object({
          cpu: z.number(),
          memory: z.number(),
          temperature: z.number(),
          networkUp: z.number(),
          networkDown: z.number(),
          tasks: z.number(),
        }),
      },
    },
  },
};

export function buildUrl(path: string, params?: Record<string, string | number>): string {
  let url = path;
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (url.includes(`:${key}`)) {
        url = url.replace(`:${key}`, String(value));
      }
    });
  }
  return url;
}

export type ChatResponse = z.infer<typeof api.chat.send.responses[200]>;
export type MetricsResponse = z.infer<typeof api.system.metrics.responses[200]>;
