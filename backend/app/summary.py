"""Resumo da squad para colar no chat (WhatsApp, Slack).

Função pura: recebe o projeto, a squad já calculada e devolve um texto.
Nenhuma IA e nenhum cálculo novo: todos os números vêm dos medidores da squad,
então o texto bate com o que aparece na tela.
"""
from .config import PROFILE_TITLES, SKILL_LABELS

EPS = 0.05  # mesma tolerância da tela para "faltam horas"

DECLARED_NOTE = "Disponibilidade declarada pelos membros; o sistema não verifica as horas."
EXAMPLE_NOTE = "Dados e horas de exemplo (fictícios)."


def _round(value: float) -> int:
    """Arredonda como o site (0,5 sobe), não como o round() do Python (que arredonda para o par)."""
    return int(value + 0.5)


def _hours(value: float) -> str:
    """Horas com no máximo 1 casa e vírgula decimal: 7,5 e 6."""
    text = f"{value:.1f}"
    if text.endswith(".0"):
        text = text[:-2]
    return text.replace(".", ",")


def _short_text(free: float, needed: float) -> str:
    """'faltam 2 h' (ou 'falta 1 h') quando as horas exigidas passam das livres; senão vazio."""
    missing = needed - free
    if missing <= EPS:
        return ""
    return f"{'falta' if missing <= 1.05 else 'faltam'} {_hours(missing)} h"


def build_summary(project, squad, members, cfg, custom: bool, weakest: str | None = None) -> str:
    """Texto curto e legível no WhatsApp e no Slack (*negrito* funciona nos dois)."""
    m = squad.metrics
    loads = {load.member_id: load for load in m.loads}
    title = PROFILE_TITLES[squad.profile]

    lines = [
        f"*{project.name}* · {project.duration_weeks} semanas",
        f"Squad {title}",
        f"Entrega {_round(m.entrega)} · Crescimento {_round(m.crescimento)} · Risco {_round(m.risco)}",
        "",
        "*Equipe*",
    ]
    for index, role in enumerate(project.roles):
        label = SKILL_LABELS[role.skill]
        member_id = squad.assignments[index]
        if member_id is None:
            lines.append(f"- {label}: vaga em aberto")
            continue
        member = members[member_id]
        details = [f"nível {member.level(role.skill)}"]
        load = loads.get(member_id)
        if load is not None:
            details.append(f"{_hours(load.capacity)} h livres · {_hours(load.demand)} h exigidas")
        short = _short_text(load.capacity, load.demand) if load is not None else ""
        extra = f" ⚠ {short}" if short else ""
        novato = ", novato" if member.is_novato(cfg.novato_months) else ""
        lines.append(f"- {label}: {member.name} ({', '.join(details)}{novato}){extra}")

    lines += ["", "*Mentorias*"]
    if m.mentorships:
        for mentorship in m.mentorships:
            mentor = members[mentorship.mentor_id].name
            mentee = members[mentorship.mentee_id].name
            lines.append(f"- {mentor} ensina {mentee} ({SKILL_LABELS[mentorship.skill]})")
    else:
        lines.append("- Nenhuma (a squad não precisa)")

    if weakest:
        lines += ["", f"*Ponto mais frágil:* {weakest}"]

    lines += ["", f"_{DECLARED_NOTE if custom else EXAMPLE_NOTE}_"]
    return "\n".join(lines)
