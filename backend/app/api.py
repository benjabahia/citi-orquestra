"""API do CITi Orquestra (FastAPI).

Toda a lógica fica no motor em Python; a API só recebe pedidos, chama o motor
e devolve JSON. O site (React) apenas desenha o que a API devolve.

Rodar localmente (na pasta backend):
    uvicorn app.api:app --reload
Documentação interativa automática: http://127.0.0.1:8000/docs
"""
from functools import lru_cache
from typing import Literal, Optional

import re
import unicodedata

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .allocator import build_squads
from .config import DEFAULT_CONFIG, LEVEL_LABELS, PROFILES, SKILL_LABELS
from .ai import briefing as briefing_ai
from .ai import interview
from .ai import llm
from .ai import profile_chat
from .data import default_availability, load_scenario
from .members_csv import parse_members_csv, template_csv
from .models import Availability, Member, Project, Role
from .recommend import recommend_all
from .serializers import (
    member_dict,
    project_dict,
    squad_dict,
    substitute_dict,
)
from .stress import stress_test, weakest_sentence
from .summary import build_summary
from .whatif import _squad_from, apply_substitution, rank_substitutes, remove_member

CFG = DEFAULT_CONFIG

app = FastAPI(
    title="CITi Orquestra",
    description="Monta 3 squads por projeto e mostra o impacto de cada troca.",
    version="0.1.0",
)

SCENARIO = load_scenario()
MEMBERS = SCENARIO.members_by_id()


@lru_cache(maxsize=None)
def _squads_for(project_id: str) -> dict:
    """Os 3 squads de um projeto. O resultado é sempre o mesmo, então guardamos."""
    project = SCENARIO.project(project_id)
    return build_squads(project, MEMBERS, SCENARIO.availability[project_id], CFG)


def _project_or_404(project_id: str):
    try:
        return SCENARIO.project(project_id)
    except (KeyError, ValueError, StopIteration):
        raise HTTPException(404, f"Projeto '{project_id}' não existe.")


class RoleIn(BaseModel):
    skill: str
    min_level: int = Field(ge=1, le=4)
    hours_per_week: float = Field(ge=1, le=20)
    critical: bool = False


class MemberProfileIn(BaseModel):
    name: str
    months_in_citi: int = Field(ge=0, le=120)
    skills: dict[str, int]
    learning_goals: list[str] = []
    # Disponibilidade declarada (perfis e planilhas antigos não têm: vale 8 h e 0 semanas).
    weekly_hours: float = Field(8.0, ge=0, le=40)
    unavailable_weeks: int = Field(0, ge=0, le=12)


class AvailabilityIn(BaseModel):
    """Ajuste do gerente para uma pessoa: horas livres por semana e semanas fora."""

    weekly_hours: float = Field(ge=0, le=40)
    unavailable_weeks: int = Field(0, ge=0, le=12)


class CustomProjectRequest(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    description: str = Field("", max_length=500)
    duration_weeks: int = Field(ge=1, le=26)
    roles: list[RoleIn] = Field(min_length=3, max_length=6)
    extra_members: list[MemberProfileIn] = []
    replace_members: Optional[list[MemberProfileIn]] = Field(
        None, min_length=3, max_length=200,
        description="planilha do gerente: quando preenchida, substitui os 24 membros de exemplo",
    )
    availability: dict[str, AvailabilityIn] = Field(
        default_factory=dict,
        description="ajuste do gerente: id do membro -> horas livres e semanas fora (vence o declarado)",
    )


def _slug(text: str) -> str:
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", plain.lower()).strip("-")[:40] or "projeto"


def _custom_context(req: CustomProjectRequest):
    """Projeto novo (vindo do briefing): devolve (projeto, membros, disponibilidade).

    A disponibilidade vem do que foi INFORMADO: planilha ou perfil (`weekly_hours`,
    `unavailable_weeks`) e, por cima, o ajuste do gerente (`availability`). Como
    trocar, aplicar e o teste de estresse chamam esta mesma função com o mesmo corpo,
    os números ficam iguais em todas as telas.
    """
    for r in req.roles:
        if r.skill not in SKILL_LABELS:
            raise HTTPException(422, f"Habilidade '{r.skill}' não existe.")
    sheet = req.replace_members is not None
    members = {} if sheet else dict(MEMBERS)
    extras, declared = [], {}
    news = [("imp", m) for m in (req.replace_members or [])] + [("novo", m) for m in req.extra_members]
    counters = {"imp": 0, "novo": 0}
    for prefix, m in news:
        if any(sk not in SKILL_LABELS or not 0 <= v <= 4 for sk, v in m.skills.items()):
            raise HTTPException(422, "Perfil com habilidade ou nível inválido.")
        counters[prefix] += 1
        member = Member(f"{prefix}{counters[prefix]}", m.name, m.months_in_citi, dict(m.skills), tuple(m.learning_goals))
        members[member.id] = member
        extras.append(member.id)
        declared[member.id] = Availability(m.weekly_hours, m.unavailable_weeks)
    top = next((i for i, r in enumerate(req.roles) if r.critical), None)
    roles = tuple(
        Role(r.skill, r.min_level, r.hours_per_week,
             weight=1.5 if i == top else 1.0, critical=(i == top))
        for i, r in enumerate(req.roles)
    )
    project = Project(f"custom-{_slug(req.name)}", req.name, req.description, req.duration_weeks, roles)
    availability = default_availability(project, extras, only_extras=sheet, declared=declared)
    for member_id, adj in req.availability.items():
        if member_id not in members:
            raise HTTPException(422, f"Ajuste de horas para um membro que não está no projeto ('{member_id}').")
        availability[member_id] = Availability(adj.weekly_hours, adj.unavailable_weeks)
    return project, members, availability


def _context(project_id: str, custom: Optional[CustomProjectRequest]):
    """Onde buscar projeto, membros e disponibilidade: exemplo pronto ou projeto novo."""
    if custom is not None:
        return _custom_context(custom)
    return _project_or_404(project_id), MEMBERS, SCENARIO.availability[project_id]


class SquadState(BaseModel):
    """O squad como está na tela agora: qual perfil e quem ocupa cada papel."""

    profile: str
    assignments: list[Optional[str]] = Field(description="id do membro (ou null) por papel")


class WhatIfRequest(SquadState):
    role_index: int
    custom: Optional[CustomProjectRequest] = Field(
        None, description="preencher quando o projeto veio de um briefing (não é um exemplo pronto)"
    )


class ApplyRequest(WhatIfRequest):
    member_id: Optional[str] = Field(None, description="null = deixar o papel vago")


def _rebuild(project, state: SquadState, members, availability):
    if state.profile not in PROFILES:
        raise HTTPException(422, "Perfil inválido.")
    if len(state.assignments) != len(project.roles):
        raise HTTPException(422, "Quantidade de papéis não bate com o projeto.")
    for mid in state.assignments:
        if mid is not None and mid not in members:
            raise HTTPException(422, f"Membro '{mid}' não existe.")
    return _squad_from(project, state.profile, state.assignments, members, availability, CFG)


def _squads_payload(project, built, members):
    """Resposta dos 3 squads + a recomendação para cada prioridade (prazo, formar, equilíbrio)."""
    squads = {p: squad_dict(built[p], project, members, CFG) for p in PROFILES}
    metrics = {p: squads[p]["metrics"] for p in PROFILES}
    return {"project": project_dict(project), "squads": squads, "recommendations": recommend_all(metrics)}


def _check_role(project, role_index: int):
    if not 0 <= role_index < len(project.roles):
        raise HTTPException(422, "Papel inexistente.")


@app.api_route("/api/health", methods=["GET", "HEAD"])
def health():
    return {"status": "ok"}


@app.get("/api/meta")
def meta():
    return {
        "skills": SKILL_LABELS,
        "levels": LEVEL_LABELS,
        "profiles": list(PROFILES),
        "novato_months": CFG.novato_months,
    }


@app.get("/api/projects")
def projects():
    return [project_dict(p) for p in SCENARIO.projects]


@app.get("/api/members")
def members():
    return [member_dict(m, CFG) for m in SCENARIO.members]


@app.get("/api/projects/{project_id}/squads")
def squads(project_id: str):
    project = _project_or_404(project_id)
    return _squads_payload(project, _squads_for(project_id), MEMBERS)


@app.post("/api/projects/{project_id}/whatif")
def whatif(project_id: str, req: WhatIfRequest):
    """Lista de substitutos para um papel, ordenada pelo impacto."""
    project, members, availability = _context(project_id, req.custom)
    _check_role(project, req.role_index)
    squad = _rebuild(project, req, members, availability)
    skill = project.roles[req.role_index].skill
    subs = rank_substitutes(project, squad, req.role_index, members, availability, CFG)
    return {
        "current": squad_dict(squad, project, members, CFG),
        "substitutes": [substitute_dict(sub, members[sub.member_id], skill, CFG) for sub in subs],
    }


class StressRequest(SquadState):
    custom: Optional[CustomProjectRequest] = Field(
        None, description="preencher quando o projeto veio de um briefing (não é um exemplo pronto)"
    )


@app.post("/api/projects/{project_id}/stress")
def stress(project_id: str, req: StressRequest):
    """Teste de estresse: o que acontece com o squad se cada pessoa sair (pior caso primeiro)."""
    project, members, availability = _context(project_id, req.custom)
    squad = _rebuild(project, req, members, availability)
    rows = stress_test(project, squad, members, availability, CFG)
    return {"results": rows, "weakest_sentence": weakest_sentence(rows)}


class SummaryRequest(StressRequest):
    """Mesmo corpo do teste de estresse, mais o id do projeto (já que aqui ele não vem na URL)."""

    project_id: str = Field("custom", max_length=80)
    include_weakest: bool = Field(
        False, description="true quando o teste de estresse já foi feito: inclui o ponto mais frágil"
    )


@app.post("/api/export/summary")
def export_summary(req: SummaryRequest):
    """Texto curto do squad atual para colar no chat. Pedido inválido: 422."""
    if req.custom is None:
        try:
            SCENARIO.project(req.project_id)
        except KeyError:
            raise HTTPException(422, f"Projeto '{req.project_id}' não existe.")
    project, members, availability = _context(req.project_id, req.custom)
    squad = _rebuild(project, req, members, availability)
    weakest = None
    if req.include_weakest:
        weakest = weakest_sentence(stress_test(project, squad, members, availability, CFG))
    text = build_summary(project, squad, members, CFG, custom=req.custom is not None, weakest=weakest)
    return {"text": text}


@app.post("/api/projects/{project_id}/apply")
def apply(project_id: str, req: ApplyRequest):
    """Aplica a troca (ou tira a pessoa) e devolve o squad recalculado."""
    project, members, availability = _context(project_id, req.custom)
    _check_role(project, req.role_index)
    squad = _rebuild(project, req, members, availability)
    if req.member_id is None:
        new = remove_member(project, squad, req.role_index, members, availability, CFG)
    else:
        if req.member_id not in members:
            raise HTTPException(422, f"Membro '{req.member_id}' não existe.")
        new = apply_substitution(project, squad, req.role_index, req.member_id, members, availability, CFG)
    return {"squad": squad_dict(new, project, members, CFG)}


# ---------------------------------------------------------------------------
# IA (real ou simulada): briefing e chat de perfil
# ---------------------------------------------------------------------------
class BriefingRequest(BaseModel):
    text: str = Field(min_length=10, max_length=6000)


@app.get("/api/ai/status")
def ai_status():
    """Informa se a IA real está ligada (o site mostra um aviso do modo)."""
    return {"mode": llm.mode_label(llm.is_configured())}


@app.post("/api/briefing/parse")
def parse_briefing(req: BriefingRequest):
    return briefing_ai.parse_briefing(req.text)


@app.post("/api/squads/build")
def build_custom(req: CustomProjectRequest):
    """Monta os 3 squads para um projeto novo (papéis vindos do briefing, já editados)."""
    project, members, availability = _custom_context(req)
    return _squads_payload(project, build_squads(project, members, availability, CFG), members)


def _source(member_id: str) -> str:
    return "planilha" if member_id.startswith("imp") else "perfil" if member_id.startswith("novo") else "exemplo"


@app.post("/api/squads/team")
def custom_team(req: CustomProjectRequest):
    """Quem está em jogo num projeto por briefing e com quantas horas (para a tabela de ajuste).

    `weekly_hours` e `unavailable_weeks` já incluem o ajuste do gerente, se houver.
    `available_hours` é a média por semana ao longo do projeto (descontadas as semanas fora).
    """
    project, members, availability = _custom_context(req)
    rows = []
    for member_id in sorted(members, key=lambda i: (_source(i) == "exemplo", i)):
        a = availability.get(member_id, Availability(0.0))
        rows.append({
            "id": member_id,
            "name": members[member_id].name,
            "source": _source(member_id),
            "is_novato": members[member_id].is_novato(CFG.novato_months),
            "weekly_hours": a.weekly_hours,
            "unavailable_weeks": a.unavailable_weeks,
            "available_hours": round(a.effective_hours(project.duration_weeks), 2),
        })
    return {"members": rows, "duration_weeks": project.duration_weeks}


class ImportRequest(BaseModel):
    text: str = Field(max_length=300_000)


@app.post("/api/members/import")
def import_members(req: ImportRequest):
    """Valida a planilha (CSV) de membros. Não guarda nada: o site guarda no navegador."""
    return parse_members_csv(req.text)


@app.get("/api/members/template")
def members_template():
    return {"csv": template_csv()}


@app.get("/api/profile/questions")
def profile_questions():
    return {"questions": profile_chat.QUESTIONS}


class ProfileRequest(BaseModel):
    name: str
    answers: dict


@app.post("/api/profile/interpret")
def profile_interpret(req: ProfileRequest):
    """Devolve o perfil calculado pelas respostas, para a pessoa CONFIRMAR antes de salvar."""
    try:
        profile = profile_chat.build_profile(req.name, req.answers)
    except profile_chat.ProfileError as error:
        raise HTTPException(422, str(error))
    hints = profile_chat.interpret_open_text(req.answers.get("open", ""))
    missing = [s for s in hints["skills"] if s not in profile["skills"]]
    return {
        "profile": profile,
        "suggested_skills": [{"skill": s, "skill_label": SKILL_LABELS[s]} for s in missing],
        "summary": hints["summary"],
        "mode": hints["mode"],
    }


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    text: str = Field(min_length=1, max_length=interview.MAX_ANSWER_CHARS)


class InterviewRequest(BaseModel):
    """Entrevista com IA: o nome fica no servidor; só os meses e a conversa vão para a IA."""

    name: str = Field(min_length=1, max_length=60)
    months_in_citi: int
    history: list[ChatMessage] = Field(min_length=1, max_length=interview.MAX_HISTORY)


class CoherenceRequest(BaseModel):
    months_in_citi: int
    skills: dict[str, int]
    history: list[ChatMessage] = Field(min_length=1, max_length=interview.MAX_HISTORY)


def _interview_inputs(months: int, history: list[ChatMessage]):
    if months not in {m["months"] for m in profile_chat.MONTH_CHOICES}:
        raise HTTPException(422, "Escolha há quanto tempo você está no CITi.")
    try:
        return interview.validate_history([m.model_dump() for m in history])
    except interview.InterviewError as error:
        raise HTTPException(422, str(error))


def _ask(job):
    """422 para pedido inválido; 503 quando a IA está desligada ou respondeu mal (a tela cai no formulário)."""
    try:
        return job()
    except interview.InterviewError as error:
        raise HTTPException(422, str(error))
    except interview.AIUnavailable as error:
        raise HTTPException(503, str(error))


@app.post("/api/profile/interview/next")
def interview_next(req: InterviewRequest):
    """Próxima pergunta da entrevista (no máximo 3) ou done=true."""
    history = _interview_inputs(req.months_in_citi, req.history)
    return {**_ask(lambda: interview.next_question(req.months_in_citi, history)), "mode": "ia_real"}


@app.post("/api/profile/interview/propose")
def interview_propose(req: InterviewRequest):
    """Rascunho de níveis (já validado) + avisos de coerência. A pessoa revisa antes de salvar."""
    history = _interview_inputs(req.months_in_citi, req.history)
    return {**_ask(lambda: interview.propose_draft(req.months_in_citi, history)), "mode": "ia_real"}


@app.post("/api/profile/interview/check")
def interview_check(req: CoherenceRequest):
    """Refaz os avisos "Vale revisar" com os níveis que a pessoa escolheu (só regras, sem IA)."""
    history = _interview_inputs(req.months_in_citi, req.history)
    if any(s not in SKILL_LABELS or not 0 <= v <= 4 for s, v in req.skills.items()):
        raise HTTPException(422, "Habilidade ou nível inválido.")
    text = interview.person_text(history)
    return {"warnings": interview.check_coherence(req.skills, req.months_in_citi, text, CFG)}


# ---------------------------------------------------------------------------
# Site (React) servido pelo mesmo servidor: um serviço, um link.
# ---------------------------------------------------------------------------
from pathlib import Path  # noqa: E402

from fastapi.staticfiles import StaticFiles  # noqa: E402

FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="site")
