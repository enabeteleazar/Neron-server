from __future__ import annotations


class AutonomousSecurity:
    """
    Sécurité V1 :
    - blacklist commandes dangereuses
    - validation actions
    """

    BLOCKED_KEYWORDS = [
        "rm -rf",
        "mkfs",
        "shutdown",
        "reboot",
        "dd ",
        ":(){:|:&};:",
    ]

    def validate(self, objective: str) -> tuple[bool, str | None]:
        lower = objective.lower()

        for keyword in self.BLOCKED_KEYWORDS:
            if keyword in lower:
                return False, keyword

        return True, None
