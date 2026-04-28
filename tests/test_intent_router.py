# tests/test_intent_router.py
"""
Tests unitaires — IntentRouter
Couvre : tous les intents, normalisation des accents, priorités, cas limites.
"""

import pytest
from core.pipeline.intent.intent_router import IntentRouter, Intent, _normalize


# ── Fixture ────────────────────────────────────────────────────────────────────

@pytest.fixture
def router():
    return IntentRouter()


# ── _normalize ─────────────────────────────────────────────────────────────────

class TestNormalize:
    def test_lowercase(self):
        assert _normalize("BONJOUR") == "bonjour"

    def test_strip_accents(self):
        assert _normalize("éàü") == "eau"

    def test_strip_and_lower(self):
        assert _normalize("  Quelle Heure  ") == "quelle heure"

    def test_empty(self):
        assert _normalize("") == ""

    def test_already_clean(self):
        assert _normalize("test") == "test"


# ── Routage par intent ─────────────────────────────────────────────────────────

class TestIntentTime:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("query", [
        "quelle heure est-il ?",
        "Quelle heure est-il",
        "Il est quelle heure ?",
        "Donne moi l'heure",
        "on est quel jour ?",
        "quel jour sommes-nous ?",
        "on est le combien ?",
        "quelle date sommes-nous ?",
    ])
    async def test_time_keywords(self, router, query):
        result = await router.route(query)
        assert result.intent == Intent.TIME_QUERY
        assert result.confidence == "high"

    @pytest.mark.asyncio
    async def test_time_with_accents_stripped(self, router):
        result = await router.route("Donne moi l'heure s'il te plaît")
        assert result.intent == Intent.TIME_QUERY


class TestIntentWeb:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("query", [
        "cherche la météo à Paris",
        "recherche les actualités",
        "google me ça",
        "news du jour",
        "météo demain",
        "actualité technologie",
    ])
    async def test_web_keywords(self, router, query):
        result = await router.route(query)
        assert result.intent == Intent.WEB_SEARCH
        assert result.confidence == "high"


class TestIntentHA:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("query", [
        "allume la lumière du salon",
        "éteins le thermostat",
        "baisse les volets",
        "home assistant status",
        "lumiere cuisine",
    ])
    async def test_ha_keywords(self, router, query):
        result = await router.route(query)
        assert result.intent == Intent.HA_ACTION
        assert result.confidence == "high"


class TestIntentCode:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("query", [
        "génère un fichier Python",
        "crée un fichier main.py",
        "écris un script bash",
        "améliore ce code",
        "refactorise ce module",
        "corrige le fichier agents.py",
        "analyse le fichier config.py",
        "optimise le fichier scheduler",
        "lis le fichier sessions.py",
        "self review",
        "revue de code",
        "rollback",
    ])
    async def test_code_keywords(self, router, query):
        result = await router.route(query)
        assert result.intent == Intent.CODE
        assert result.confidence == "high"


class TestIntentCodeAudit:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("query", [
        "analyse ton code",
        "analyse-toi",
        "inspecte ton code",
        "audite ton code",
        "auto audit",
        "auto-audit",
        "qualite de ton code",
        "analyse le code de neron",
    ])
    async def test_audit_keywords(self, router, query):
        result = await router.route(query)
        assert result.intent == Intent.CODE_AUDIT
        assert result.confidence == "high"


class TestIntentPersonality:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("query", [
        "tu es trop long",
        "sois bref",
        "raccourcis tes réponses",
        "plus de détail s'il te plaît",
        "sois direct",
        "mode technique",
        "sois plus sympa",
        "calme-toi",
        "mode focus",
        "sois positif",
    ])
    async def test_personality_keywords(self, router, query):
        result = await router.route(query)
        assert result.intent == Intent.PERSONALITY_FEEDBACK
        assert result.confidence == "high"


class TestIntentConversation:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("query", [
        "bonjour",
        "comment ça va ?",
        "tu peux m'aider ?",
        "test",
        "hello world",
        "explique-moi la photosynthèse",
        "",
    ])
    async def test_fallback_conversation(self, router, query):
        result = await router.route(query)
        assert result.intent == Intent.CONVERSATION
        assert result.confidence == "medium"


# ── Priorités ──────────────────────────────────────────────────────────────────

class TestIntentPriority:
    @pytest.mark.asyncio
    async def test_personality_over_everything(self, router):
        """PERSONALITY_FEEDBACK est détecté en premier."""
        result = await router.route("cherche et sois bref")
        assert result.intent == Intent.PERSONALITY_FEEDBACK

    @pytest.mark.asyncio
    async def test_code_audit_over_code(self, router):
        """CODE_AUDIT prioritaire sur CODE générique."""
        result = await router.route("analyse ton code et génère un rapport")
        assert result.intent == Intent.CODE_AUDIT

    @pytest.mark.asyncio
    async def test_time_over_conversation(self, router):
        result = await router.route("dis-moi quelle heure il est s'il te plaît")
        assert result.intent == Intent.TIME_QUERY
