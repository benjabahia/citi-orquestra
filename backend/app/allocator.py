"""Monta os 3 squads de um projeto (Seguro, Evolutivo, Balanceado).

Como funciona (decisão Q3: quem decide é o ALGORITMO, não o LLM):

1. Cada tipo de squad tem uma "nota" própria (profile_objective), que pesa
   entrega, crescimento e risco de um jeito diferente.
2. A busca parte de vários squads iniciais e vai trocando pessoas enquanto a
   nota melhorar (subida de encosta). Quem tem a maior nota no fim vence.
3. Regras duras por tipo de squad (para as 3 opções serem realmente diferentes):
   - Seguro:     nenhum novato.
   - Balanceado: exatamente 1 novato (se houver novato disponível).
   - Evolutivo:  pelo menos 2 novatos (ou metade dos papéis), sempre com mentor.
4. Os 3 squads precisam ter pessoas diferentes entre si (nunca saem repetidas).

O resultado é determinístico: mesma entrada e mesma `seed` dão o mesmo squad.
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
    """Todos os squads "vizinhos": trocar uma pessoa por alguém de fora, ou
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


def _novato_rule(profile: str, project: Project, members: dict, pool: list, cfg: Config):
    """Regra de novatos de cada tipo, como uma função "quanto falta para cumprir" (0 = cumpre).

    - Seguro:     nenhum novato.
    - Balanceado: exatamente 1 (se houver novato disponível).
    - Evolutivo:  pelo menos max(evolutiva_min_novatos, metade dos papéis), limitado a quantos existem.
    """
    n_novatos = sum(1 for m in pool if members[m].is_novato(cfg.novato_months))
    min_novatos = min(max(cfg.evolutiva_min_novatos, len(project.roles) // 2), n_novatos)

    def gap(state) -> int:
        k = sum(1 for s in state if s is not None and members[s].is_novato(cfg.novato_months))
        if profile == "segura":
            return k
        if profile == "balanceada":
            return abs(k - min(1, n_novatos))
        return max(0, min_novatos - k)  # evolutiva

    return gap


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
    novato_gap = _novato_rule(profile, project, members, pool, cfg)

    def feasible(state, strict):
        if frozenset(s for s in state if s is not None) in exclude:
            return False
        return not strict or novato_gap(state) == 0

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

    # Evolutivo e Balanceado podem disputar o mesmo melhor squad. Quem é montado
    # por último pega as "sobras", então testamos as duas ordens e ficamos com a
    # que dá a maior nota somada (cada squad medido pela nota do seu tipo).
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
    return _enforce_ladder(segura, balanceada, evolutiva, project, members, availability, cfg)


# ---------------------------------------------------------------------------
# Escada entre os tipos de squad
# ---------------------------------------------------------------------------
# Cada tipo é montado pela SUA nota, que mistura entrega, crescimento e risco.
# Isso não garante sozinho a escada do produto:
#     crescimento: Evolutivo >= Balanceado >= Seguro
#     entrega:     Seguro >= Balanceado
# (a busca é local e pode parar num arranjo "bom o bastante" para a nota, mas com
# menos crescimento que o Balanceado). Por isso, no fim, conferimos a escada e,
# só se ela quebrar, refazemos o squad que ficou fora do lugar. Nos projetos em
# que a escada já vale, nada muda.


def _ids(squad: Squad) -> frozenset:
    return _ids_of_state(squad.assignments)


def _repair_squad(squad, limits, starts, project, members, availability, cfg, exclude, restarts=8):
    """Procura um squad do MESMO tipo que respeite `limits` (lista de
    (medidor, ">=" ou "<=", valor)). Devolve o squad novo, ou None se não achar.

    A busca é a mesma subida de encosta, mas com uma ordem de prioridades:
      1º cumprir a regra de novatos do tipo;
      2º mentor para quem precisa;
      3º cumprir os limites da escada;
      4º ter o mínimo de pessoas sobrecarregadas (sobrecarga evitável não entra);
      5º só então, a nota normal do tipo de squad (entrega, risco...).
    O squad novo só é aceito se cumpre a escada e não piora a regra de novatos
    nem a de mentoria em relação ao squad original.
    """
    pool = available_pool(project, members, availability)
    novato_gap = _novato_rule(squad.profile, project, members, pool, cfg)
    cache = {}

    def metrics_of(state):
        if state not in cache:
            cache[state] = evaluate(project, state, members, availability, cfg)
        return cache[state]

    def unmentored(state):
        return sum(1 for f in metrics_of(state).factors if f.kind == "sem_mentor")

    def shortfall(state):
        m, total = metrics_of(state), 0.0
        for name, op, value in limits:
            v = getattr(m, name)
            total += max(0.0, value - v) if op == ">=" else max(0.0, v - value)
        return round(total, 6)

    def overloaded(state):
        return sum(1 for f in metrics_of(state).factors if f.kind == "sobrecarga")

    def key(state):
        return (-novato_gap(state), -unmentored(state), -shortfall(state), -overloaded(state),
                round(profile_objective(squad.profile, metrics_of(state), cfg), 6))

    def allowed(state):
        return _ids_of_state(state) not in exclude

    def climb(current):
        if not allowed(current):
            # Começa de um arranjo proibido (ex.: o do Balanceado): o 1º passo é obrigatório.
            options = [nb for nb in _neighbors(current, pool) if allowed(nb)]
            if not options:
                return None
            current = max(options, key=key)  # max devolve o primeiro em caso de empate: estável
        current_key = key(current)
        while True:
            best, best_key = None, current_key
            for nb in _neighbors(current, pool):
                if allowed(nb):
                    k = key(nb)
                    if k > best_key:
                        best, best_key = nb, k
            if best is None:
                return current
            current, current_key = best, best_key

    # Além dos arranjos dados, alguns pontos de partida sorteados (semente fixa: resultado estável),
    # porque a subida de encosta pode parar num "pico local" que não cumpre a escada.
    rng = random.Random(f"escada-{squad.profile}-{project.id}")
    n, k = len(project.roles), min(len(project.roles), len(pool))
    for _ in range(restarts):
        chosen = rng.sample(pool, k) + [None] * (n - k)
        rng.shuffle(chosen)
        starts = list(starts) + [tuple(chosen)]
    found = [s for s in (climb(tuple(st)) for st in starts) if s is not None]
    if not found:
        return None
    best = sorted(found, key=lambda s: (tuple(-x for x in key(s)), _sort_key(s)))[0]
    original = tuple(squad.assignments)
    if (shortfall(best) > 0 or novato_gap(best) > novato_gap(original)
            or unmentored(best) > unmentored(original)):
        return None
    metrics = metrics_of(best)
    return Squad(
        profile=squad.profile,
        assignments=best,
        metrics=metrics,
        objective=round(profile_objective(squad.profile, metrics, cfg), 2),
        notes=squad.notes if novato_gap(best) else (),
    )


def _ids_of_state(state) -> frozenset:
    return frozenset(s for s in state if s is not None)


def _ladder_limits(profile: str, sq: dict) -> list:
    """Os limites que o squad `profile` precisa respeitar em relação aos outros dois."""
    seg, bal, evo = (sq[p].metrics for p in ("segura", "balanceada", "evolutiva"))
    if profile == "evolutiva":
        return [("crescimento", ">=", bal.crescimento)]
    if profile == "segura":
        return [("entrega", ">=", bal.entrega),
                ("crescimento", "<=", min(bal.crescimento, evo.crescimento))]
    return [  # balanceada: fica entre os outros dois
        ("crescimento", ">=", seg.crescimento),
        ("crescimento", "<=", evo.crescimento),
        ("entrega", "<=", seg.entrega),
    ]


def _out_of_place(sq: dict) -> set:
    """Quais tipos de squad estão envolvidos em algum degrau quebrado da escada."""
    seg, bal, evo = (sq[p].metrics for p in ("segura", "balanceada", "evolutiva"))
    bad = set()
    if evo.crescimento < bal.crescimento:
        bad |= {"evolutiva", "balanceada"}
    if bal.crescimento < seg.crescimento or seg.entrega < bal.entrega:
        bad |= {"segura", "balanceada"}
    if seg.crescimento > evo.crescimento:
        bad.add("segura")
    return bad


def _enforce_ladder(segura, balanceada, evolutiva, project, members, availability, cfg):
    """Confere a escada e, se ela quebrar, refaz o squad fora do lugar.

    Ordem de tentativa (do que menos piora o resultado para o que mais piora):
      1. Evolutivo: busca um arranjo que cresça pelo menos o mesmo que o Balanceado.
      2. Seguro: busca um arranjo sem novatos que entregue pelo menos o mesmo que o Balanceado
         e não cresça mais que os outros dois (veteranos que têm o papel como meta contam
         crescimento, e isso pode deixar o Seguro "acima" do Evolutivo).
      3. Balanceado: refaz para caber entre os outros dois (crescimento entre o do Seguro
         e o do Evolutivo, entrega até a do Seguro). Acontece quando o Evolutivo não
         consegue crescer mais (ex.: poucos papéis e nenhum mentor que sirva a 2 novatos).
    Cada refação respeita as regras de novatos e de mentoria do tipo e não repete
    as pessoas dos outros dois squads. Se a escada já vale, nada muda.
    """
    sq = {"segura": segura, "balanceada": balanceada, "evolutiva": evolutiva}
    for _ in range(3):
        if not _out_of_place(sq):
            break
        for profile in ("evolutiva", "segura", "balanceada"):
            if profile not in _out_of_place(sq):
                continue
            others = [sq[p] for p in sq if p != profile]
            starts = [sq[profile].assignments] + [o.assignments for o in others]
            novo = _repair_squad(
                sq[profile], _ladder_limits(profile, sq), starts,
                project, members, availability, cfg, frozenset(_ids(o) for o in others),
            )
            if novo is not None:
                sq[profile] = novo
    return {"segura": sq["segura"], "evolutiva": sq["evolutiva"], "balanceada": sq["balanceada"]}
