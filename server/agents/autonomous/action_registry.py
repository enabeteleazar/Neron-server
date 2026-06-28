from __future__ import annotations


class ActionRegistry:
    def __init__(self):
        self.actions = {}

    def register(
        self,
        name: str,
        handler,
    ) -> None:

        self.actions[name] = handler

    def get(
        self,
        name: str,
    ):

        if name not in self.actions:
            raise ValueError(
                f"Action inconnue: {name}"
            )

        return self.actions[name]

    def exists(
        self,
        name: str,
    ) -> bool:

        return name in self.actions

    def list_actions(
        self,
    ) -> list[str]:

        return sorted(
            self.actions.keys()
        )
