"""Monta as 3 squads de um projeto (Segura, Evolutiva, Balanceada).

Como funciona (decisão Q3: quem decide é o ALGORITMO, não o LLM):

1. Cada tipo de squad tem uma "nota" própria (profile_objective), que pesa
   entrega, crescimento e risco de um jeito diferente.
2. A busca parte de várias squads iniciais e vai trocando pessoas enquanto a
   nota melhorar (subida de encosta). Quem tem a maior nota no fim vence.
3. Regras duras por tipo de squad (para as 3 opções serem realmente diferentes):
   - Segura:     nenhum novato.
   - Balanceada: exatamente 1 novato (se houver novato disponível).
   - Evolutiva:  pelo menos 1 novato a cada 3 papéis (a busca pode escolher mais), com mentor.
4. As 3 squads precisam ter pessoas diferentes entre si (nunca saem repetidas).

O resultado é determinístico: mesma entrada e mesma `seed` dão a mesma squad.
"""
import random

from .config import DEFAULT_CONFIG, PROFILES, Config
from .models import Project, Squad
from .scoring import capacity_of, evaluate, profile_objective


def available_pool(project: Project, members: dict, availability: dict) -> list:
    """Ids de quem tem alguma hora livre neste projeto (em ordem, p/ ser estável)."""
    return sorted(
        mid
        for mid in members
        if capacity_of(availability, mid, project.duration_weeks) > 0
    )


def _neighbors(state: tuple, pool: list):
    """Todas as squads "vizinhas": trocar uma pessoa por alguém de fora, ou
    trocar duas pessoas de papel."""
    n = len(state)
    used = {s for s in state if s is not None}
    for i in range(n):
        for cand in pool:
            if cand not in used:
                nb = list(state)
                nb[i] = cand
                yield tuple(nb)
    for i in range(n):
        for j in range(i + 1, n):
            if state[i] != state[j]:
                nb = list(state)
                nb[i], nb[j] = nb[j], nb[i]
                yield tuple(nb)


def _sort_key(state: tuple) -> tuple:
    return tuple("" if s is None else s for s in state)


def build_squad(
    profile: str,
    project: Project,
    members: dict,
    availability: dict,
    cfg: Config = DEFAULT_CONFIG,
    seed: int = 7,
    restarts: int = 5,
    exclude: frozenset = frozenset(),
) -> Squad:
    """`exclude` é um conjunto de squads (conjuntos de ids) que NÃO podem se repetir."""
    if profile not in PROFILES:
        raise ValueError(f"perfil desconhecido: {profile}")

    pool = available_pool(project, members, availability)
    n = len(project.roles)
    rng = random.Random(f"{seed}-{profile}-{project.id}")
    notes = []

    novatos_in_pool = [m for m in pool if members[m].is_novato(cfg.novato_months)]
    min_novatos = min(max(1, n // 3), len(novatos_in_pool))

    def count_novatos(state):
        return sum(1 for s in state if s is not None and members[s].is_novato(cfg.novato_months))

    def feasible(state, strict):
        if frozenset(s for s in state if s is not None) in exclude:
            return False
        if not strict:
            return True
        k = count_novatos(state)
        if profile == "segura":
            return k == 0
        if profile == "balanceada":
            return k == min(1, len(novatos_in_pool))
        return k >= min_novatos  # evolutiva

    cache = {}

    def metrics_of(state):
        if state not in cache:
            cache[state] = evaluate(project, state, members, availability, cfg)
        return cache[state]

    def score(state):
        return profile_objective(profile, metrics_of(state), cfg)

    def random_state():
        k = min(n, len(pool))
        chosen = rng.sample(pool, k) + [None] * (n - k)
        rng.shuffle(chosen)
        return tuple(chosen)

    def climb(start, strict):
        current, current_score = start, score(start)
        while True:
            best, best_score = None, current_score
            for nb in _neighbors(current, pool):
                if not feasible(nb, strict):
                    continue
                s = score(nb)
                if s > best_score + 1e-9:
                    best, best_score = nb, s
            if best is None:
                return current, current_score
            current, current_score = best, best_score

    results = []
    for strict in (True, False):
        starts = []
        for _ in range(400):
            st = random_state()
            if feasible(st, strict):
                starts.append(st)
            if len(starts) >= restarts:
                break
        if starts:
            if not strict:
                notes.append(
                    "Não há pessoas suficientes para cumprir todas as regras deste tipo de squad; "
                    "a regra sobre novatos foi relaxada."
                )
            results = [climb(st, strict) for st in starts]
            break

    if not results:  # ninguém disponível
        empty = tuple([None] * n)
        results = [(empty, score(empty))]

    # Maior nota vence; o desempate pelos ids deixa o resultado estável.
    best_state, best_score = sorted(results, key=lambda r: (-r[1], _sort_key(r[0])))[0]
    return Squad(
        profile=profile,
        assignments=best_state,
        metrics=metrics_of(best_state),
        objective=round(best_score, 2),
        notes=tuple(notes),
    )


def build_squads(
    project: Project,
    members: dict,
    availability: dict,
    cfg: Config = DEFAULT_CONFIG,
    seed: int = 7,
    restarts: int = 5,
) -> dict:
    """As 3 opções para o gerente comparar lado a lado."""
    def ids_of(squad):
        return frozenset(a for a in squad.assignments if a is not None)

    def build(profile, taken):
        return build_squad(
            profile, project, members, availability, cfg, seed, restarts, frozenset(taken)
        )

    segura = build("segura", set())

    # Evolutiva e Balanceada podem disputar a mesma melhor squad. Quem é montada
    # por último pega as "sobras", então testamos as duas ordens e ficamos com a
    # que dá a maior nota somada (cada squad medida pela nota do seu tipo).
    option_a = [build("evolutiva", {ids_of(segura)})]
    option_a.append(build("balanceada", {ids_of(segura), ids_of(option_a[0])}))
    option_b = [build("balanceada", {ids_of(segura)})]
    option_b.append(build("evolutiva", {ids_of(segura), ids_of(option_b[0])}))

    total_a = sum(sq.objective for sq in option_a)
    total_b = sum(sq.objective for sq in option_b)
    if total_a >= total_b:
        evolutiva, balanceada = option_a
    else:
        balanceada, evolutiva = option_b
    return {"segura": segura, "evolutiva": evolutiva, "balanceada": balanceada}
