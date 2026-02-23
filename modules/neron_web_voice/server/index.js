import express from 'express';
import { createServer as createHttpServer } from 'node:http';
import { createServer as createHttpsServer } from 'node:https';
import { readFileSync, existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const app = express();
const PORT = parseInt(process.env.PORT || '8080', 10);

let CORE_URL = process.env.NERON_CORE_URL || 'http://localhost:8000';
let STT_URL  = process.env.NERON_STT_URL  || 'http://localhost:8001';

app.use((req, res, next) => {
  const start = Date.now();
  res.on('finish', () => {
    if (!req.path.startsWith('/api')) return;
    console.log(`${req.method} ${req.path} ${res.statusCode} - ${Date.now() - start}ms`);
  });
  next();
});

app.get('/api/health', (_req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

app.get('/api/config', (_req, res) => {
  res.json({ coreUrl: CORE_URL, sttUrl: STT_URL });
});

app.post('/api/config', express.json(), (req, res) => {
  const { coreUrl, sttUrl } = req.body;
  if (coreUrl) CORE_URL = coreUrl.replace(/\/$/, '');
  if (sttUrl)  STT_URL  = sttUrl.replace(/\/$/, '');
  console.log(`Config updated - Core: ${CORE_URL} | STT: ${STT_URL}`);
  res.json({ coreUrl: CORE_URL, sttUrl: STT_URL });
});

app.post('/api/stt', async (req, res) => {
  try {
    const chunks = [];
    req.on('data', chunk => chunks.push(chunk));
    req.on('end', async () => {
      const body = Buffer.concat(chunks);
      const contentType = req.headers['content-type'] || '';
      console.log(`STT proxy -> ${STT_URL}/transcribe (${body.length} bytes, ${contentType})`);
      const response = await fetch(`${STT_URL}/transcribe`, {
        method: 'POST',
        headers: {
          'content-type': contentType,
          'content-length': String(body.length),
        },
        body,
      });
      const data = await response.json();
      if (!response.ok) return res.status(response.status).json(data);
      res.json(data);
    });
  } catch (e) {
    console.error('STT proxy error:', e);
    res.status(502).json({ error: e.message });
  }
});

app.post('/api/core', express.json(), async (req, res) => {
  try {
    const response = await fetch(`${CORE_URL}/input/text`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req.body),
    });
    if (!response.ok) {
      const text = await response.text();
      return res.status(response.status).json({ error: text });
    }
    res.json(await response.json());
  } catch (e) {
    console.error('Core proxy error:', e);
    res.status(502).json({ error: `Core inaccessible : ${e.message}` });
  }
});

const publicDir = path.resolve(__dirname, '../public');
app.use(express.static(publicDir));

app.get('/{*path}', (_req, res) => {
  res.sendFile(path.join(publicDir, 'index.html'));
});

app.use((err, _req, res, _next) => {
  console.error('Server error:', err);
  res.status(err.status || 500).json({ error: err.message || 'Internal Server Error' });
});

const certPath = path.resolve(__dirname, '../cert.pem');
const keyPath  = path.resolve(__dirname, '../key.pem');

if (existsSync(certPath) && existsSync(keyPath)) {
  const server = createHttpsServer({ cert: readFileSync(certPath), key: readFileSync(keyPath) }, app);
  server.listen({ port: PORT, host: '0.0.0.0' }, () => {
    console.log(`Neron (HTTPS) -> https://localhost:${PORT}`);
    console.log(`Reseau local  -> https://100.77.245.31:${PORT}`);
    console.log(`Core: ${CORE_URL} | STT: ${STT_URL}`);
  });
} else {
  const server = createHttpServer(app);
  server.listen({ port: PORT, host: '0.0.0.0' }, () => {
    console.log(`Neron (HTTP) -> http://localhost:${PORT}`);
  });
}
