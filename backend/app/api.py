"""API do CITi Orquestra (FastAPI).

Toda a lógica fica no motor em Python; a API só recebe pedidos, chama o motor
e devolve JSON. O site (React) apenas desenha o que a API devolve.

Rodar localmente (na pasta backend):
    uvicorn app.api:app --reload
Documentação interativa automática: http://127.0.0.1:8000/docs
"""
from functools import lru_cache
from typing import Optional

import re
import unicodedata

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .allocator import build_squads
from .config import DEFAULT_CONFIG, LEVEL_LABELS, PROFILES, SKILL_LABELS
from .ai import briefing as briefing_ai
from .ai import llm
from .ai import profile_chat
from .data import default_availability, load_scenario
from .models import Member, Project, Role
from .recommend import recommend_all
from .serializers import (
    member_dict,
    project_dict,
    squad_dict,
    substitute_dict,
)
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
    """As 3 squads de um projeto. O resultado é sempre o mesmo, então guardamos."""
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


class CustomProjectRequest(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    description: str = Field("", max_length=500)
    duration_weeks: int = Field(ge=1, le=26)
    roles: list[RoleIn] = Field(min_length=3, max_length=6)
    extra_members: list[MemberProfileIn] = []


def _slug(text: str) -> str:
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", plain.lower()).strip("-")[:40] or "projeto"


def _custom_context(req: CustomProjectRequest):
    """Projeto novo (vindo do briefing): devolve (projeto, membros, disponibilidade)."""
    for r in req.roles:
        if r.skill not in SKILL_LABELS:
            raise HTTPException(422, f"Habilidade '{r.skill}' não existe.")
    members = dict(MEMBERS)
    extras = []
    for i, m in enumerate(req.extra_members):
        if any(sk not in SKILL_LABELS or not 0 <= v <= 4 for sk, v in m.skills.items()):
            raise HTTPException(422, "Perfil com habilidade ou nível inválido.")
        member = Member(f"novo{i + 1}", m.name, m.months_in_citi, dict(m.skills), tuple(m.learning_goals))
        members[member.id] = member
        extras.append(member.id)
    top = next((i for i, r in enumerate(req.roles) if r.critical), None)
    roles = tuple(
        Role(r.skill, r.min_level, r.hours_per_week,
             weight=1.5 if i == top else 1.0, critical=(i == top))
        for i, r in enumerate(req.roles)
    )
    project = Project(f"custom-{_slug(req.name)}", req.name, req.description, req.duration_weeks, roles)
    return project, members, default_availability(project, extras)


def _context(project_id: str, custom: Optional[CustomProjectRequest]):
    """Onde buscar projeto, membros e disponibilidade: exemplo pronto ou projeto novo."""
    if custom is not None:
        return _custom_context(custom)
    return _project_or_404(project_id), MEMBERS, SCENARIO.availability[project_id]


class SquadState(BaseModel):
    """A squad como está na tela agora: qual perfil e quem ocupa cada papel."""

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
    """Resposta das 3 squads + a recomendação para cada prioridade (prazo, formar, equilíbrio)."""
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


@app.post("/api/projects/{project_id}/apply")
def apply(project_id: str, req: ApplyRequest):
    """Aplica a troca (ou tira a pessoa) e devolve a squad recalculada."""
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
    """Monta as 3 squads para um projeto novo (papéis vindos do briefing, já editados)."""
    project, members, availability = _custom_context(req)
    return _squads_payload(project, build_squads(project, members, availability, CFG), members)


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


# ---------------------------------------------------------------------------
# Site (React) servido pelo mesmo servidor: um serviço, um link.
# ---------------------------------------------------------------------------
from pathlib import Path  # noqa: E402

from fastapi.staticfiles import StaticFiles  # noqa: E402

FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="site")
