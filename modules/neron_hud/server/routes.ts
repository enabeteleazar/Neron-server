import type { Express } from "express";
import type { Server } from "http";

const CORE_URL     = process.env.NERON_CORE_URL     || "http://neron_core:8000";
const STT_URL      = process.env.NERON_STT_URL      || "http://neron_stt:8001";
const WATCHDOG_URL = process.env.NERON_WATCHDOG_URL || "http://neron_watchdog:8003";
const API_KEY      = process.env.NERON_API_KEY       || "";

const chatHistory: { id: number; role: string; content: string; createdAt: string }[] = [];
let msgId = 1;

export async function registerRoutes(httpServer: Server, app: Express): Promise<Server> {

  app.post("/api/chat", async (req, res) => {
    try {
      const { message } = req.body;
      if (!message) return res.status(400).json({ message: "Message requis" });

      chatHistory.push({ id: msgId++, role: "user", content: message, createdAt: new Date().toISOString() });

      const response = await fetch(`${CORE_URL}/input/text`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-API-Key": API_KEY },
        body: JSON.stringify({ text: message }),
      });

      if (!response.ok) throw new Error(`Core ${response.status}`);
      const data = await response.json();
      const reply = data.response || "...";

      chatHistory.push({ id: msgId++, role: "assistant", content: reply, createdAt: new Date().toISOString() });
      res.json({ message: reply });
    } catch (err: any) {
      console.error("Chat error:", err.message);
      res.status(500).json({ message: `Neron Core inaccessible : ${err.message}` });
    }
  });

  app.get("/api/chat/history", (_req, res) => {
    res.json(chatHistory.slice(-50));
  });

  app.post("/api/stt", async (req, res) => {
    try {
      const chunks: Buffer[] = [];
      req.on("data", (c: Buffer) => chunks.push(c));
      req.on("end", async () => {
        const body = Buffer.concat(chunks);
        const ct = req.headers["content-type"] || "";
        const r = await fetch(`${STT_URL}/transcribe`, {
          method: "POST",
          headers: { "content-type": ct, "content-length": String(body.length) },
          body,
        });
        res.status(r.status).json(await r.json());
      });
    } catch (err: any) {
      res.status(502).json({ error: err.message });
    }
  });

  app.get("/api/system/metrics", async (_req, res) => {
    try {
      const [scoreRes, statusRes] = await Promise.all([
        fetch(`${WATCHDOG_URL}/score`),
        fetch(`${WATCHDOG_URL}/status`),
      ]);
      const scoreData  = scoreRes.ok  ? await scoreRes.json()  : {};
      const statusData = statusRes.ok ? await statusRes.json() : {};

      // services est un objet { "Neron Core": { healthy, response_time, error }, ... }
      const rawServices = statusData.services || {};
      const services = Object.entries(rawServices).map(([name, info]: [string, any]) => ({
        name,
        status: info.healthy ? "up" : "down",
        latency_ms: info.response_time ? Math.round(info.response_time * 1000) : null,
        error: info.error || null,
      }));

      const up = services.filter(s => s.status === "up").length;
      res.json({
        score:      scoreData.score      ?? Math.round((up / Math.max(services.length, 1)) * 100),
        status:     scoreData.status     ?? (up === services.length ? "healthy" : "degraded"),
        up_count:   up,
        down_count: services.length - up,
        services,
      });
    } catch (err: any) {
      res.status(502).json({ error: err.message });
    }
  });

  app.get("/api/system/anomalies", async (_req, res) => {
    try {
      const r = await fetch(`${WATCHDOG_URL}/anomalies`);
      res.json(r.ok ? await r.json() : { anomalies: [] });
    } catch { res.json({ anomalies: [] }); }
  });

  app.get("/api/system/logs/:service", async (req, res) => {
    try {
      const lines = req.query.lines || 30;
      const r = await fetch(`${WATCHDOG_URL}/logs/${req.params.service}?lines=${lines}`);
      res.json(r.ok ? await r.json() : { logs: [] });
    } catch { res.json({ logs: [] }); }
  });

  return httpServer;
}
