# agents/code_agent.py
# Néron Core — Agent Développeur Autonome

import asyncio
import hashlib
import httpx
import json
import os
import shutil
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from agents.base_agent import BaseAgent, AgentResult
from config import settings

# ── Constantes ────────────────────────────────────────────────────────────────

OLLAMA_HOST  = settings.OLLAMA_HOST
OLLAMA_MODEL = getattr(settings, 'CODE_AGENT_MODEL', settings.OLLAMA_MODEL)

LLM_TIMEOUT  = settings.LLM_TIMEOUT

# Répertoire racine de Néron — toute écriture hors de là est bloquée
_NERON_ROOT  = Path(__file__).parent.parent.resolve()
_BACKUP_DIR  = _NERON_ROOT / "data" / "code_backups"
_SANDBOX_TIMEOUT = 10  # secondes

# Extensions considérées comme code Python
_PY_EXT = {".py"}

# Dossiers exclus de l'auto-analyse (on ne touche pas au venv, cache, etc.)
_EXCLUDE_DIRS = {"__pycache__", "venv", ".git", "data", "docs", "scripts"}

# ── Prompts LLM ───────────────────────────────────────────────────────────────

_PROMPT_GENERATE = """Tu es un expert Python. Génère uniquement du code Python propre,
documenté avec des docstrings, sans explications ni balises markdown.
Juste le code brut, prêt à être écrit dans un fichier .py."""

_PROMPT_IMPROVE = """Tu es un expert en qualité de code Python.
Analyse le code fourni et retourne une version améliorée.
Règles strictes :
- Corriger les bugs évidents
- Ajouter les docstrings manquantes
- Respecter PEP8
- Ne pas changer la logique métier sans raison explicite
- Retourner UNIQUEMENT le code Python amélioré, sans explications, sans balises markdown."""

_PROMPT_ANALYZE = """Tu es un expert Python. Analyse ce fichier source et retourne
un rapport JSON avec exactement ce format (rien d'autre) :
{
  "quality_score": <0-100>,
  "issues": ["issue1", "issue2"],
  "suggestions": ["suggestion1", "suggestion2"],
  "has_docstrings": <true|false>,
  "pep8_ok": <true|false>
}"""


# ── Utilitaires internes ───────────────────────────────────────────────────────

def _safe_path(raw: str) -> Path:
    """Valide qu'un chemin reste dans _NERON_ROOT. Lève ValueError sinon."""
    target = (_NERON_ROOT / raw).resolve()
    if not str(target).startswith(str(_NERON_ROOT)):
        raise ValueError(f"Chemin non autorisé (hors workspace) : {raw!r}")
    return target


def _backup(path: Path) -> Optional[Path]:
    """Sauvegarde un fichier avant modification. Retourne le chemin du backup."""
    if not path.exists():
        return None
    _BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts        = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = str(path.relative_to(_NERON_ROOT)).replace("/", "_").replace("\\", "_")
    dest      = _BACKUP_DIR / f"{safe_name}.{ts}.bak"
    shutil.copy2(path, dest)
    # Rotation : garder les 10 derniers backups de ce fichier
    existing = sorted(_BACKUP_DIR.glob(f"{safe_name}.*.bak"))
    for old in existing[:-10]:
        old.unlink(missing_ok=True)
    return dest


def _rollback(path: Path) -> bool:
    """Restaure le backup le plus récent pour ce fichier."""
    safe_name = str(path.relative_to(_NERON_ROOT)).replace("/", "_").replace("\\", "_")
    backups   = sorted(_BACKUP_DIR.glob(f"{safe_name}.*.bak"))
    if not backups:
        return False
    shutil.copy2(backups[-1], path)
    return True


def _sandbox_test(code: str) -> dict:
    """
    Exécute le code dans un subprocess isolé.
    Retourne {"ok": bool, "stdout": str, "stderr": str}
    """
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write(code)
        tmp = Path(f.name)
    try:
        result = subprocess.run(
            ["python3", str(tmp)],
            capture_output=True, text=True,
            timeout=_SANDBOX_TIMEOUT
        )
        return {
            "ok":     result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "stdout": "", "stderr": f"Timeout ({_SANDBOX_TIMEOUT}s)"}
    except Exception as e:
        return {"ok": False, "stdout": "", "stderr": str(e)}
    finally:
        tmp.unlink(missing_ok=True)


def _check_syntax(code: str) -> dict:
    """Vérifie la syntaxe Python sans exécuter le code."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write(code)
        tmp = Path(f.name)
    try:
        result = subprocess.run(
            ["python3", "-m", "py_compile", str(tmp)],
            capture_output=True, text=True
        )
        return {"ok": result.returncode == 0, "stderr": result.stderr}
    finally:
        tmp.unlink(missing_ok=True)


# ── Agent principal ────────────────────────────────────────────────────────────

class CodeAgent(BaseAgent):
    """
    Agent développeur autonome de Néron.

    Actions disponibles via execute() :
      - "generate"  : génère un nouveau fichier Python
      - "improve"   : améliore un fichier existant (backup + sandbox)
      - "analyze"   : analyse un fichier et retourne un rapport
      - "read"      : lit le contenu d'un fichier source
      - "self_review" : passe en revue tous les fichiers source de Néron
      - "rollback"  : restaure le dernier backup d'un fichier
    """

    def __init__(self):
        super().__init__(name="code_agent")
        self.logger.info(
            f"CodeAgent init — Ollama : {OLLAMA_HOST} | modèle : {OLLAMA_MODEL}"
        )

    # ── Point d'entrée principal ───────────────────────────────────────────

    async def execute(self, query: str, **kwargs) -> AgentResult:
        """
        Dispatch selon kwargs["action"]. Si aucune action explicite,
        détecte l'intention depuis le texte de la query.
        """
        start  = self._timer()
        action = kwargs.get("action") or self._detect_action(query)
        path   = kwargs.get("path", "")

        self.logger.info(f"CodeAgent action={action!r} path={path!r} query={query[:60]!r}")

        try:
            if action == "generate":
                return await self._generate(query, path, start)
            elif action == "improve":
                return await self._improve(path, query, start)
            elif action == "analyze":
                return await self._analyze(path, start)
            elif action == "read":
                return await self._read(path, start)
            elif action == "self_review":
                return await self._self_review(start)
            elif action == "rollback":
                return self._do_rollback(path, start)
            else:
                # Action inconnue → génération libre
                return await self._generate(query, path, start)
        except ValueError as e:
            return self._failure(str(e), latency_ms=self._elapsed_ms(start))
        except Exception as e:
            self.logger.exception(f"CodeAgent exception inattendue : {e}")
            return self._failure(f"Erreur inattendue : {e}", latency_ms=self._elapsed_ms(start))

    # ── check_connection (requis par watchdog_agent) ───────────────────────

    async def check_connection(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{OLLAMA_HOST}/api/tags")
                return r.status_code == 200
        except Exception:
            return False

    async def reload(self) -> bool:
        return await self.check_connection()

    # ── Actions ────────────────────────────────────────────────────────────

    async def _generate(self, query: str, path: str, start: float) -> AgentResult:
        """Génère du code Python et l'écrit si un path est fourni."""
        code = await self._llm_call(_PROMPT_GENERATE, query)
        if not code:
            return self._failure("LLM n'a pas retourné de code", latency_ms=self._elapsed_ms(start))

        # Nettoyer les balises markdown que certains modèles ajoutent
        import re as _re
        code = _re.sub(r"^```python\s*", "", code.strip())
        code = _re.sub(r"^```\s*", "", code.strip())
        code = _re.sub(r"```$", "", code.strip()).strip()

        result_meta = {"action": "generate", "code_length": len(code)}

        if path:
            write_result = self._write_code(path, code)
            if not write_result["ok"]:
                return self._failure(write_result["error"], latency_ms=self._elapsed_ms(start))
            result_meta["path"]    = write_result["path"]
            result_meta["sandbox"] = write_result.get("sandbox", {})
            summary = f"Fichier généré : {write_result['path']}\n\n```python\n{code[:500]}\n```"
        else:
            summary = f"```python\n{code}\n```"

        return self._success(summary, metadata=result_meta, latency_ms=self._elapsed_ms(start))

    async def _improve(self, path: str, context: str, start: float) -> AgentResult:
        """Améliore un fichier existant. Backup + syntax check + écriture."""
        if not path:
            return self._failure("Chemin de fichier requis pour 'improve'", latency_ms=self._elapsed_ms(start))

        safe = _safe_path(path)
        if not safe.exists():
            return self._failure(f"Fichier introuvable : {path}", latency_ms=self._elapsed_ms(start))

        original = safe.read_text(encoding="utf-8")
        prompt   = f"Contexte : {context}\n\nCode à améliorer :\n{original}"
        improved = await self._llm_call(_PROMPT_IMPROVE, prompt)

        if not improved or improved.strip() == original.strip():
            return self._success(
                f"Aucune amélioration nécessaire pour {path}",
                metadata={"action": "improve", "changed": False},
                latency_ms=self._elapsed_ms(start)
            )

        # Vérification syntaxe
        syntax = _check_syntax(improved)
        if not syntax["ok"]:
            return self._failure(
                f"Syntaxe invalide dans le code amélioré : {syntax['stderr'][:200]}",
                latency_ms=self._elapsed_ms(start)
            )

        # Backup + écriture
        backup_path = _backup(safe)
        safe.write_text(improved, encoding="utf-8")
        self.logger.info(f"Fichier amélioré : {safe} (backup : {backup_path})")

        return self._success(
            f"✅ {path} amélioré avec succès.\nBackup : {backup_path.name if backup_path else 'N/A'}",
            metadata={
                "action":      "improve",
                "path":        str(safe),
                "backup":      str(backup_path) if backup_path else None,
                "changed":     True,
                "lines_before": len(original.splitlines()),
                "lines_after":  len(improved.splitlines()),
            },
            latency_ms=self._elapsed_ms(start)
        )

    async def _analyze(self, path: str, start: float) -> AgentResult:
        """Analyse un fichier et retourne un rapport qualité JSON."""
        if not path:
            return self._failure("Chemin de fichier requis pour 'analyze'", latency_ms=self._elapsed_ms(start))

        safe = _safe_path(path)
        if not safe.exists():
            return self._failure(f"Fichier introuvable : {path}", latency_ms=self._elapsed_ms(start))

        code   = safe.read_text(encoding="utf-8")
        prompt = f"Fichier : {path}\n\nCode :\n{code}"
        raw    = await self._llm_call(_PROMPT_ANALYZE, prompt)

        try:
            report = json.loads(raw or "{}")
        except json.JSONDecodeError:
            report = {"raw": raw, "parse_error": True}

        summary = (
            f"📊 Analyse de `{path}`\n"
            f"Score : {report.get('quality_score', '?')}/100\n"
            f"Issues : {len(report.get('issues', []))}\n"
            f"Suggestions : {len(report.get('suggestions', []))}"
        )
        return self._success(
            summary,
            metadata={"action": "analyze", "path": str(safe), "report": report},
            latency_ms=self._elapsed_ms(start)
        )

    async def _read(self, path: str, start: float) -> AgentResult:
        """Lit le contenu d'un fichier source."""
        if not path:
            return self._failure("Chemin de fichier requis pour 'read'", latency_ms=self._elapsed_ms(start))

        safe = _safe_path(path)
        if not safe.exists():
            return self._failure(f"Fichier introuvable : {path}", latency_ms=self._elapsed_ms(start))

        content = safe.read_text(encoding="utf-8")
        return self._success(
            content,
            metadata={"action": "read", "path": str(safe), "lines": len(content.splitlines())},
            latency_ms=self._elapsed_ms(start)
        )

    async def _self_review(self, start: float) -> AgentResult:
        """
        Passe en revue tous les fichiers Python de Néron.
        Analyse chacun et retourne un rapport global.
        """
        files   = self._list_source_files()
        reports = []

        for f in files:
            try:
                code   = f.read_text(encoding="utf-8")
                prompt = f"Fichier : {f.name}\n\nCode :\n{code[:3000]}"  # limite contexte
                raw    = await self._llm_call(_PROMPT_ANALYZE, prompt)
                try:
                    report = json.loads(raw or "{}")
                except json.JSONDecodeError:
                    report = {"quality_score": None, "issues": [], "suggestions": []}

                reports.append({
                    "file":          str(f.relative_to(_NERON_ROOT)),
                    "quality_score": report.get("quality_score"),
                    "issues":        report.get("issues", []),
                    "suggestions":   report.get("suggestions", []),
                })
            except Exception as e:
                self.logger.warning(f"self_review: erreur sur {f}: {e}")
                reports.append({"file": str(f), "error": str(e)})

        # Résumé global
        scored  = [r for r in reports if isinstance(r.get("quality_score"), (int, float))]
        avg     = round(sum(r["quality_score"] for r in scored) / len(scored), 1) if scored else None
        total_issues = sum(len(r.get("issues", [])) for r in reports)

        summary = (
            f"🔍 Auto-review Néron — {len(files)} fichiers analysés\n"
            f"Score moyen : {avg}/100\n"
            f"Issues totales : {total_issues}"
        )
        return self._success(
            summary,
            metadata={
                "action":       "self_review",
                "files_count":  len(files),
                "avg_score":    avg,
                "total_issues": total_issues,
                "reports":      reports,
            },
            latency_ms=self._elapsed_ms(start)
        )

    def _do_rollback(self, path: str, start: float) -> AgentResult:
        """Restaure le dernier backup d'un fichier."""
        if not path:
            return self._failure("Chemin requis pour 'rollback'", latency_ms=self._elapsed_ms(start))
        try:
            safe = _safe_path(path)
            ok   = _rollback(safe)
            if ok:
                return self._success(
                    f"✅ Rollback effectué pour {path}",
                    metadata={"action": "rollback", "path": str(safe)},
                    latency_ms=self._elapsed_ms(start)
                )
            return self._failure(f"Aucun backup trouvé pour {path}", latency_ms=self._elapsed_ms(start))
        except ValueError as e:
            return self._failure(str(e), latency_ms=self._elapsed_ms(start))

    # ── Helpers ────────────────────────────────────────────────────────────

    def _detect_action(self, query: str) -> str:
        import unicodedata

        def norm(t):
            n = unicodedata.normalize("NFD", t.lower())
            return "".join(c for c in n if unicodedata.category(c) != "Mn")

        q = norm(query)

        if any(w in q for w in ("genere", "cree", "ecris", "generer", "creer")):
            return "generate"
        if any(w in q for w in ("ameliore", "optimise", "corrige", "refactorise")):
            return "improve"
        if any(w in q for w in ("analyse", "inspecte", "qualite", "rapport")):
            return "analyze"
        if any(w in q for w in ("self review", "auto review", "revue", "passe en revue")):
            return "self_review"
        if any(w in q for w in ("rollback", "restaure", "annule")):
            return "rollback"
        if any(w in q for w in ("lis le fichier", "montre le fichier", "affiche le fichier")):
            return "read"
        return "generate"


    def _write_code(self, path: str, code: str) -> dict:
        """Valide, sauvegarde et écrit du code. Rollback auto si erreur."""
        try:
            safe = _safe_path(path)
        except ValueError as e:
            return {"ok": False, "error": str(e)}

        # Forcer extension .py
        if safe.suffix not in _PY_EXT:
            safe = safe.with_suffix(".py")

        # Vérification syntaxe
        syntax = _check_syntax(code)
        if not syntax["ok"]:
            return {"ok": False, "error": f"Syntaxe invalide : {syntax['stderr'][:200]}"}

        # Backup si existant
        backup = _backup(safe)

        # Écriture
        safe.parent.mkdir(parents=True, exist_ok=True)
        safe.write_text(code, encoding="utf-8")
        safe.chmod(0o755)

        # Test sandbox (non bloquant — on avertit seulement)
        sandbox = _sandbox_test(code)
        if not sandbox["ok"]:
            self.logger.warning(f"Sandbox KO pour {safe} : {sandbox['stderr'][:100]}")

        return {
            "ok":      True,
            "path":    str(safe),
            "backup":  str(backup) if backup else None,
            "sandbox": sandbox,
        }

    def _list_source_files(self) -> list[Path]:
        """Liste tous les fichiers .py de Néron, hors dossiers exclus."""
        files = []
        for p in _NERON_ROOT.rglob("*.py"):
            if not any(excl in p.parts for excl in _EXCLUDE_DIRS):
                files.append(p)
        return sorted(files)

    async def _llm_call(self, system: str, prompt: str) -> Optional[str]:
        """Appel Ollama /api/chat avec retry x2."""
        payload = {
            "model":    OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": prompt},
            ],
            "stream": False,
        }
        for attempt in range(1, 3):
            try:
                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(connect=5.0, read=LLM_TIMEOUT, write=5.0, pool=5.0)
                ) as client:
                    r = await client.post(f"{OLLAMA_HOST}/api/chat", json=payload)
                    r.raise_for_status()
                    return r.json().get("message", {}).get("content", "").strip()
            except httpx.TimeoutException:
                self.logger.warning(f"LLM timeout (essai {attempt})")
            except Exception as e:
                self.logger.warning(f"LLM erreur (essai {attempt}) : {e}")
        return None
