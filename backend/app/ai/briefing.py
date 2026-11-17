"""Leitura do briefing: o gerente cola o texto do projeto e o sistema PROPÕE os papéis.
O gerente sempre pode editar a proposta antes de montar os squads."""
import re

from ..config import SKILLS, SKILL_LABELS
from . import llm

MIN_ROLES, MAX_ROLES = 3, 6

# Palavras que sugerem cada habilidade (versão simulada, sem IA).
KEYWORDS = {
    "frontend": [r"front", r"interface", r"\btelas?\b", r"\bsite\b", r"react", r"\bweb\b", r"página", r"responsiv"],
    "backend": [r"back", r"\bapi\b", r"servidor", r"integra", r"regras? de negócio", r"autentica", r"login"],
    "banco_dados": [r"banco de dados", r"\bsql\b", r"modelagem", r"postgres", r"armazen", r"relatórios?"],
    "ux_ui": [r"\bux\b", r"\bui\b", r"design", r"protótipo", r"usabilidade", r"figma", r"identidade visual"],
    "gestao": [r"gest", r"prazo", r"cliente", r"cronograma", r"escopo", r"scrum", r"entrega"],
    "qa": [r"teste", r"qualidade", r"\bqa\b", r"\bbugs?\b", r"homolog", r"segurança"],
    "dados_ia": [r"\bia\b", r"inteligência artificial", r"machine learning", r"dashboard", r"análise de dados", r"preditiv", r"recomenda"],
    "devops": [r"deploy", r"infra", r"cloud", r"nuvem", r"docker", r"ci/cd", r"hospedagem", r"disponibilidade"],
}
DEFAULT_HOURS = {"gestao": 5, "qa": 5, "ux_ui": 6}


def _duration(text: str) -> int:
    lowered = text.lower()
    weeks = re.search(r"(\d+)\s*semanas?", lowered)
    if weeks:
        return max(1, min(26, int(weeks.group(1))))
    months = re.search(r"(\d+)\s*m[eê]s(?:es)?", lowered)
    if months:
        return max(1, min(26, int(months.group(1)) * 4))
    return 6


def _role(skill, min_level, hours, critical=False, reason=""):
    return {
        "skill": skill,
        "skill_label": SKILL_LABELS[skill],
        "min_level": int(min_level),
        "hours_per_week": float(hours),
        "critical": bool(critical),
        "reason": reason,
    }


def parse_simulated(text: str) -> dict:
    lowered = text.lower()
    hits = {
        skill: sum(len(re.findall(p, lowered)) for p in patterns)
        for skill, patterns in KEYWORDS.items()
    }
    chosen = [s for s, n in sorted(hits.items(), key=lambda kv: -kv[1]) if n > 0][:MAX_ROLES]
    for filler in ("frontend", "backend", "gestao"):  # garante o mínimo de papéis
        if len(chosen) >= MIN_ROLES:
            break
        if filler not in chosen:
            chosen.append(filler)
    top = chosen[0]
    roles = []
    for skill in chosen:
        n = hits[skill]
        level = 3 if n >= 3 else 2
        roles.append(
            _role(
                skill, level, DEFAULT_HOURS.get(skill, 8), critical=(skill == top and n >= 2),
                reason=f"O briefing cita {SKILL_LABELS[skill]} {n}x." if n else "Papel básico de qualquer projeto.",
            )
        )
    return {"name": "", "duration_weeks": _duration(text), "roles": roles}


SYSTEM_PROMPT = f"""Você ajuda a montar equipes de projetos de software em uma empresa júnior.
Leia o briefing e proponha um nome curto para o projeto (até 5 palavras) e de 3 a 6 papéis.
Responda SOMENTE com JSON no formato:
{{"name": "<nome curto do projeto>", "duration_weeks": <inteiro>, "roles": [{{"skill": <uma de {list(SKILLS)}>,
"min_level": <1 a 4>, "hours_per_week": <número de 2 a 12>, "critical": <true/false>,
"reason": "<uma frase curta em português>"}}]}}
Marque como critical no máximo 1 papel: aquele sem o qual o projeto trava."""


def _validate(data):
    """Aceita a resposta da IA só se estiver no formato certo."""
    try:
        roles = []
        seen = set()
        for r in data["roles"]:
            skill = r["skill"]
            if skill not in SKILLS or skill in seen:
                continue
            seen.add(skill)
            roles.append(
                _role(
                    skill,
                    min(4, max(1, int(r["min_level"]))),
                    min(12, max(2, float(r["hours_per_week"]))),
                    bool(r.get("critical", False)),
                    str(r.get("reason", ""))[:160],
                )
            )
        if not MIN_ROLES <= len(roles) <= MAX_ROLES:
            return None
        if sum(r["critical"] for r in roles) > 1:
            first = True
            for r in roles:
                if r["critical"] and not first:
                    r["critical"] = False
                first = first and not r["critical"]
        weeks = min(26, max(1, int(data.get("duration_weeks", 6))))
        name = " ".join(str(data.get("name", "")).split())[:60]
        return {"name": name, "duration_weeks": weeks, "roles": roles}
    except (KeyError, TypeError, ValueError):
        return None


def parse_briefing(text: str) -> dict:
    """Devolve {duration_weeks, roles, mode}. Tenta a IA real; cai no simulado."""
    real = llm.ask_json(SYSTEM_PROMPT, text[:4000])
    parsed = _validate(real) if real else None
    result = parsed or parse_simulated(text)
    result["mode"] = llm.mode_label(parsed is not None)
    return result
