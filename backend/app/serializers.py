"""Transforma os resultados do motor (dataclasses) em dicionários simples,
prontos para virarem JSON e serem desenhados pelo site."""
from .config import SKILL_LABELS


def role_dict(index, role):
    return {
        "index": index,
        "skill": role.skill,
        "skill_label": SKILL_LABELS[role.skill],
        "min_level": role.min_level,
        "hours_per_week": role.hours_per_week,
        "critical": role.critical,
    }


def project_dict(project):
    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "duration_weeks": project.duration_weeks,
        "roles": [role_dict(i, r) for i, r in enumerate(project.roles)],
    }


def member_dict(member, cfg):
    return {
        "id": member.id,
        "name": member.name,
        "months_in_citi": member.months_in_citi,
        "is_novato": member.is_novato(cfg.novato_months),
        "skills": member.skills,
        "learning_goals": list(member.learning_goals),
    }


def metrics_dict(metrics):
    return {
        "entrega": metrics.entrega,
        "crescimento": metrics.crescimento,
        "risco": metrics.risco,
        "role_coverage": list(metrics.role_coverage),
        "factors": [
            {
                "kind": f.kind,
                "points": f.points,
                "message": f.message,
                "member_id": f.member_id,
                "skill": f.skill,
            }
            for f in metrics.factors
        ],
        "loads": [
            {
                "member_id": l.member_id,
                "role_index": l.role_index,
                "capacity": l.capacity,
                "demand": l.demand,
                "mentoring_hours": l.mentoring_hours,
            }
            for l in metrics.loads
        ],
        "mentorships": [
            {"mentor_id": m.mentor_id, "mentee_id": m.mentee_id, "skill": m.skill}
            for m in metrics.mentorships
        ],
    }


def squad_dict(squad, project, members, cfg):
    slots = []
    for index, role in enumerate(project.roles):
        member_id = squad.assignments[index]
        member = members.get(member_id) if member_id else None
        slots.append(
            {
                **role_dict(index, role),
                "member_id": member_id,
                "member_name": member.name if member else None,
                "member_level": member.level(role.skill) if member else None,
                "is_novato": member.is_novato(cfg.novato_months) if member else False,
            }
        )
    return {
        "profile": squad.profile,
        "slots": slots,
        "assignments": list(squad.assignments),
        "metrics": metrics_dict(squad.metrics),
        "notes": list(squad.notes),
    }


def substitute_dict(sub, member, skill, cfg):
    return {
        "member_id": sub.member_id,
        "name": sub.name,
        "skill_level": member.level(skill),
        "is_novato": member.is_novato(cfg.novato_months),
        "months_in_citi": member.months_in_citi,
        "metrics": metrics_dict(sub.metrics),
        "delta_entrega": sub.delta_entrega,
        "delta_crescimento": sub.delta_crescimento,
        "delta_risco": sub.delta_risco,
        "new_issues": list(sub.new_issues),
        "resolved_issues": list(sub.resolved_issues),
    }
