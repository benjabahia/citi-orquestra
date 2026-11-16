"""API do CITi Orquestra (FastAPI).

Toda a lógica fica no motor em Python; a API só recebe pedidos, chama o motor
e devolve JSON. O site (React) apenas desenha o que a API devolve.

Rodar localmente (na pasta backend):
    uvicorn app.api:app --reload
Documentação interativa automática: http://127.0.0.1:8000/docs
"""
from functools import lru_cache
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .allocator import build_squads
from .config import DEFAULT_CONFIG, LEVEL_LABELS, PROFILES, SKILL_LABELS
from .data import load_scenario
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


class SquadState(BaseModel):
    """A squad como está na tela agora: qual perfil e quem ocupa cada papel."""

    profile: str
    assignments: list[Optional[str]] = Field(description="id do membro (ou null) por papel")


class WhatIfRequest(SquadState):
    role_index: int


class ApplyRequest(WhatIfRequest):
    member_id: Optional[str] = Field(None, description="null = deixar o papel vago")


def _rebuild(project, state: SquadState):
    if state.profile not in PROFILES:
        raise HTTPException(422, "Perfil inválido.")
    if len(state.assignments) != len(project.roles):
        raise HTTPException(422, "Quantidade de papéis não bate com o projeto.")
    for mid in state.assignments:
        if mid is not None and mid not in MEMBERS:
            raise HTTPException(422, f"Membro '{mid}' não existe.")
    return _squad_from(
        project, state.profile, state.assignments, MEMBERS,
        SCENARIO.availability[project.id], CFG,
    )


def _check_role(project, role_index: int):
    if not 0 <= role_index < len(project.roles):
        raise HTTPException(422, "Papel inexistente.")


@app.get("/api/health")
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
    built = _squads_for(project_id)
    return {
        "project": project_dict(project),
        "squads": {p: squad_dict(built[p], project, MEMBERS, CFG) for p in PROFILES},
    }


@app.post("/api/projects/{project_id}/whatif")
def whatif(project_id: str, req: WhatIfRequest):
    """Lista de substitutos para um papel, ordenada pelo impacto."""
    project = _project_or_404(project_id)
    _check_role(project, req.role_index)
    squad = _rebuild(project, req)
    subs = rank_substitutes(
        project, squad, req.role_index, MEMBERS, SCENARIO.availability[project_id], CFG
    )
    return {
        "current": squad_dict(squad, project, MEMBERS, CFG),
        "substitutes": [substitute_dict(s) for s in subs],
    }


@app.post("/api/projects/{project_id}/apply")
def apply(project_id: str, req: ApplyRequest):
    """Aplica a troca (ou tira a pessoa) e devolve a squad recalculada."""
    project = _project_or_404(project_id)
    _check_role(project, req.role_index)
    squad = _rebuild(project, req)
    availability = SCENARIO.availability[project_id]
    if req.member_id is None:
        new = remove_member(project, squad, req.role_index, MEMBERS, availability, CFG)
    else:
        if req.member_id not in MEMBERS:
            raise HTTPException(422, f"Membro '{req.member_id}' não existe.")
        new = apply_substitution(
            project, squad, req.role_index, req.member_id, MEMBERS, availability, CFG
        )
    return {"squad": squad_dict(new, project, MEMBERS, CFG)}
