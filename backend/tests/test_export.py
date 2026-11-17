"""Exportar o resultado: resumo do squad para colar no chat."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api import app
from app.members_csv import parse_members_csv
from app.summary import DECLARED_NOTE, EXAMPLE_NOTE, _hours, _round

client = TestClient(app)
DADOS = Path(__file__).parent / "dados"

ROLES = [
    {"skill": "frontend", "min_level": 2, "hours_per_week": 6, "critical": False},
    {"skill": "backend", "min_level": 3, "hours_per_week": 8, "critical": True},
    {"skill": "qa", "min_level": 2, "hours_per_week": 5, "critical": False},
]


def custom(sheet=None, roles=ROLES):
    return {
        "name": "Projeto do resumo", "description": "", "duration_weeks": 6,
        "roles": roles, "extra_members": [], "replace_members": sheet,
    }


def planilha():
    return parse_members_csv((DADOS / "membros-teste-horas.csv").read_text(encoding="utf-8"))["members"]


def resumo(project_id, squad, body_custom=None, weakest=False):
    body = {
        "project_id": project_id, "profile": squad["profile"], "assignments": squad["assignments"],
        "custom": body_custom, "include_weakest": weakest,
    }
    r = client.post("/api/export/summary", json=body)
    assert r.status_code == 200, r.text
    return r.json()["text"]


def numeros(squad):
    m = squad["metrics"]
    return (f"Entrega {_round(m['entrega'])} · Crescimento {_round(m['crescimento'])} · "
            f"Risco {_round(m['risco'])}")


def test_projeto_pronto_traz_todos_os_papeis_pessoas_e_numeros():
    data = client.get("/api/projects/pagamentos/squads").json()
    for squad in data["squads"].values():
        texto = resumo("pagamentos", squad)
        assert data["project"]["name"] in texto
        assert f"{data['project']['duration_weeks']} semanas" in texto
        assert numeros(squad) in texto
        for slot in squad["slots"]:
            assert slot["skill_label"] in texto
            assert slot["member_name"] in texto
        assert EXAMPLE_NOTE in texto
        assert DECLARED_NOTE not in texto


def test_horas_livres_e_exigidas_batem_com_a_squad():
    squad = client.get("/api/projects/loja-cosmeticos/squads").json()["squads"]["balanceada"]
    texto = resumo("loja-cosmeticos", squad)
    for load in squad["metrics"]["loads"]:
        assert f"{_hours(load['capacity'])} h livres · {_hours(load['demand'])} h exigidas" in texto


def test_mentorias_aparecem_com_quem_ensina_quem():
    squad = client.get("/api/projects/agenda-clinica/squads").json()["squads"]["evolutiva"]
    assert squad["metrics"]["mentorships"], "o teste precisa de um squad com mentoria"
    texto = resumo("agenda-clinica", squad)
    nomes = {s["member_id"]: s["member_name"] for s in squad["slots"]}
    for x in squad["metrics"]["mentorships"]:
        assert f"{nomes[x['mentor_id']]} ensina {nomes[x['mentee_id']]}" in texto


def test_squad_sem_mentoria_diz_que_nao_precisa():
    squad = client.get("/api/projects/pagamentos/squads").json()["squads"]["segura"]
    assert not squad["metrics"]["mentorships"]
    assert "Nenhuma" in resumo("pagamentos", squad)


def test_marca_de_falta_de_horas_quando_ha():
    """Só 3 pessoas para 3 papéis e todas com poucas horas: o resumo avisa a falta."""
    sheet = [
        {"name": "Ana", "months_in_citi": 20, "skills": {"frontend": 3}, "learning_goals": [], "weekly_hours": 4},
        {"name": "Bia", "months_in_citi": 20, "skills": {"backend": 4}, "learning_goals": [], "weekly_hours": 6},
        {"name": "Cau", "months_in_citi": 20, "skills": {"qa": 3}, "learning_goals": [], "weekly_hours": 2},
    ]
    body = custom(sheet=sheet)
    squad = client.post("/api/squads/build", json=body).json()["squads"]["segura"]
    texto = resumo("custom", squad, body)
    assert "faltam 2 h" in texto      # Ana: 4 livres, 6 exigidas
    assert "faltam 3 h" in texto      # Cau: 2 livres, 5 exigidas
    assert texto.count("⚠") == 3


def test_sem_falta_de_horas_nao_aparece_a_marca():
    squad = client.get("/api/projects/pagamentos/squads").json()["squads"]["segura"]
    sobrecarga = any(f["kind"] == "sobrecarga" for f in squad["metrics"]["factors"])
    texto = resumo("pagamentos", squad)
    assert ("⚠" in texto) == sobrecarga


def test_projeto_por_briefing_com_planilha():
    body = custom(sheet=planilha())
    built = client.post("/api/squads/build", json=body).json()
    for squad in built["squads"].values():
        texto = resumo("custom", squad, body)
        assert numeros(squad) in texto
        assert DECLARED_NOTE in texto
        assert "Projeto do resumo" in texto
        for slot in squad["slots"]:
            assert slot["skill_label"] in texto and slot["member_name"] in texto


def test_resume_o_estado_atual_depois_de_uma_troca():
    """O texto usa quem ocupa cada papel agora, não a sugestão original."""
    data = client.get("/api/projects/pagamentos/squads").json()
    squad = data["squads"]["segura"]
    body = {"project_id": "pagamentos", "profile": "segura", "assignments": squad["assignments"], "role_index": 0}
    novo = client.post("/api/projects/pagamentos/whatif", json=body).json()["substitutes"][0]
    aplicado = client.post("/api/projects/pagamentos/apply", json={**body, "member_id": novo["member_id"]}).json()["squad"]
    texto = resumo("pagamentos", aplicado)
    assert novo["name"] in texto
    assert numeros(aplicado) in texto


def test_ponto_mais_fragil_so_com_o_teste_de_estresse():
    squad = client.get("/api/projects/pagamentos/squads").json()["squads"]["segura"]
    sem = resumo("pagamentos", squad)
    com = resumo("pagamentos", squad, weakest=True)
    assert "Ponto mais frágil" not in sem
    assert "Ponto mais frágil" in com and "Rafael Teixeira" in com
    # a frase é a mesma do teste de estresse
    body = {"profile": "segura", "assignments": squad["assignments"], "custom": None}
    frase = client.post("/api/projects/pagamentos/stress", json=body).json()["weakest_sentence"]
    assert frase in com


def test_vaga_em_aberto_aparece_no_texto():
    squad = client.get("/api/projects/pagamentos/squads").json()["squads"]["segura"]
    squad["assignments"][3] = None
    papel = squad["slots"][3]["skill_label"]
    assert f"{papel}: vaga em aberto" in resumo("pagamentos", squad)


def test_arredondamento_e_horas_como_no_site():
    assert _round(12.5) == 13 and _round(13.5) == 14 and _round(0.4) == 0
    assert _hours(6.0) == "6" and _hours(7.5) == "7,5" and _hours(0.0) == "0"


@pytest.mark.parametrize("mudanca", [
    {"project_id": "nao-existe"},
    {"profile": "inexistente"},
    {"assignments": ["m01"]},
    {"assignments": ["fantasma", "fantasma", "fantasma", "fantasma"]},
])
def test_pedido_invalido_devolve_422(mudanca):
    squad = client.get("/api/projects/pagamentos/squads").json()["squads"]["segura"]
    body = {"project_id": "pagamentos", "profile": "segura", "assignments": squad["assignments"], "custom": None}
    body.update(mudanca)
    assert client.post("/api/export/summary", json=body).status_code == 422


def test_pedido_sem_campos_obrigatorios_devolve_422():
    assert client.post("/api/export/summary", json={}).status_code == 422
    assert client.post("/api/export/summary", json={"profile": "segura"}).status_code == 422


def test_projeto_por_briefing_invalido_devolve_422():
    body = custom(sheet=planilha(), roles=[{"skill": "magia", "min_level": 2, "hours_per_week": 5, "critical": False}] * 3)
    r = client.post("/api/export/summary", json={
        "project_id": "custom", "profile": "segura", "assignments": [None, None, None], "custom": body,
    })
    assert r.status_code == 422
