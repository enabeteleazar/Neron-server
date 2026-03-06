# tests/test_neron.py - Tests complets Néron v2.0 (natif, sans Docker)

import pytest
import sys
import wave
import struct
import tempfile
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "modules", "neron_core"))

# ━━━ MEMORY ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@pytest.fixture(scope="module")
def memory():
    from agents.memory_agent import MemoryAgent, init_db
    init_db()
    return MemoryAgent()

def test_memory_store(memory):
    entry_id = memory.store("capitale france", "Paris", {"source": "pytest"})
    assert entry_id > 0

def test_memory_retrieve(memory):
    results = memory.retrieve(limit=1)
    assert isinstance(results, list)
    assert len(results) > 0

def test_memory_search(memory):
    results = memory.search("capitale france", limit=1)
    assert len(results) > 0
    assert "capitale france" in results[0]["input"]

def test_memory_retrieve_limit(memory):
    memory.store("test limit 1", "r1", {})
    memory.store("test limit 2", "r2", {})
    results = memory.retrieve(limit=2)
    assert len(results) <= 2

def test_memory_search_no_result(memory):
    results = memory.search("xyzabcdef123456", limit=1)
    assert isinstance(results, list)

# ━━━ LLM ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@pytest.fixture(scope="module")
def llm():
    from agents.llm_agent import LLMAgent
    return LLMAgent()

@pytest.mark.asyncio
async def test_llm_connection(llm):
    ok = await llm.check_connection()
    assert ok, "Ollama inaccessible sur localhost:11434"

@pytest.mark.asyncio
async def test_llm_execute(llm):
    result = await llm.execute("Réponds uniquement par le mot : BONJOUR")
    assert result.success, f"LLM failure: {result.error}"
    assert len(result.content) > 0

@pytest.mark.asyncio
async def test_llm_execute_with_context(llm):
    result = await llm.execute(
        "Quel est le sujet ?",
        context_data="Historique récent:\nUtilisateur: parle de Python\nNéron: Python est un langage."
    )
    assert result.success
    assert len(result.content) > 0

@pytest.mark.asyncio
async def test_llm_metadata(llm):
    result = await llm.execute("Dis OK")
    assert result.success
    assert "model" in result.metadata
    assert "tokens_used" in result.metadata

@pytest.mark.asyncio
async def test_llm_stream(llm):
    tokens = []
    async for token in llm.stream("Dis juste : OK"):
        tokens.append(token)
        if len(tokens) > 20:
            break
    assert len(tokens) > 0

# ━━━ STT ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@pytest.fixture(scope="module")
def stt():
    from agents.stt_agent import STTAgent, load_model
    load_model()
    return STTAgent()

@pytest.fixture
def silent_wav():
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp = f.name
        with wave.open(tmp, 'w') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(struct.pack('<' + 'h' * 16000, *([0] * 16000)))
    with open(tmp, "rb") as f:
        data = f.read()
    os.remove(tmp)
    return data

@pytest.mark.asyncio
async def test_stt_connection(stt):
    ok = await stt.check_connection()
    assert ok, "faster-whisper non chargé"

@pytest.mark.asyncio
async def test_stt_transcribe(stt, silent_wav):
    result = await stt.transcribe(silent_wav, "test.wav")
    assert result.success, f"STT failure: {result.error}"
    assert "language" in result.metadata

@pytest.mark.asyncio
async def test_stt_invalid_format(stt):
    result = await stt.transcribe(b"fake", "test.xyz")
    assert not result.success
    assert "Format" in result.error

@pytest.mark.asyncio
async def test_stt_file_too_large(stt):
    big = b"0" * (11 * 1024 * 1024)  # 11MB > 10MB max
    result = await stt.transcribe(big, "big.wav")
    assert not result.success
    assert "volumineux" in result.error

# ━━━ TTS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@pytest.fixture(scope="module")
def tts():
    from agents.tts_agent import TTSAgent, load_engine
    load_engine()
    return TTSAgent()

@pytest.mark.asyncio
async def test_tts_connection(tts):
    ok = await tts.check_connection()
    assert ok, "pyttsx3 non chargé"

@pytest.mark.asyncio
async def test_tts_synthesize(tts):
    result = await tts.synthesize("Bonjour, je suis Néron.")
    assert result.success, f"TTS failure: {result.error}"
    assert len(result.metadata["audio_bytes"]) > 0

@pytest.mark.asyncio
async def test_tts_empty_text(tts):
    result = await tts.synthesize("")
    assert not result.success
    assert result.error == "Texte vide"

@pytest.mark.asyncio
async def test_tts_text_too_long(tts):
    result = await tts.synthesize("x" * 1001)
    assert not result.success
    assert "long" in result.error

# ━━━ ROUTER ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@pytest.fixture(scope="module")
def router():
    from orchestrator.intent_router import IntentRouter
    return IntentRouter(llm_agent=None)

@pytest.mark.asyncio
async def test_router_web_search(router):
    from orchestrator.intent_router import Intent
    result = await router.route("cherche des infos sur Python")
    assert result.intent == Intent.WEB_SEARCH
    assert result.confidence == "high"

@pytest.mark.asyncio
async def test_router_meteo(router):
    from orchestrator.intent_router import Intent
    result = await router.route("quelle est la météo demain")
    assert result.intent == Intent.WEB_SEARCH

@pytest.mark.asyncio
async def test_router_ha_action(router):
    from orchestrator.intent_router import Intent
    result = await router.route("allume la lumière")
    assert result.intent == Intent.HA_ACTION

@pytest.mark.asyncio
async def test_router_time_heure(router):
    from orchestrator.intent_router import Intent
    result = await router.route("quelle heure est-il")
    assert result.intent == Intent.TIME_QUERY
    assert result.confidence == "high"

@pytest.mark.asyncio
async def test_router_time_date(router):
    from orchestrator.intent_router import Intent
    result = await router.route("on est quel jour")
    assert result.intent == Intent.TIME_QUERY

@pytest.mark.asyncio
async def test_router_conversation(router):
    from orchestrator.intent_router import Intent
    result = await router.route("bonjour comment tu vas")
    assert result.intent == Intent.CONVERSATION

@pytest.mark.asyncio
async def test_router_result_structure(router):
    result = await router.route("bonjour")
    assert hasattr(result, "intent")
    assert hasattr(result, "confidence")
