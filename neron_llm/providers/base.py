from abc import ABC, abstractmethod


class BaseProvider(ABC):
    """Interface commune à tous les providers LLM.

    Toutes les implémentations DOIVENT être async pour permettre
    l'exécution parallèle et race sans bloquer l'event loop.
    """

    @abstractmethod
    async def generate(self, message: str, model: str) -> str:
        """Envoie un message au LLM et retourne la réponse textuelle."""
        ...
