"""Chat guiado do perfil do membro (decisões Q2 a Q5).

Perguntas curtas, com respostas de âncora concreta ("já entreguei sozinho em
projeto real") em vez de "nota de 0 a 4". Os NÍVEIS são calculados aqui,
pelas respostas de âncora: a IA nunca decide o nível de ninguém. Ela só lê a
pergunta aberta e SUGERE habilidades que a pessoa pode confirmar ou ignorar.
"""
import re

from ..config import SKILLS, SKILL_LABELS
from . import llm

ANCHORS = [
    "Nunca trabalhei com isso",
    "Fiz cursos ou exercícios, sem entregar nada real",
    "Já entreguei algo pequeno, com ajuda de alguém",
    "Já entreguei sozinho(a) em um projeto real",
    "Já resolvi problemas difíceis e ensinei outras pessoas",
]

MONTH_CHOICES = [
    {"label": "Menos de 3 meses", "months": 2},
    {"label": "De 3 a 6 meses", "months": 4},
    {"label": "De 6 meses a 1 ano", "months": 9},
    {"label": "Mais de 1 ano", "months": 18},
    {"label": "Mais de 2 anos", "months": 30},
]

MAX_GOALS = 2

# Disponibilidade declarada pela pessoa (perfis antigos sem esses campos usam o padrão).
DEFAULT_WEEKLY_HOURS = 8.0
DEFAULT_UNAVAILABLE_WEEKS = 0
MAX_WEEKLY_HOURS = 40
MAX_UNAVAILABLE_WEEKS = 12
HOUR_SUGGESTIONS = [2, 4, 6, 8, 10, 12]
SKILL_OPTIONS = [{"value": s, "label": SKILL_LABELS[s]} for s in SKILLS]

QUESTIONS = [
    {
        "id": "areas",
        "type": "multi",
        "text": "Em quais áreas você já colocou a mão na massa?",
        "options": SKILL_OPTIONS,
    },
    {
        "id": "levels",
        "type": "levels",
        "text": "Para cada área, qual frase descreve melhor você hoje?",
        "options": [{"value": i, "label": a} for i, a in enumerate(ANCHORS)],
    },
    {
        "id": "months",
        "type": "choice",
        "text": "Há quanto tempo você está no CITi?",
        "options": [{"value": m["months"], "label": m["label"]} for m in MONTH_CHOICES],
    },
    {
        "id": "goals",
        "type": "multi",
        "max": MAX_GOALS,
        "text": f"O que você mais quer aprender neste ciclo? (até {MAX_GOALS})",
        "options": SKILL_OPTIONS,
    },
    {
        "id": "hours",
        "type": "number",
        "text": "Quantas horas por semana você consegue dedicar a projetos neste ciclo?",
        "min": 0,
        "max": MAX_WEEKLY_HOURS,
        "step": 0.5,
        "unit": "h por semana",
        "suggestions": HOUR_SUGGESTIONS,
        "default": DEFAULT_WEEKLY_HOURS,
    },
    {
        "id": "away",
        "type": "number",
        "text": "Em quantas semanas dos próximos projetos você estará fora?",
        "min": 0,
        "max": MAX_UNAVAILABLE_WEEKS,
        "step": 1,
        "unit": "semana(s)",
        "suggestions": [],
        "default": DEFAULT_UNAVAILABLE_WEEKS,
    },
    {
        "id": "open",
        "type": "open",
        "text": "Conte, em poucas linhas, algo que você fez e te deixou orgulhoso(a).",
        "optional": True,
    },
]

# Palavras do texto livre que sugerem uma habilidade (versão simulada).
SUGGEST_KEYWORDS = {
    "frontend": [r"front", r"interface", r"\bsite\b", r"react", r"página", r"\bhtml\b", r"\bcss\b"],
    "backend": [r"back", r"\bapi\b", r"servidor", r"flask", r"django", r"fastapi", r"node"],
    "banco_dados": [r"banco de dados", r"\bsql\b", r"postgres", r"mysql", r"modelagem"],
    "ux_ui": [r"\bux\b", r"\bui\b", r"design", r"figma", r"protótipo"],
    "gestao": [r"gerenci", r"liderei", r"organizei", r"\bscrum\b", r"coordenei", r"cronograma"],
    "qa": [r"teste", r"\bqa\b", r"\bbugs?\b", r"qualidade"],
    "dados_ia": [r"dados", r"\bia\b", r"machine learning", r"python", r"análise", r"dashboard"],
    "devops": [r"deploy", r"docker", r"\bci\b", r"servidor linux", r"nuvem", r"cloud", r"\baws\b"],
}


def suggest_simulated(text: str) -> list:
    lowered = text.lower()
    return [
        s for s, patterns in SUGGEST_KEYWORDS.items()
        if any(re.search(p, lowered) for p in patterns)
    ]


SYSTEM_PROMPT = f"""Você lê um texto curto em que um membro de uma empresa júnior de tecnologia
conta algo de que se orgulha. Diga quais habilidades o texto sugere, escolhendo SOMENTE entre
{list(SKILLS)}. Responda apenas JSON: {{"skills": [<habilidades>], "summary": "<uma frase em português>"}}.
Não atribua níveis nem faça julgamentos sobre a pessoa."""


def interpret_open_text(text: str) -> dict:
    """Devolve {skills, summary, mode} a partir da resposta aberta."""
    text = (text or "").strip()[:1500]
    if not text:
        return {"skills": [], "summary": "", "mode": llm.mode_label(False)}
    real = llm.ask_json(SYSTEM_PROMPT, text)
    if real and isinstance(real.get("skills"), list):
        skills = [s for s in real["skills"] if s in SKILLS]
        return {"skills": skills, "summary": str(real.get("summary", ""))[:200], "mode": llm.mode_label(True)}
    skills = suggest_simulated(text)
    return {"skills": skills, "summary": "", "mode": llm.mode_label(False)}


class ProfileError(ValueError):
    pass


def build_profile(name: str, answers: dict) -> dict:
    """Transforma as respostas em perfil. Só os níveis de âncora definem o nível."""
    name = (name or "").strip()
    if not name:
        raise ProfileError("Informe seu nome.")
    areas = answers.get("areas") or []
    levels = answers.get("levels") or {}
    goals = answers.get("goals") or []
    months = answers.get("months")
    if any(a not in SKILLS for a in areas) or any(g not in SKILLS for g in goals):
        raise ProfileError("Habilidade desconhecida.")
    if len(goals) > MAX_GOALS:
        raise ProfileError(f"Escolha no máximo {MAX_GOALS} objetivos de aprendizado.")
    if months not in {m["months"] for m in MONTH_CHOICES}:
        raise ProfileError("Escolha há quanto tempo você está no CITi.")
    skills = {}
    for area in areas:
        level = levels.get(area)
        if not isinstance(level, int) or not 0 <= level <= 4:
            raise ProfileError(f"Escolha uma frase para {SKILL_LABELS[area]}.")
        skills[area] = level
    weekly_hours, unavailable_weeks = availability_from(answers)
    return {
        "name": name, "months_in_citi": months, "skills": skills, "learning_goals": list(goals),
        "weekly_hours": weekly_hours, "unavailable_weeks": unavailable_weeks,
    }


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def availability_from(answers: dict):
    """Horas livres por semana (0 a 40) e semanas fora (inteiro de 0 a 12).

    Campo ausente (perfil antigo) = padrão de 8 h e 0 semanas.
    """
    hours = answers.get("weekly_hours")
    weeks = answers.get("unavailable_weeks")
    if hours is None:
        hours = DEFAULT_WEEKLY_HOURS
    elif not _is_number(hours) or not 0 <= hours <= MAX_WEEKLY_HOURS:
        raise ProfileError(f"Informe de 0 a {MAX_WEEKLY_HOURS} horas por semana.")
    if weeks is None:
        weeks = DEFAULT_UNAVAILABLE_WEEKS
    elif not _is_number(weeks) or weeks != int(weeks) or not 0 <= weeks <= MAX_UNAVAILABLE_WEEKS:
        raise ProfileError(f"Informe um número inteiro de 0 a {MAX_UNAVAILABLE_WEEKS} semanas fora.")
    return float(hours), int(weeks)
