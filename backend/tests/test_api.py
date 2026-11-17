"""Testes da API: o site depende destas respostas."""
import pytest
from fastapi.testclient import TestClient

from app.api import app

client = TestClient(app)


def test_api_saudavel_e_lista_projetos():
    """A API responde e lista os 6 projetos."""
    assert client.get("/api/health").json() == {"status": "ok"}
    projetos = client.get("/api/projects").json()
    assert len(projetos) == 6
    assert all(p["roles"] for p in projetos)


def test_api_devolve_tres_squads_completas():
    """GET squads devolve segura, evolutiva e balanceada com medidores."""
    r = client.get("/api/projects/pagamentos/squads").json()
    assert set(r["squads"]) == {"segura", "evolutiva", "balanceada"}
    segura = r["squads"]["segura"]
    assert segura["slots"][0]["member_name"] == "Rafael Teixeira"
    assert 0 <= segura["metrics"]["risco"] <= 100
    assert len(segura["metrics"]["role_coverage"]) == len(segura["slots"])


def test_api_projeto_inexistente_da_404():
    """Projeto que não existe devolve erro 404 claro."""
    assert client.get("/api/projects/nao-existe/squads").status_code == 404


def test_api_fluxo_de_substituicao_no_projeto_armadilha():
    """Fluxo da demo: ver substitutos do Rafael e aplicar a troca."""
    base = client.get("/api/projects/pagamentos/squads").json()["squads"]["segura"]
    corpo = {"profile": "segura", "assignments": base["assignments"], "role_index": 0}

    lista = client.post("/api/projects/pagamentos/whatif", json=corpo).json()
    assert lista["substitutes"]
    melhor = lista["substitutes"][0]
    assert melhor["delta_entrega"] < 0 and melhor["delta_risco"] > 0

    novo = client.post(
        "/api/projects/pagamentos/apply", json={**corpo, "member_id": melhor["member_id"]}
    ).json()["squad"]
    assert novo["slots"][0]["member_id"] == melhor["member_id"]
    assert novo["metrics"]["risco"] == pytest.approx(melhor["metrics"]["risco"])

    vago = client.post("/api/projects/pagamentos/apply", json=corpo).json()["squad"]
    assert vago["slots"][0]["member_id"] is None
    assert vago["metrics"]["risco"] > base["metrics"]["risco"]


def test_api_rejeita_pedidos_invalidos():
    """Perfil, papel ou membro inválidos devolvem erro 422, nunca quebram."""
    base = client.get("/api/projects/pagamentos/squads").json()["squads"]["segura"]
    ok = {"profile": "segura", "assignments": base["assignments"], "role_index": 0}
    assert client.post("/api/projects/pagamentos/whatif", json={**ok, "profile": "x"}).status_code == 422
    assert client.post("/api/projects/pagamentos/whatif", json={**ok, "role_index": 99}).status_code == 422
    assert client.post("/api/projects/pagamentos/whatif", json={**ok, "assignments": ["zzz"] * 4}).status_code == 422
    assert client.post("/api/projects/pagamentos/apply", json={**ok, "member_id": "zzz"}).status_code == 422


def test_site_e_servido_pelo_mesmo_servidor():
    """A página inicial do site abre na raiz (quando o front-end foi construído)."""
    from app.api import FRONTEND_DIST

    if not FRONTEND_DIST.exists():
        pytest.skip("front-end ainda não construído")
    r = client.get("/")
    assert r.status_code == 200 and "CITi Orquestra" in r.text
