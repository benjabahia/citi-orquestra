"""Cálculo dos medidores e atribuição de mentores.

Nada aqui usa IA: são contas simples e explicáveis (decisão Q3 e Q17).
O app pode perguntar "de onde veio esse número?" e a resposta está na lista
de `factors`, que já vem escrita em português.
"""
from collections import Counter

from .config import DEFAULT_CONFIG, LEVEL_LABELS, PROFILE_WEIGHTS, SKILL_LABELS, Config
from .models import (
    Factor,
    MemberLoad,
    Mentorship,
    Metrics,
    Project,
    Role,
)


def _label(skill: str) -> str:
    return SKILL_LABELS.get(skill, skill)


def _plural_niveis(n: int) -> str:
    return f"{n} nível" if n == 1 else f"{n} níveis"


def capacity_of(availability: dict, member_id: str, duration_weeks: int) -> float:
    """Horas por semana que a pessoa realmente tem neste projeto."""
    a = availability.get(member_id)
    return a.effective_hours(duration_weeks) if a else 0.0


def needs_mentor(member, role: Role, cfg: Config = DEFAULT_CONFIG) -> bool:
    """Precisa de mentor quem é novato ou está 2+ níveis abaixo do exigido."""
    gap = role.min_level - member.level(role.skill)
    return member.is_novato(cfg.novato_months) or gap >= 2


def assign_mentors(project, assignments, members, availability, cfg: Config = DEFAULT_CONFIG):
    """Escolhe um mentor da própria squad para cada pessoa que precisa.

    Regras (Q9): mentor tem nível alto NA MESMA habilidade do papel do mentorando,
    atende no máximo 2 pessoas e prefere quem ainda tem horas sobrando.
    """
    filled = [(i, members[mid]) for i, mid in enumerate(assignments) if mid is not None]
    mentees = [(i, m) for i, m in filled if needs_mentor(m, project.roles[i], cfg)]
    mentee_ids = {m.id for _, m in mentees}
    # Quem sabe menos é atendido primeiro; o desempate por id deixa o resultado estável.
    mentees.sort(
        key=lambda im: (
            im[1].level(project.roles[im[0]].skill),
            im[1].months_in_citi,
            im[1].id,
        )
    )
    role_hours = {m.id: project.roles[i].hours_per_week for i, m in filled}
    count = Counter()
    result = []
    for i, mentee in mentees:
        skill = project.roles[i].skill
        candidates = []
        for _, mentor in filled:
            if mentor.id == mentee.id or mentor.id in mentee_ids:
                continue
            if mentor.level(skill) < cfg.mentor_min_level:
                continue
            if count[mentor.id] >= cfg.max_mentees_per_mentor:
                continue
            cap = capacity_of(availability, mentor.id, project.duration_weeks)
            demand_after = role_hours[mentor.id] + cfg.mentoring_hours_per_mentee * (
                count[mentor.id] + 1
            )
            candidates.append((cap >= demand_after, mentor.level(skill), count[mentor.id], mentor.id))
        if not candidates:
            continue
        # Prefere: tem horas sobrando > nível maior > menos mentorandos > id.
        candidates.sort(key=lambda c: (not c[0], -c[1], c[2], c[3]))
        mentor_id = candidates[0][3]
        count[mentor_id] += 1
        result.append(Mentorship(mentor_id=mentor_id, mentee_id=mentee.id, skill=skill))
    return tuple(result)


def evaluate(project: Project, assignments, members, availability, cfg: Config = DEFAULT_CONFIG) -> Metrics:
    """Calcula os 3 medidores (0 a 100) de uma squad.

    - entrega     = cobertura das habilidades x folga de horas, menos o tempo gasto em mentoria
    - crescimento = meta de aprendizado atendida + apoio de mentor
    - risco       = soma de penalidades (cada uma vira um `Factor` explicado)
    """
    roles = project.roles
    if len(assignments) != len(roles):
        raise ValueError("assignments precisa ter um item por papel do projeto")
    ids = [a for a in assignments if a is not None]
    if len(set(ids)) != len(ids):
        raise ValueError("A mesma pessoa não pode ocupar dois papéis")

    mentorships = assign_mentors(project, assignments, members, availability, cfg)
    n_mentees = Counter(m.mentor_id for m in mentorships)
    mentored_ids = {m.mentee_id for m in mentorships}

    factors, loads = [], []
    coverage, hours_factor, growth = [], [], []

    for i, role in enumerate(roles):
        mid = assignments[i]
        skill_label = _label(role.skill)

        if mid is None:
            coverage.append(0.0)
            hours_factor.append(0.0)
            growth.append(0.0)
            factors.append(
                Factor(
                    "lacuna",
                    cfg.risk_lacuna * role.weight,
                    f"Sem cobertura de {skill_label}: o papel (nível {LEVEL_LABELS[role.min_level]}) está vago.",
                    None,
                    role.skill,
                )
            )
            continue

        m = members[mid]
        level = m.level(role.skill)
        mentored = mid in mentored_ids

        # --- Cobertura: com mentor, o nível efetivo sobe 1 ---
        effective_level = level + (cfg.mentor_level_boost if mentored else 0)
        # Na ENTREGA a ajuda do mentor vale menos: novato com mentor ainda rende menos
        # do que um veterano. No RISCO (abaixo) ela conta o nível inteiro.
        delivery_level = level + (cfg.mentor_delivery_boost if mentored else 0)
        cov = 1.0 if role.min_level <= 0 else min(1.0, delivery_level / role.min_level)
        coverage.append(cov)
        gap = max(0, role.min_level - effective_level)
        if gap > 0:
            factors.append(
                Factor(
                    "nivel_abaixo",
                    cfg.risk_per_level_gap * gap * role.weight,
                    f"{m.name} está {_plural_niveis(gap)} abaixo do exigido em {skill_label} "
                    f"(nível atual: {LEVEL_LABELS[level]}; o projeto pede: {LEVEL_LABELS[role.min_level]}).",
                    mid,
                    role.skill,
                )
            )

        # --- Horas: papel + mentoria contra a disponibilidade ---
        mentoring_hours = cfg.mentoring_hours_per_mentee * n_mentees[mid]
        demand = role.hours_per_week + mentoring_hours
        cap = capacity_of(availability, mid, project.duration_weeks)
        hours_factor.append(1.0 if demand <= 0 else min(1.0, cap / demand))
        loads.append(
            MemberLoad(
                member_id=mid,
                role_index=i,
                capacity=round(cap, 2),
                demand=round(demand, 2),
                mentoring_hours=mentoring_hours,
            )
        )
        if demand > cap + 1e-9:
            factors.append(
                Factor(
                    "sobrecarga",
                    cfg.risk_overload,
                    f"{m.name} está sobrecarregado(a): "
                    f"{'o papel e a mentoria pedem' if mentoring_hours > 0 else 'o papel pede'} "
                    f"{demand:g}h por semana e há {cap:.1f}h disponíveis.",
                    mid,
                    role.skill,
                )
            )

        # --- Precisava de mentor e não tem ---
        if needs_mentor(m, role, cfg) and not mentored:
            factors.append(
                Factor(
                    "sem_mentor",
                    cfg.risk_novato_sem_mentor,
                    f"{m.name} precisa de mentoria em {skill_label}, mas ninguém na squad pode ensinar.",
                    mid,
                    role.skill,
                )
            )

        # --- Crescimento ---
        goal = 1.0 if role.skill in m.learning_goals else 0.0
        learns_with_help = 1.0 if (mentored and level < role.min_level) else 0.0
        growth.append(cfg.growth_goal_weight * goal + cfg.growth_mentor_weight * learns_with_help)

    # --- Ponto único de falha: só vale para papéis críticos ---
    present = [members[a] for a in assignments if a is not None]
    filled_skills = {roles[i].skill for i, a in enumerate(assignments) if a is not None}
    for skill in sorted({r.skill for r in roles if r.critical}):
        coverers = [m for m in present if m.level(skill) >= cfg.backup_min_level]
        if len(coverers) == 1:
            factors.append(
                Factor(
                    "spof",
                    cfg.risk_spof,
                    f"Ponto único de falha em {_label(skill)}: só {coverers[0].name} cobre; "
                    f"se sair, o projeto trava.",
                    coverers[0].id,
                    skill,
                )
            )
        elif len(coverers) == 0 and skill in filled_skills:
            factors.append(
                Factor(
                    "spof",
                    cfg.risk_spof,
                    f"Ninguém na squad cobre {_label(skill)} com nível suficiente.",
                    None,
                    skill,
                )
            )

    weights = [r.weight for r in roles]
    wsum = sum(weights) or 1.0
    cov_avg = sum(w * c for w, c in zip(weights, coverage)) / wsum
    hours_avg = sum(w * h for w, h in zip(weights, hours_factor)) / wsum
    entrega = 100.0 * cov_avg * hours_avg - cfg.mentoring_delivery_cost * len(mentorships)
    entrega = max(0.0, entrega)
    crescimento = 100.0 * sum(growth) / len(roles)
    risco = min(100.0, sum(f.points for f in factors))

    factors.sort(key=lambda f: (-f.points, f.kind, f.member_id or "", f.skill or ""))
    return Metrics(
        entrega=round(entrega, 1),
        crescimento=round(crescimento, 1),
        risco=round(risco, 1),
        factors=tuple(factors),
        loads=tuple(loads),
        mentorships=mentorships,
        role_coverage=tuple(round(c, 2) for c in coverage),
    )


def profile_objective(profile: str, metrics: Metrics, cfg: Config = DEFAULT_CONFIG) -> float:
    """Nota usada na busca: cada tipo de squad pesa os medidores de um jeito."""
    w = PROFILE_WEIGHTS[profile]
    unmentored = sum(1 for f in metrics.factors if f.kind == "sem_mentor")
    overloaded = sum(1 for f in metrics.factors if f.kind == "sobrecarga")
    return (
        w.entrega * metrics.entrega
        + w.crescimento * metrics.crescimento
        - w.risco * metrics.risco
        - cfg.unmentored_penalty * unmentored
        - cfg.overload_search_penalty * overloaded
    )
