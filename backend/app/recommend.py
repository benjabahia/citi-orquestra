"""Recomendação por prioridade: qual das 3 squads combina com o momento do projeto.

Função PURA e sem IA: recebe os 3 medidores de cada squad e devolve qual
recomendar e uma frase curta com os números reais (texto-modelo).

Nota de cada squad (quanto maior, melhor), com os pesos de PRIORITY_WEIGHTS:
    nota = peso_entrega * entrega + peso_crescimento * crescimento + peso_risco * (100 - risco)

- prazo:      pesa entrega e risco baixo. Trava extra: nunca recomenda uma squad
              cujo risco passa do menor risco entre as três em mais de
              `prazo_max_risk_gap` pontos.
- formar:     pesa sobretudo o crescimento (um pouco de entrega e risco, para não
              recomendar uma squad de formação que põe o projeto em perigo).
- equilibrio: os três medidores valem o mesmo.

Empate (notas iguais até 2 casas): vence a primeira na ordem fixa da prioridade
(TIE_ORDER). Assim o resultado é sempre o mesmo para a mesma entrada.
"""
import math

from .config import PRIORITY_WEIGHTS, PROFILE_TITLES, RECOMMEND_CONFIG

PRIORITIES = ("prazo", "formar", "equilibrio")

# Ordem de desempate: a squad que "combina mais" com a prioridade vem primeiro.
TIE_ORDER = {
    "prazo": ("segura", "balanceada", "evolutiva"),
    "formar": ("evolutiva", "balanceada", "segura"),
    "equilibrio": ("balanceada", "segura", "evolutiva"),
}

EPS = 1e-9


def show(value: float) -> int:
    """Arredonda como a tela (Math.round do JavaScript): 12,5 vira 13.

    O round() do Python arredondaria 12,5 para 12 e a frase citaria um número
    diferente do que aparece na tabela.
    """
    return int(math.floor(value + 0.5))


def score(priority: str, m: dict) -> float:
    w = PRIORITY_WEIGHTS[priority]
    return round(w.entrega * m["entrega"] + w.crescimento * m["crescimento"] + w.risco * (100 - m["risco"]), 2)


def _best(values: dict, profile: str, lower_is_better=False) -> bool:
    """A squad `profile` tem o melhor valor (empates contam como melhor)?"""
    target = min(values.values()) if lower_is_better else max(values.values())
    return abs(values[profile] - target) < EPS


def recommend(priority: str, metrics: dict, cfg=RECOMMEND_CONFIG) -> dict:
    """`metrics` = {"segura": {"entrega":.., "crescimento":.., "risco":..}, ...}.

    Devolve {"priority", "profile", "reason", "scores"}.
    """
    if priority not in PRIORITIES:
        raise ValueError(f"prioridade desconhecida: {priority}")
    order = [p for p in TIE_ORDER[priority] if p in metrics]
    if not order:
        raise ValueError("nenhuma squad para comparar")

    scores = {p: score(priority, metrics[p]) for p in order}
    candidates = list(order)
    if priority == "prazo":
        lowest = min(metrics[p]["risco"] for p in order)
        candidates = [p for p in order if metrics[p]["risco"] <= lowest + cfg.prazo_max_risk_gap + EPS]

    top = max(scores[p] for p in candidates)
    tied = [p for p in candidates if abs(scores[p] - top) < EPS]  # já na ordem de desempate
    winner = tied[0]

    # Alguém teria nota maior, mas foi barrado pela trava de risco?
    blocked = [p for p in order if p not in candidates and scores[p] > top + EPS]

    reason = _reason(priority, winner, metrics, blocked[0] if blocked else None)
    if len(tied) > 1:
        others = " e a ".join(PROFILE_TITLES[p] for p in tied[1:])
        reason += f" Empata com a {others}; vale a ordem fixa de desempate."
    return {"priority": priority, "profile": winner, "reason": reason, "scores": scores}


def recommend_all(metrics: dict, cfg=RECOMMEND_CONFIG) -> dict:
    return {p: recommend(p, metrics, cfg) for p in PRIORITIES}


def _reason(priority: str, winner: str, metrics: dict, blocked) -> str:
    """Texto-modelo: frases fixas preenchidas com os números (arredondados como na tela)."""
    me = metrics[winner]
    E, C, R = show(me["entrega"]), show(me["crescimento"]), show(me["risco"])
    entregas = {p: m["entrega"] for p, m in metrics.items()}
    riscos = {p: m["risco"] for p, m in metrics.items()}
    cresc = {p: m["crescimento"] for p, m in metrics.items()}

    if priority == "prazo":
        top_e, low_r = _best(entregas, winner), _best(riscos, winner, lower_is_better=True)
        if top_e and low_r:
            text = f"Maior entrega ({E}) e menor risco ({R})."
        elif top_e:
            text = f"Maior entrega ({E}), com risco {R}."
        elif low_r:
            text = f"Menor risco ({R}), com entrega {E}."
        else:
            text = f"Entrega {E} e risco {R}: o melhor saldo entre as três."
        if blocked:
            b = metrics[blocked]
            text += (
                f" A {PROFILE_TITLES[blocked]} entregaria {show(b['entrega'])}, "
                f"mas tem risco {show(b['risco'])}, muito acima."
            )
        return text

    if priority == "formar":
        if _best(cresc, winner):
            return f"Maior crescimento ({C}), com risco {R}."
        rival = max(cresc, key=lambda p: (cresc[p], -TIE_ORDER["formar"].index(p)))
        rm = metrics[rival]
        return (
            f"Crescimento {C} com risco {R}. A {PROFILE_TITLES[rival]} cresce mais "
            f"({show(rm['crescimento'])}), mas com risco {show(rm['risco'])}."
        )

    # equilibrio
    return f"Melhor conjunto dos três medidores: entrega {E}, crescimento {C} e risco {R}."
