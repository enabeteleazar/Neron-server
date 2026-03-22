# agents/code_audit_agent.py
# Néron Core — Agent Développeur Autonome
# analyse et audit du code

from ollama import Ollama
import os

class CodeAuditAgent:
    def __init__(self, model="mistral"):
        self.ollama = Ollama(model=model)

    def audit_file(self, file_path):
        with open(file_path, "r") as f:
            code = f.read()
        prompt = f"Analyse ce code Python et indique erreurs ou améliorations:\n{code}"
        return self.ollama.chat(prompt)

    def audit_all(self, folder="core"):
        reports = {}
        for root, _, files in os.walk(folder):
            for file in files:
                if file.endswith(".py"):
                    path = os.path.join(root, file)
                    reports[path] = self.audit_file(path)
        return reports
