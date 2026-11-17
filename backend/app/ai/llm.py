"""Adaptador de IA: um único ponto de contato com o modelo de linguagem.

- Com a chave GROQ_API_KEY configurada, chama o Groq (plano gratuito).
- Sem chave, ou se a chamada falhar (limite, rede, resposta ruim), devolve
  None e quem chamou usa a versão SIMULADA (regras simples). O site mostra
  qual modo respondeu ("IA real" ou "simulado").

A IA só INTERPRETA texto e EXPLICA. Quem decide a squad é o algoritmo.
A chave nunca sai do servidor: o site não a conhece.
"""
import json
import os
import re
from pathlib import Path

import httpx

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-oss-120b"
TIMEOUT_SECONDS = 15.0


def _load_env_file() -> None:
    """Lê backend/.env (se existir) sem depender de bibliotecas extras."""
    path = Path(__file__).resolve().parents[2] / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env_file()


def is_configured() -> bool:
    return bool(os.environ.get("GROQ_API_KEY"))


def mode_label(used_real: bool) -> str:
    return "ia_real" if used_real else "simulado"


def _extract_json(text: str):
    """Pega o primeiro objeto JSON da resposta, mesmo que venha com texto em volta."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def ask_json(system: str, user: str):
    """Pede ao modelo uma resposta em JSON. Devolve um dict ou None (use o simulado)."""
    if not is_configured():
        return None
    payload = {
        "model": os.environ.get("GROQ_MODEL", DEFAULT_MODEL),
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    headers = {"Authorization": f"Bearer {os.environ['GROQ_API_KEY']}"}
    try:
        response = httpx.post(GROQ_URL, json=payload, headers=headers, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
    except (httpx.HTTPError, KeyError, IndexError, ValueError):
        return None
    return _extract_json(content)
