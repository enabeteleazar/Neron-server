import asyncio
import logging
from typing import Dict

from neron_llm.core.router import LLMRouter
from neron_llm.core.types import LLMRequest, LLMResponse, ParallelLLMResponse, RaceLLMResponse
from neron_llm.providers.ollama import OllamaProvider
from neron_llm.providers.claude import ClaudeProvider
from neron_llm.providers.base import BaseProvider

logger = logging.getLogger(__name__)


class LLMManager:
    """Orchestre les appels LLM selon le mode demandé.

    Modes disponibles :
    - single   : un seul provider, choisi par le router
    - parallel : tous les providers en asyncio.gather — retourne tous les résultats
    - race     : asyncio.wait(FIRST_COMPLETED) — retourne le premier, annule les autres
    """

    def __init__(self):
        self.router = LLMRouter()
        self.providers: Dict[str, BaseProvider] = {
            "ollama": OllamaProvider(),
            "claude": ClaudeProvider(),
        }

    # ------------------------------------------------------------------
    # Mode SINGLE
    # ------------------------------------------------------------------

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Appel unique vers le provider sélectionné par le router."""
        provider_name = self.router.select_provider(request)
        model = self.router.select_model(request.task)

        provider = self.providers.get(provider_name) or self.providers["ollama"]

        logger.debug("single | provider=%s model=%s", provider_name, model)
        response = await provider.generate(request.message, model)

        return LLMResponse(provider=provider_name, model=model, response=response)

    # ------------------------------------------------------------------
    # Mode PARALLEL
    # ------------------------------------------------------------------

    async def generate_parallel(self, request: LLMRequest) -> ParallelLLMResponse:
        """Interroge tous les providers simultanément via asyncio.gather.

        Retourne tous les résultats, même si certains échouent (les erreurs
        sont capturées et incluses dans la réponse sous forme de message d'erreur).
        """
        model = self.router.select_model(request.task)

        async def call(name: str, provider: BaseProvider) -> tuple[str, str]:
            try:
                resp = await provider.generate(request.message, model)
                return name, resp
            except Exception as exc:
                logger.warning("parallel | provider=%s erreur: %s", name, exc)
                return name, f"[ERREUR {name}] {exc}"

        tasks = [call(name, p) for name, p in self.providers.items()]
        pairs = await asyncio.gather(*tasks)

        return ParallelLLMResponse(results=dict(pairs))

    # ------------------------------------------------------------------
    # Mode RACE
    # ------------------------------------------------------------------

    async def generate_race(self, request: LLMRequest) -> RaceLLMResponse:
        """Lance tous les providers en compétition — le premier qui répond gagne.

        Les tâches perdantes sont explicitement annulées.
        """
        model = self.router.select_model(request.task)

        async def call(name: str, provider: BaseProvider) -> tuple[str, str]:
            resp = await provider.generate(request.message, model)
            return name, resp

        loop = asyncio.get_running_loop()
        tasks = {
            loop.create_task(call(name, p), name=name)
            for name, p in self.providers.items()
        }

        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

        # Annuler les perdants proprement
        for t in pending:
            t.cancel()
            try:
                await t
            except (asyncio.CancelledError, Exception):
                pass

        winner_task = next(iter(done))
        try:
            winner_name, winner_response = winner_task.result()
        except Exception as exc:
            logger.error("race | le gagnant a levé une exception: %s", exc)
            winner_name, winner_response = "unknown", f"[ERREUR RACE] {exc}"

        logger.debug("race | gagnant=%s", winner_name)
        return RaceLLMResponse(winner=winner_name, response=winner_response)
