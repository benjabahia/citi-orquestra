"""Teste de estresse ("e se alguém sair?")."""
from fastapi.testclient import TestClient

from app.api import app

client = TestClient(app)

CUSTOM = {
    "name": "App da clínica",
    "description": "",
    "duration_weeks": 6,
    "roles": [
        {"skill": "frontend", "min_level": 2, "hours_per_week": 6, "critical": False},
        {"skill": "backend", "min_level": 3, "hours_per_week": 8, "critical": True},
        {"skill": "qa", "min_level": 2, "hours_per_week": 5, "critical": False},
    ],
    "extra_members": [],
}


def _stress(project_id, squad, custom=None):
    body = {"profile": squad["profile"], "assignments": squad["assignments"], "custom": custom}
    r = client.post(f"/api/projects/{project_id}/stress", json=body)
    assert r.status_code == 200, r.text
    return r.json()


def test_unico_backend_do_projeto_pagamentos_e_o_mais_fragil():
    """No projeto armadilha, tirar o único back-end de referência (Rafael) é o pior caso."""
    squad = client.get("/api/projects/pagamentos/squads").json()["squads"]["segura"]
    r = _stress("pagamentos", squad)
    primeiro = r["results"][0]
    assert primeiro["name"] == "Rafael Teixeira"
    assert primeiro["delta_risco"] > 0 and primeiro["delta_entrega"] < 0
    assert "Rafael Teixeira" in r["weakest_sentence"]
    riscos = [x["risco_after"] for x in r["results"]]
    assert riscos == sorted(riscos, reverse=True)


def test_lista_cobre_todos_os_membros_da_squad():
    """Uma linha por pessoa do squad, em qualquer perfil."""
    for profile, squad in client.get("/api/projects/loja-cosmeticos/squads").json()["squads"].items():
        r = _stress("loja-cosmeticos", squad)
        ids = {x["member_id"] for x in r["results"]}
        assert ids == {a for a in squad["assignments"] if a}
        assert len(r["results"]) == len(ids)


def test_vaga_em_aberto_nao_entra_na_lista():
    """Papel vago não tem ninguém para sair."""
    squad = client.get("/api/projects/pagamentos/squads").json()["squads"]["segura"]
    squad["assignments"][3] = None
    r = _stress("pagamentos", squad)
    assert len(r["results"]) == 3


def test_funciona_em_projeto_criado_por_briefing():
    """Projeto custom: o corpo traz o projeto e o resultado cobre o squad montado."""
    built = client.post("/api/squads/build", json=CUSTOM).json()
    squad = built["squads"]["balanceada"]
    r = _stress("custom", squad, CUSTOM)
    assert {x["member_id"] for x in r["results"]} == {a for a in squad["assignments"] if a}
    assert r["weakest_sentence"]


def test_estresse_rejeita_pedido_invalido():
    """Perfil inválido devolve 422."""
    r = client.post(
        "/api/projects/pagamentos/stress",
        json={"profile": "x", "assignments": [None] * 4},
    )
    assert r.status_code == 422
