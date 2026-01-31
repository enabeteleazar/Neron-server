import type { Express } from "express";
import { createServer, type Server } from "http";
import { storage } from "./storage";
import { api } from "@shared/routes";
import { z } from "zod";

const OLLAMA_BASE_URL = process.env.OLLAMA_BASE_URL || "http://localhost:11434";

export async function registerRoutes(
  httpServer: Server,
  app: Express
): Promise<Server> {
  
  // --- Chat API (using Ollama) ---
  app.post(api.chat.send.path, async (req, res) => {
    try {
      const { message } = api.chat.send.input.parse(req.body);

      // Save user message
      await storage.createMessage({
        role: "user",
        content: message,
      });

      // Get history for context (last 10 messages)
      const history = await storage.getMessages();
      const recentHistory = history.slice(-10).map(msg => ({
        role: msg.role as "user" | "assistant",
        content: msg.content
      }));

      // Call Ollama API
      const ollamaResponse = await fetch(`${OLLAMA_BASE_URL}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: "llama3.2",
          messages: [
            { 
              role: "system", 
              content: "You are JARVIS, a highly advanced virtual assistant. You are helpful, precise, and speak in a technical but polite manner. Keep responses concise and suitable for a HUD interface." 
            },
            ...recentHistory,
            { role: "user", content: message }
          ],
          stream: false
        }),
      });

      if (!ollamaResponse.ok) {
        throw new Error(`Ollama error: ${ollamaResponse.status}`);
      }

      const ollamaData = await ollamaResponse.json();
      const assistantMessage = ollamaData.message?.content || "I am unable to process that request.";

      // Save assistant message
      await storage.createMessage({
        role: "assistant",
        content: assistantMessage,
      });

      res.json({ message: assistantMessage });

    } catch (err) {
      console.error("Chat Error:", err);
      res.status(500).json({ message: "Failed to process chat request. Make sure Ollama is running." });
    }
  });

  app.get(api.chat.history.path, async (req, res) => {
    const messages = await storage.getMessages();
    res.json(messages);
  });

  // --- System Metrics API (Mock) ---
  app.get(api.system.metrics.path, async (req, res) => {
    const metrics = {
      cpu: Math.floor(Math.random() * 30) + 10,
      memory: Math.floor(Math.random() * 40) + 20,
      temperature: Math.floor(Math.random() * 15) + 45,
      networkUp: Math.floor(Math.random() * 500) + 100,
      networkDown: Math.floor(Math.random() * 2000) + 500,
      tasks: Math.floor(Math.random() * 5) + 40,
    };
    res.json(metrics);
  });

  return httpServer;
}
