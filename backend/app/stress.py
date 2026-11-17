"""Teste de estresse: "e se alguém sair?".

Para cada pessoa do squad, simula a saída dela (reaproveitando `remove_member`)
e compara os medidores antes e depois. A lista sai do PIOR caso para o melhor:
quem, ao sair, deixa o risco mais alto vem primeiro. Sem IA: só contas e frases-modelo.
"""
from .config import DEFAULT_CONFIG, SKILL_LABELS, Config
from .whatif import remove_member

EPS = 0.05  # diferenças menores que isso são tratadas como "sem mudança"


def stress_test(project, squad, members, availability, cfg: Config = DEFAULT_CONFIG) -> list:
    """Uma linha por pessoa do squad, ordenada do mais frágil ao menos frágil.

    Ordem: maior risco depois da saída; empate -> maior queda de entrega; depois id (estável).
    """
    base = squad.metrics
    base_keys = {f.key() for f in base.factors}
    rows = []
    for index, member_id in enumerate(squad.assignments):
        if member_id is None:
            continue
        after = remove_member(project, squad, index, members, availability, cfg).metrics
        new_factors = [f for f in after.factors if f.key() not in base_keys]
        main = max(new_factors, key=lambda f: f.points) if new_factors else None
        role = project.roles[index]
        rows.append(
            {
                "member_id": member_id,
                "name": members[member_id].name,
                "role_index": index,
                "skill": role.skill,
                "skill_label": SKILL_LABELS[role.skill],
                "critical": role.critical,
                "risco_before": base.risco,
                "risco_after": after.risco,
                "delta_risco": round(after.risco - base.risco, 1),
                "delta_entrega": round(after.entrega - base.entrega, 1),
                "entrega_after": after.entrega,
                "main_issue": main.message if main else None,
            }
        )
    rows.sort(key=lambda r: (-r["risco_after"], r["delta_entrega"], r["member_id"]))
    return rows


def _num(value: float) -> str:
    return f"{round(value):d}"


def weakest_sentence(rows: list) -> str:
    """Frase simples sobre o ponto mais frágil (texto-modelo, números como na tela)."""
    if not rows:
        return "Não há ninguém no squad para testar."
    top = rows[0]
    if top["delta_risco"] <= EPS:
        return (
            "Nenhuma saída aumenta o risco: o squad aguenta perder qualquer pessoa. "
            f"A que mais pesa na entrega é {top['name']}."
            if top["delta_entrega"] < -EPS
            else "Nenhuma saída muda o risco nem a entrega deste squad."
        )
    text = (
        f"Se {top['name']} sair, o papel de {top['skill_label']} fica vago e o risco sobe de "
        f"{_num(top['risco_before'])} para {_num(top['risco_after'])}."
    )
    if top["main_issue"]:
        text += f" Principal motivo: {top['main_issue']}"
    return text
