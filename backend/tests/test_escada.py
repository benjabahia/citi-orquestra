"""Escada entre os tipos de squad, também em projetos por briefing (custom).

Regra do produto:
    crescimento: Evolutivo >= Balanceado >= Seguro
    entrega:     Seguro >= Balanceado
Antes ela só era garantida nos 6 projetos de exemplo. O caso FisioAgenda (achado ao
gravar o vídeo) tinha o Evolutivo com crescimento 28 e o Balanceado com 32.
"""
import random
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api import app
from app.config import DEFAULT_CONFIG, SKILLS

client = TestClient(app)
DADOS = Path(__file__).parent / "dados"

FISIOAGENDA = {
    "name": "FisioAgenda",
    "duration_weeks": 10,
    "roles": [
        {"skill": "backend", "min_level": 3, "hours_per_week": 8, "critical": True},
        {"skill": "frontend", "min_level": 2, "hours_per_week": 6, "critical": False},
        {"skill": "ux_ui", "min_level": 2, "hours_per_week": 4, "critical": False},
        {"skill": "devops", "min_level": 2, "hours_per_week": 4, "critical": False},
        {"skill": "qa", "min_level": 2, "hours_per_week": 4, "critical": False},
    ],
}


def montar(body):
    r = client.post("/api/squads/build", json=body)
    assert r.status_code == 200, r.text
    return r.json()["squads"]


def novatos(squad):
    return sum(1 for s in squad["slots"] if s["member_id"] and s["is_novato"])


def novatos_disponiveis(body):
    team = client.post("/api/squads/team", json=body).json()["members"]
    return sum(1 for m in team if m["is_novato"] and m["available_hours"] > 0)


def conferir_escada(body, sq):
    """A escada e as regras de cada tipo, com uma mensagem que diz qual degrau quebrou."""
    seg, bal, evo = (sq[p]["metrics"] for p in ("segura", "balanceada", "evolutiva"))
    nome = body["name"]
    assert evo["crescimento"] >= bal["crescimento"] >= seg["crescimento"], (nome, "crescimento", seg, bal, evo)
    assert seg["entrega"] >= bal["entrega"], (nome, "entrega", seg["entrega"], bal["entrega"])

    # As regras de novatos continuam valendo (quando não foram relaxadas por falta de gente).
    pool = novatos_disponiveis(body)
    minimo = min(max(DEFAULT_CONFIG.evolutiva_min_novatos, len(body["roles"]) // 2), pool)
    if not sq["segura"]["notes"]:
        assert novatos(sq["segura"]) == 0, nome
    if not sq["balanceada"]["notes"]:
        assert novatos(sq["balanceada"]) == min(1, pool), nome
    if not sq["evolutiva"]["notes"]:
        assert novatos(sq["evolutiva"]) >= minimo, nome

    # Os três continuam diferentes entre si.
    conjuntos = [frozenset(a for a in sq[p]["assignments"] if a) for p in sq]
    assert len(set(conjuntos)) == 3, nome


def briefing_aleatorio(i, sheet=None):
    """Papéis, níveis, horas e duração sorteados com semente fixa (sempre os mesmos).

    Antes da correção, os sorteios 1, 3, 8, 9 e 19 quebravam a escada com o pool de
    exemplo e o 21 com a planilha com horas: a varredura cobre casos reais, não só fáceis.
    """
    rng = random.Random(f"varredura-{i}")
    skills = rng.sample(SKILLS, rng.randint(3, 6))
    critico = rng.choice([None] + list(range(len(skills))))
    body = {
        "name": f"Briefing {i}",
        "duration_weeks": rng.choice([2, 4, 6, 8, 10, 12]),
        "roles": [
            {"skill": s, "min_level": rng.randint(1, 4),
             "hours_per_week": rng.choice([2, 4, 5, 6, 8, 10, 12]), "critical": k == critico}
            for k, s in enumerate(skills)
        ],
    }
    if sheet is not None:
        body["replace_members"] = sheet
    return body


def planilha(nome):
    r = client.post("/api/members/import", json={"text": (DADOS / nome).read_text(encoding="utf-8")})
    data = r.json()
    assert data["ok"], data["errors"]
    return data["members"]


# --- (i) o caso exato do FisioAgenda ---------------------------------------


def test_fisioagenda_evolutivo_cresce_pelo_menos_o_balanceado():
    sq = montar(FISIOAGENDA)
    conferir_escada(FISIOAGENDA, sq)
    # Antes: Evolutivo 28 < Balanceado 32. Agora o Evolutivo forma mais gente.
    assert sq["evolutiva"]["metrics"]["crescimento"] > 28
    assert sq["evolutiva"]["metrics"]["crescimento"] >= sq["balanceada"]["metrics"]["crescimento"]
    # Quem precisa de mentor tem mentor.
    assert not [f for f in sq["evolutiva"]["metrics"]["factors"] if f["kind"] == "sem_mentor"]


def test_fisioagenda_continua_deterministico_e_aceita_troca():
    """Mesma entrada, mesmo resultado; e o Evolutivo refeito aceita trocas como qualquer squad."""
    a, b = montar(FISIOAGENDA), montar(FISIOAGENDA)
    assert a == b
    evo = a["evolutiva"]
    corpo = {"profile": "evolutiva", "assignments": evo["assignments"], "role_index": 0, "custom": FISIOAGENDA}
    r = client.post("/api/projects/custom/whatif", json=corpo)
    assert r.status_code == 200
    assert r.json()["current"]["metrics"] == evo["metrics"]


# --- (ii) varredura com o pool de exemplo ------------------------------------


@pytest.mark.parametrize("i", range(30))
def test_varredura_briefings_pool_de_exemplo(i):
    body = briefing_aleatorio(i)
    conferir_escada(body, montar(body))


# --- (iii) varredura com pool de planilha importada --------------------------


@pytest.mark.parametrize("arquivo", ["membros-teste.csv", "membros-teste-horas.csv"])
@pytest.mark.parametrize("i", range(30))
def test_varredura_briefings_pool_de_planilha(arquivo, i):
    body = briefing_aleatorio(i, sheet=planilha(arquivo))
    conferir_escada(body, montar(body))

