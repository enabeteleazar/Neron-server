"""
neron/skills.py
===============
Skills — système de plugins inspiré d'OpenClaw Skills Platform.

Concept clé (repris d'OpenClaw) :
  "Skill discovery vs. skill injection est un détail important :
   le runtime sélectionne uniquement la/les skill(s) pertinente(s)
   au tour actuel pour éviter de faire exploser le prompt."

Structure d'une Skill :
  ~/.neron/workspace/skills/<nom>/SKILL.md   ← instructions injectées
  ~/.neron/workspace/skills/<nom>/skill.json ← métadonnées + triggers

Format skill.json :
  {
    "name": "weather",
    "description": "Donne la météo actuelle.",
    "version": "1.0.0",
    "triggers": ["météo", "weather", "temps qu'il fait", "température"],
    "inject_always": false,
    "tools": ["get_weather"]  // tools Python à enregistrer
  }

Format SKILL.md :
  # Weather Skill
  Tu as accès à l'outil get_weather(city: str).
  Utilise-le quand l'utilisateur demande la météo.

Injection sélective :
  L'AgentRouter appelle skills.build_system_injection(intent)
  qui retourne le contenu SKILL.md des skills dont un trigger
  matche l'intent courant. Les skills inject_always=true sont
  toujours incluses.
"""

from __future__ import annotations

import importlib.util
import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger("neron.skills")

WORKSPACE_DIR = Path(os.getenv("NERON_WORKSPACE_DIR", Path.home() / ".neron" / "workspace"))
SKILLS_DIR = WORKSPACE_DIR / "skills"

# ──────────────────────────────────────────────────────────────────────────────
# Dataclass Skill
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class Skill:
    name: str
    description: str = ""
    version: str = "1.0.0"
    triggers: list[str] = field(default_factory=list)
    inject_always: bool = False
    skill_md: str = ""           # contenu du SKILL.md
    tools: list[str] = field(default_factory=list)  # noms d'outils Python
    _handlers: dict[str, Callable] = field(default_factory=dict, repr=False)

    def matches_intent(self, intent: str | None) -> bool:
        if intent is None:
            return False
        intent_lower = intent.lower()
        return any(trigger.lower() in intent_lower for trigger in self.triggers)

    async def call(self, tool_name: str, **kwargs: Any) -> Any:
        handler = self._handlers.get(tool_name)
        if handler is None:
            return {"error": f"Outil inconnu dans la skill {self.name} : {tool_name}"}
        return await handler(**kwargs)

# ──────────────────────────────────────────────────────────────────────────────
# SkillRegistry
# ──────────────────────────────────────────────────────────────────────────────

class SkillRegistry:
    """
    Charge, indexe et injecte les skills au runtime.
    Scan automatique du répertoire skills/ au démarrage.
    """

    def __init__(self, skills_dir: Path | None = None) -> None:
        self.skills_dir = skills_dir or SKILLS_DIR
        self._skills: dict[str, Skill] = {}
        self._load_all()

    # ── Chargement ──────────────────────────────────────────────────────────

    def _load_all(self) -> None:
        if not self.skills_dir.exists():
            self.skills_dir.mkdir(parents=True, exist_ok=True)
            self._install_builtin_skills()
            return

        for skill_dir in sorted(self.skills_dir.iterdir()):
            if skill_dir.is_dir():
                self._load_skill_dir(skill_dir)

        if not self._skills:
            self._install_builtin_skills()

        logger.info("Skills chargées : %s", list(self._skills.keys()))

    def _load_skill_dir(self, skill_dir: Path) -> None:
        meta_path = skill_dir / "skill.json"
        md_path = skill_dir / "SKILL.md"

        if not meta_path.exists():
            return

        try:
            with meta_path.open(encoding="utf-8") as f:
                meta = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Impossible de charger %s : %s", meta_path, e)
            return

        skill_md = ""
        if md_path.exists():
            skill_md = md_path.read_text(encoding="utf-8")

        skill = Skill(
            name=meta.get("name", skill_dir.name),
            description=meta.get("description", ""),
            version=meta.get("version", "1.0.0"),
            triggers=meta.get("triggers", []),
            inject_always=meta.get("inject_always", False),
            skill_md=skill_md,
            tools=meta.get("tools", []),
        )

        # Charge le module Python de la skill si présent
        py_path = skill_dir / "skill.py"
        if py_path.exists():
            self._load_skill_module(skill, py_path)

        self._skills[skill.name] = skill
        logger.debug("Skill chargée : %s (triggers: %s)", skill.name, skill.triggers)

    def _load_skill_module(self, skill: Skill, py_path: Path) -> None:
        """Charge dynamiquement le module Python d'une skill."""
        try:
            spec = importlib.util.spec_from_file_location(
                f"neron.skills.{skill.name}", py_path
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            # Enregistre les handlers : fonctions async dont le nom est dans skill.tools
            for tool_name in skill.tools:
                handler = getattr(module, tool_name, None)
                if handler and callable(handler):
                    skill._handlers[tool_name] = handler
                    logger.debug("Handler %s.%s chargé", skill.name, tool_name)
        except Exception as e:
            logger.warning("Erreur chargement module skill %s : %s", skill.name, e)

    # ── Skills intégrées (toujours disponibles) ─────────────────────────────

    def _install_builtin_skills(self) -> None:
        """Installe les skills de base de Neron sans fichiers sur disque."""
        builtins = [
            Skill(
                name="neron_core",
                description="Capacités de base de Neron (identité, statut).",
                inject_always=True,
                skill_md=NERON_CORE_SKILL_MD,
            ),
            Skill(
                name="ollama",
                description="Skill pour interroger Ollama directement.",
                triggers=["modèle", "ollama", "llm", "liste des modèles", "models"],
                skill_md=OLLAMA_SKILL_MD,
            ),
            Skill(
                name="nexus_avatar",
                description="Contrôle l'avatar 3D dans NEXUS.",
                triggers=["avatar", "animation", "expression", "parle", "bouge"],
                skill_md=NEXUS_AVATAR_SKILL_MD,
            ),
        ]
        for skill in builtins:
            self._skills[skill.name] = skill

    # ── API publique ────────────────────────────────────────────────────────

    def register(self, skill: Skill) -> None:
        self._skills[skill.name] = skill
        logger.info("Skill enregistrée : %s", skill.name)

    def get(self, name: str) -> Skill | None:
        return self._skills.get(name)

    def list_all(self) -> list[Skill]:
        return list(self._skills.values())

    def build_system_injection(self, intent: str | None = None) -> str:
        """
        Retourne le contenu SKILL.md des skills pertinentes à injecter.
        Sélection : inject_always=True OU trigger matche l'intent.
        Limite : max 3 skills injectées par tour pour ne pas saturer le prompt.
        """
        selected: list[Skill] = []

        # 1. Skills toujours injectées
        for skill in self._skills.values():
            if skill.inject_always and skill.skill_md:
                selected.append(skill)

        # 2. Skills contextuelles (max 2 supplémentaires)
        if intent:
            for skill in self._skills.values():
                if not skill.inject_always and skill.skill_md and skill.matches_intent(intent):
                    selected.append(skill)
                    if len(selected) >= 3:
                        break

        if not selected:
            return ""

        parts = [f"## Skill : {s.name}\n{s.skill_md.strip()}" for s in selected]
        return "\n\n".join(parts)

    async def call(self, skill_name: str, tool_name: str | None = None, **kwargs: Any) -> Any:
        """Appel direct d'une skill depuis la Gateway."""
        skill = self._skills.get(skill_name)
        if skill is None:
            return {"error": f"Skill inconnue : {skill_name}"}
        if tool_name is None:
            return {"name": skill.name, "description": skill.description, "skill_md": skill.skill_md}
        return await skill.call(tool_name, **kwargs)

    def reload(self) -> None:
        """Recharge toutes les skills depuis le disque (hot-reload)."""
        self._skills.clear()
        self._load_all()
        logger.info("Skills rechargées")

# ──────────────────────────────────────────────────────────────────────────────
# Contenu SKILL.md des skills intégrées
# ──────────────────────────────────────────────────────────────────────────────

NERON_CORE_SKILL_MD = """
# Neron Core
Tu es **Neron**, l'assistant IA local du projet NEXUS.
Tu es incarné dans un avatar 3D rendu via Three.js r128.
Tu communiques via un Gateway WebSocket local sur le réseau LAN/Tailscale.
Tu peux interagir avec des modèles LLM locaux via Ollama.

Règles de base :
- Sois concis, précis, et utile.
- Si tu ne sais pas quelque chose, dis-le franchement.
- Préfère les réponses en français sauf si l'utilisateur parle une autre langue.
""".strip()

OLLAMA_SKILL_MD = """
# Ollama Skill
Tu peux informer l'utilisateur sur les modèles Ollama disponibles.
L'API Ollama est accessible sur `http://192.168.1.130:8010`.
Endpoints utiles :
- GET /api/tags          — liste les modèles installés
- POST /api/chat         — conversation (stream=true)
- POST /api/generate     — completion simple
""".strip()

NEXUS_AVATAR_SKILL_MD = """
# NEXUS Avatar Skill
L'avatar 3D de Neron est rendu dans Three.js r128 (hiérarchie THREE.Group, MeshPhongMaterial).
Quand tu veux animer ou décrire une action de l'avatar, précise :
- L'expression : neutre | sourire | surprise | pensif | alerte
- L'animation : idle | parler | hocher | regarder_gauche | regarder_droite
Ces états sont transmis via WebSocket au client NEXUS frontend.
""".strip()

# ──────────────────────────────────────────────────────────────────────────────
# Exemple de skill externe (structure sur disque)
# ──────────────────────────────────────────────────────────────────────────────

EXAMPLE_SKILL_JSON = {
    "name": "example_skill",
    "description": "Exemple de skill externe.",
    "version": "1.0.0",
    "triggers": ["exemple", "test", "démo"],
    "inject_always": False,
    "tools": ["hello_world"],
}

EXAMPLE_SKILL_MD = """
# Example Skill
Cette skill de démonstration répond au déclencheur "exemple" ou "test".
Elle expose l'outil `hello_world` qui retourne un message de bienvenue.
""".strip()

EXAMPLE_SKILL_PY = '''
async def hello_world(name: str = "monde") -> dict:
    return {"message": f"Bonjour, {name} ! Skill Neron opérationnelle."}
'''.strip()


def create_example_skill(skills_dir: Path | None = None) -> Path:
    """Utilitaire : crée une skill d'exemple sur le disque."""
    base = (skills_dir or SKILLS_DIR) / "example_skill"
    base.mkdir(parents=True, exist_ok=True)
    (base / "skill.json").write_text(json.dumps(EXAMPLE_SKILL_JSON, indent=2, ensure_ascii=False))
    (base / "SKILL.md").write_text(EXAMPLE_SKILL_MD)
    (base / "skill.py").write_text(EXAMPLE_SKILL_PY)
    return base
