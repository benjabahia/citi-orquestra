"""Substituições ("e se?"): trocar ou tirar uma pessoa e ver o impacto.

O gerente clica numa pessoa e recebe a lista de substitutos ordenada pelo
impacto previsto (decisão Q10). O sistema AVISA quando a troca piora algo,
mas não bloqueia: quem decide é o gerente.
"""
from dataclasses import dataclass

from .config import DEFAULT_CONFIG, Config
from .models import Metrics, Project, Squad
from .scoring import capacity_of, evaluate, profile_objective


@dataclass(frozen=True)
class Substitute:
    member_id: str
    name: str
    metrics: Metrics
    delta_entrega: float
    delta_crescimento: float
    delta_risco: float
    objective_delta: float
    new_issues: tuple        # problemas que passam a existir com a troca
    resolved_issues: tuple   # problemas que a troca resolve


def _squad_from(project, profile, assignments, members, availability, cfg, notes=()):
    metrics = evaluate(project, tuple(assignments), members, availability, cfg)
    return Squad(
        profile=profile,
        assignments=tuple(assignments),
        metrics=metrics,
        objective=round(profile_objective(profile, metrics, cfg), 2),
        notes=tuple(notes),
    )


def remove_member(project, squad, role_index, members, availability, cfg: Config = DEFAULT_CONFIG) -> Squad:
    """Deixa o papel vago (ex.: a pessoa saiu do projeto)."""
    assignments = list(squad.assignments)
    assignments[role_index] = None
    return _squad_from(project, squad.profile, assignments, members, availability, cfg, squad.notes)


def apply_substitution(
    project, squad, role_index, new_member_id, members, availability, cfg: Config = DEFAULT_CONFIG
) -> Squad:
    """Coloca `new_member_id` no papel. Se ele já está em outro papel da squad,
    os dois trocam de lugar."""
    assignments = list(squad.assignments)
    old = assignments[role_index]
    if new_member_id in assignments:
        assignments[assignments.index(new_member_id)] = old
    assignments[role_index] = new_member_id
    return _squad_from(project, squad.profile, assignments, members, availability, cfg, squad.notes)


def rank_substitutes(
    project: Project,
    squad: Squad,
    role_index: int,
    members: dict,
    availability: dict,
    cfg: Config = DEFAULT_CONFIG,
    min_skill_level: int = 1,
) -> list:
    """Candidatos de fora da squad para o papel `role_index`, do melhor ao pior
    para o TIPO de squad (segura, evolutiva ou balanceada).

    Só entram candidatos com pelo menos `min_skill_level` (padrão: iniciante)
    na habilidade do papel: sugerir quem nunca viu o assunto não ajuda ninguém.
    """
    base = squad.metrics
    base_keys = {f.key(): f.message for f in base.factors}
    base_obj = profile_objective(squad.profile, base, cfg)
    in_squad = {a for a in squad.assignments if a is not None}

    ranked = []
    for mid in sorted(members):
        if mid in in_squad:
            continue
        if capacity_of(availability, mid, project.duration_weeks) <= 0:
            continue
        if members[mid].level(project.roles[role_index].skill) < min_skill_level:
            continue
        assignments = list(squad.assignments)
        assignments[role_index] = mid
        metrics = evaluate(project, tuple(assignments), members, availability, cfg)
        new_keys = {f.key(): f.message for f in metrics.factors}
        ranked.append(
            Substitute(
                member_id=mid,
                name=members[mid].name,
                metrics=metrics,
                delta_entrega=round(metrics.entrega - base.entrega, 1),
                delta_crescimento=round(metrics.crescimento - base.crescimento, 1),
                delta_risco=round(metrics.risco - base.risco, 1),
                objective_delta=round(profile_objective(squad.profile, metrics, cfg) - base_obj, 2),
                new_issues=tuple(m for k, m in new_keys.items() if k not in base_keys),
                resolved_issues=tuple(m for k, m in base_keys.items() if k not in new_keys),
            )
        )
    ranked.sort(key=lambda s: (-s.objective_delta, s.member_id))
    return ranked
