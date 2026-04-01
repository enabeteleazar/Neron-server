# Neron API Endpoints Summary

## ✅ Available Endpoints

### 1. **GET /** - Root/Info
```
GET http://localhost:8010/
```
Returns:
```json
{
  "message": "Neron AI API",
  "version": "2.1.0"
}
```

---

### 2. **GET /status** - System Status
```
GET http://localhost:8010/status
```
Returns:
```json
{
  "status": "online",
  "service": "neron_api",
  "version": "2.1.0",
  "llm_ready": true,
  "model": "minimax-m2.7:cloud"
}
```

---

### 3. **POST /chat** - Chat Endpoint
```
POST http://localhost:8010/chat
Content-Type: application/json

{
  "message": "Hello, how are you?",
  "context": "optional"
}
```

Response:
```json
{
  "response": "Hi! I'm Neron, an AI assistant...",
  "success": true
}
```

---

### 4. **POST /input/text** - Text Input (Non-Streaming)
```
POST http://localhost:8010/input/text
Content-Type: application/json

{
  "text": "What's your name?",
  "mode": "default",
  "context": "optional"
}
```

**Modes:**
- `default` - Direct LLM response
- `plan` - Step-by-step plan
- `autopilot` - Extended autonomous mode
- `pipeline` - Intent routing + LLM

Response:
```json
{
  "response": "I'm Neron...",
  "success": true,
  "mode": "default",
  "intent": null,
  "confidence": null,
  "context": "optional"
}
```

---

### 5. **POST /input/stream** - Text Input (Streaming) ⭐ NEW
```
POST http://localhost:8010/input/stream
Content-Type: application/json

{
  "text": "Tell me a story",
  "mode": "default",
  "context": "optional"
}
```

Returns NDJSON stream:
```
{"type": "metadata", "intent": "assistant", "confidence": 0.95}
{"type": "chunk", "data": "Once upon "}
{"type": "chunk", "data": "a time..."}
{"type": "complete", "success": true}
```

**Stream Response Types:**
| Type | Fields | Description |
|------|--------|-------------|
| `metadata` | intent, confidence | Routing metadata (pipeline mode) |
| `chunk` | data | Response fragment |
| `complete` | success | End of stream |
| `error` | message | Error message |

---

## 🔑 Authentication

Optional header for all endpoints:
```
X-API-Key: your-api-key
```

If `NERON_API_KEY` is set in config, API key validation is enforced.

---

## 📊 Testing

```bash
# Test all endpoints
python3 test_endpoints.py

# Test streaming specifically
python3 test_stream.py
```

---

## 🚀 Usage Examples

### Python (Async)
```python
import httpx
import json

async with httpx.AsyncClient() as client:
    # Non-streaming
    resp = await client.post(
        "http://localhost:8010/input/text",
        json={"text": "Hello", "mode": "default"}
    )
    data = resp.json()
    print(data["response"])
    
    # Streaming
    async with client.stream(
        "POST",
        "http://localhost:8010/input/stream",
        json={"text": "Tell me a story"}
    ) as resp:
        async for line in resp.aiter_lines():
            data = json.loads(line)
            if data["type"] == "chunk":
                print(data["data"], end="", flush=True)
```

### JavaScript/Node.js
```javascript
// Non-streaming
const response = await fetch('http://localhost:8010/input/text', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ text: 'Hi', mode: 'default' })
});
const data = await response.json();
console.log(data.response);

// Streaming
const response = await fetch('http://localhost:8010/input/stream', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ text: 'Tell me a story' })
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  
  const lines = decoder.decode(value).split('\n');
  for (const line of lines) {
    if (line.trim()) {
      const data = JSON.parse(line);
      if (data.type === 'chunk') {
        process.stdout.write(data.data);
      }
    }
  }
}
```

### cURL
```bash
# Non-streaming
curl -X POST http://localhost:8010/input/text \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello", "mode": "default"}'

# Streaming (shows progress)
curl -X POST http://localhost:8010/input/stream \
  -H "Content-Type: application/json" \
  -d '{"text": "Tell me a story"}'
```

---

## 🔗 Server Configuration

Default settings:
- Host: `0.0.0.0`
- Port: `8010`
- LLM Model: `minimax-m2.7:cloud`
- Ollama Host: `http://localhost:11434`

Configure via environment:
```bash
export SERVER_HOST="localhost"
export NERON_CORE_HTTP=8010
export OLLAMA_MODEL="llama2"
```

Or via `neron.yaml`:
```yaml
server:
  host: 0.0.0.0
  port: 8010

llm:
  model: minimax-m2.7:cloud
  host: http://localhost:11434
```

---

## 📝 Response Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad request |
| 403 | Invalid API key |
| 500 | Server error |

---

## 🐛 Troubleshooting

**Port 8010 already in use:**
```bash
bash start_neron.sh  # Uses safe cleanup
```

**LLM not responding:**
Check `GET /status` - `llm_ready` must be true

**Streaming client connection dropped:**
Ensure client can handle NDJSON format with newline delimiters

---

Last updated: 2026-04-01
