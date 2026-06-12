from __future__ import annotations

from core.capabilities.models import CapabilityDecision, CapabilityResult
from core.pipeline.intent.intent_router import Intent, IntentResult


class FakeMetrics:
    def record_request_start(self):
        return None

    def record_request_end(self, _elapsed):
        return None

    def record_intent(self, _intent):
        return None


class FakeIntentRouter:
    async def route(self, _query):
        return IntentResult(
            intent=Intent.CONVERSATION,
            confidence="high",
            confidence_score=0.9,
        )


class FakeCapabilityResolver:
    def __init__(self, result):
        self.result = result
        self.requests = []

    async def resolve(self, request):
        self.requests.append(request)
        return self.result


async def test_natural_telegram_input_passes_through_capability_resolver(monkeypatch):
    from core import app as core_app

    resolver = FakeCapabilityResolver(
        CapabilityResult(
            status="completed",
            response="Pâques 2027 tombe le 28 mars 2027.",
            tool_slug="date.easter",
            decision=CapabilityDecision(
                decision="use_existing_tool",
                confidence=0.96,
                reason="tool found",
                capability_type="tool",
                selected_tool="date.easter",
            ),
        )
    )

    async def fake_publish(*_args, **_kwargs):
        return None

    monkeypatch.setattr(core_app, "router", FakeIntentRouter())
    monkeypatch.setattr(core_app, "metrics", FakeMetrics())
    monkeypatch.setattr(core_app.event_bus, "publish", fake_publish)
    monkeypatch.setattr(core_app, "get_capability_resolver", lambda: resolver)

    response = await core_app.text_input(
        core_app.TextInput(
            text="Donne-moi la date de Pâques 2027",
            source_channel="telegram",
            user_id="chat-42",
        ),
        None,
    )

    assert response.response == "Pâques 2027 tombe le 28 mars 2027."
    assert response.intent == "use_existing_tool"
    assert response.agent == "date.easter"
    assert response.metadata["source"] == "telegram"
    assert resolver.requests[0].channel == "telegram"
    assert resolver.requests[0].user_id == "chat-42"


async def test_natural_telegram_creation_returns_short_async_response(monkeypatch):
    from core import app as core_app

    resolver = FakeCapabilityResolver(
        CapabilityResult(
            status="pending",
            response="Je m’en occupe. Je te reviens avec la réponse dès que c’est prêt.",
            async_started=True,
            goal_id="goal-123",
            decision=CapabilityDecision(
                decision="create_agent",
                confidence=0.91,
                reason="durable request",
                capability_type="agent",
                requires_creation=True,
                creation_type="agent",
                async_required=True,
            ),
        )
    )

    async def fake_publish(*_args, **_kwargs):
        return None

    monkeypatch.setattr(core_app, "router", FakeIntentRouter())
    monkeypatch.setattr(core_app, "metrics", FakeMetrics())
    monkeypatch.setattr(core_app.event_bus, "publish", fake_publish)
    monkeypatch.setattr(core_app, "get_capability_resolver", lambda: resolver)

    response = await core_app.text_input(
        core_app.TextInput(text="Surveille mon serveur", source_channel="telegram"),
        None,
    )

    assert response.intent == "create_agent"
    assert response.response.startswith("Je m’en occupe")
    assert response.metadata["capability"]["goal_id"] == "goal-123"
    assert "sandbox" not in response.response.lower()
    assert "registry" not in response.response.lower()


async def test_unknown_durable_telegram_request_does_not_reach_conversation(monkeypatch):
    from core import app as core_app
    from core.capabilities.registry import CapabilityRegistry
    from core.capabilities.resolver import CapabilityResolver

    class EmptyAgents:
        def list_agent_records(self):
            return []

    class EmptyProjects:
        def list_projects(self, status=None, limit=100):
            return []

    class Goals:
        def create_goal(self, **kwargs):
            return {"id": "goal-log-analysis", "metadata": kwargs["metadata"]}

        def update_status(self, goal_id, status, **kwargs):
            return {"id": goal_id, "status": status}

    class Engine:
        def enqueue_goal(self, goal_id, title, source, metadata):
            return {"goal_id": goal_id, "status": "queued"}

    class Runner:
        def submit(self, **kwargs):
            self.submitted = kwargs

    async def fake_publish(*_args, **_kwargs):
        return None

    resolver = CapabilityResolver(
        registry=CapabilityRegistry(
            agent_registry=EmptyAgents(),
            project_manager=EmptyProjects(),
            builtins=[],
        ),
        goal_manager=Goals(),
        execution_engine=Engine(),
        background_runner=Runner(),
    )
    monkeypatch.setattr(core_app, "router", FakeIntentRouter())
    monkeypatch.setattr(core_app, "metrics", FakeMetrics())
    monkeypatch.setattr(core_app.event_bus, "publish", fake_publish)
    monkeypatch.setattr(core_app, "get_capability_resolver", lambda: resolver)

    response = await core_app.text_input(
        core_app.TextInput(
            text="Analyse automatiquement les logs Néron et résume les erreurs critiques",
            source_channel="telegram",
        ),
        None,
    )

    capability = response.metadata["capability"]
    assert response.intent == "create_agent"
    assert response.response.startswith("Je m’en occupe")
    assert capability["async_started"] is True
    assert capability["goal_id"] == "goal-log-analysis"
