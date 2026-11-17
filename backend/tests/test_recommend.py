"""Testes da recomendação por prioridade (prazo apertado, formar gente, equilíbrio)."""
import pytest
from fastapi.testclient import TestClient

from app.allocator import build_squads
from app.api import app
from app.data import load_scenario
from app.recommend import PRIORITIES, recommend, recommend_all, show
from app.serializers import metrics_dict

client = TestClient(app)


def _m(entrega, crescimento, risco):
    return {"entrega": entrega, "crescimento": crescimento, "risco": risco}


@pytest.fixture(scope="module")
def example_metrics():
    """Medidores reais das 3 squads de cada um dos 6 projetos de exemplo."""
    scenario = load_scenario()
    members = scenario.members_by_id()
    out = {}
    for project in scenario.projects:
        built = build_squads(project, members, scenario.availability[project.id])
        out[project.id] = {p: metrics_dict(sq.metrics) for p, sq in built.items()}
    return out


# Projeto -> (prazo, formar, equilibrio)
EXPECTED = {
    "agenda-clinica": ("segura", "evolutiva", "balanceada"),
    "loja-cosmeticos": ("segura", "evolutiva", "balanceada"),
    "painel-industria": ("segura", "evolutiva", "segura"),
    "app-logistica": ("segura", "evolutiva", "balanceada"),
    "site-institucional": ("segura", "evolutiva", "balanceada"),
    # Projeto armadilha: a Evolutiva cresce mais, mas o risco dela (47) pesa demais.
    "pagamentos": ("segura", "balanceada", "balanceada"),
}


@pytest.mark.parametrize("project_id", sorted(EXPECTED))
def test_cada_prioridade_recomenda_o_esperado_nos_6_projetos(example_metrics, project_id):
    recs = recommend_all(example_metrics[project_id])
    got = tuple(recs[p]["profile"] for p in PRIORITIES)
    assert got == EXPECTED[project_id]


def test_prazo_nunca_recomenda_risco_muito_acima_nos_exemplos(example_metrics):
    for metrics in example_metrics.values():
        chosen = metrics[recommend("prazo", metrics)["profile"]]
        assert chosen["risco"] <= min(m["risco"] for m in metrics.values()) + 15


def test_prazo_barra_squad_de_risco_muito_alto_mesmo_com_nota_maior():
    """A Segura teria a melhor nota (entrega 100), mas o risco 40 está muito acima de 10."""
    metrics = {
        "segura": _m(100, 0, 40),
        "evolutiva": _m(40, 60, 30),
        "balanceada": _m(65, 30, 10),
    }
    rec = recommend("prazo", metrics)
    assert rec["scores"]["segura"] > rec["scores"]["balanceada"]  # a trava é que muda o resultado
    assert rec["profile"] == "balanceada"
    assert rec["reason"] == (
        "Menor risco (10), com entrega 65. A Segura entregaria 100, mas tem risco 40, muito acima."
    )


def test_motivo_cita_os_numeros_corretos(example_metrics):
    agenda = recommend_all(example_metrics["agenda-clinica"])
    assert agenda["prazo"]["reason"] == "Maior entrega (100) e menor risco (0)."
    assert agenda["formar"]["reason"] == "Maior crescimento (65), com risco 25."
    assert agenda["equilibrio"]["reason"] == (
        "Melhor conjunto dos três medidores: entrega 92, crescimento 40 e risco 0."
    )
    pag = recommend("formar", example_metrics["pagamentos"])
    assert pag["reason"] == (
        "Crescimento 40 com risco 17. A Evolutiva cresce mais (50), mas com risco 47."
    )


@pytest.mark.parametrize("project_id", sorted(EXPECTED))
def test_numeros_do_motivo_sao_os_da_squad_recomendada(example_metrics, project_id):
    """O equilíbrio cita os 3 medidores: conferimos que são os da squad escolhida."""
    metrics = example_metrics[project_id]
    rec = recommend("equilibrio", metrics)
    m = metrics[rec["profile"]]
    assert f"entrega {show(m['entrega'])}," in rec["reason"]
    assert f"crescimento {show(m['crescimento'])} " in rec["reason"]
    assert rec["reason"].endswith(f"risco {show(m['risco'])}.")


def test_arredonda_igual_a_tela():
    """7,5 aparece como 8 na tabela (Math.round); o motivo precisa dizer 8, não 7."""
    assert show(7.5) == 8 and show(12.5) == 13 and show(36.7) == 37 and show(0) == 0


@pytest.mark.parametrize(
    "priority, winner, loser",
    [("prazo", "segura", "balanceada"), ("formar", "evolutiva", "balanceada"), ("equilibrio", "balanceada", "segura")],
)
def test_empate_tem_desempate_estavel(priority, winner, loser):
    """Três squads com números idênticos: vence a primeira da ordem fixa da prioridade."""
    same = _m(80, 40, 10)
    metrics = {"segura": same, "evolutiva": same, "balanceada": same}
    rec = recommend(priority, metrics)
    assert rec["profile"] == winner
    assert "Empata com a" in rec["reason"] and "ordem fixa de desempate" in rec["reason"]
    # A ordem em que as squads chegam não muda o resultado.
    reversed_metrics = dict(reversed(list(metrics.items())))
    assert recommend(priority, reversed_metrics) == rec
    # Sem empate (uma squad bem pior), não aparece aviso de empate.
    sem_empate = recommend(priority, {winner: same, loser: _m(10, 5, 90)})
    assert sem_empate["profile"] == winner and "Empata" not in sem_empate["reason"]


def test_prioridade_invalida_da_erro():
    with pytest.raises(ValueError):
        recommend("pressa", {"segura": _m(1, 1, 1)})


def test_api_devolve_recomendacoes_no_exemplo_e_no_projeto_de_briefing():
    exemplo = client.get("/api/projects/agenda-clinica/squads").json()
    assert set(exemplo["recommendations"]) == set(PRIORITIES)
    assert exemplo["recommendations"]["prazo"]["profile"] == "segura"

    corpo = {
        "name": "App de teste",
        "duration_weeks": 6,
        "roles": [
            {"skill": "frontend", "min_level": 2, "hours_per_week": 6},
            {"skill": "backend", "min_level": 3, "hours_per_week": 8, "critical": True},
            {"skill": "gestao", "min_level": 2, "hours_per_week": 4},
        ],
    }
    custom = client.post("/api/squads/build", json=corpo).json()
    recs = custom["recommendations"]
    assert set(recs) == set(PRIORITIES)
    for rec in recs.values():
        assert rec["profile"] in custom["squads"]
        assert rec["reason"]
    # A recomendação bate com a função pura aplicada aos números devolvidos.
    metrics = {p: sq["metrics"] for p, sq in custom["squads"].items()}
    assert recs == recommend_all(metrics)
