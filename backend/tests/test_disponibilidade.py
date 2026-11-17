"""Disponibilidade real de horas: perfil, planilha, ajuste do gerente e cálculo."""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.ai.profile_chat import QUESTIONS, ProfileError, build_profile
from app.api import app
from app.members_csv import HEADER, TEMPLATE_HEADER, parse_members_csv, template_csv
from app.models import Availability

client = TestClient(app)
DADOS = Path(__file__).parent / "dados"


def ler(nome):
    return (DADOS / nome).read_text(encoding="utf-8")


RESPOSTAS = {"areas": ["frontend"], "levels": {"frontend": 2}, "months": 9, "goals": [], "open": ""}

ROLES = [
    {"skill": "frontend", "min_level": 2, "hours_per_week": 6, "critical": False},
    {"skill": "backend", "min_level": 3, "hours_per_week": 8, "critical": True},
    {"skill": "qa", "min_level": 2, "hours_per_week": 5, "critical": False},
]


def custom(sheet=None, extra=(), availability=None, weeks=6, roles=ROLES):
    body = {
        "name": "Projeto das horas",
        "description": "",
        "duration_weeks": weeks,
        "roles": roles,
        "extra_members": list(extra),
        "replace_members": sheet,
    }
    if availability is not None:
        body["availability"] = availability
    return body


def planilha_horas():
    r = parse_members_csv(ler("membros-teste-horas.csv"))
    assert r["ok"], r["errors"]
    return r["members"]


def build(body):
    r = client.post("/api/squads/build", json=body)
    assert r.status_code == 200, r.text
    return r.json()


def team(body):
    r = client.post("/api/squads/team", json=body)
    assert r.status_code == 200, r.text
    return {m["name"]: m for m in r.json()["members"]}


# ---------------- perfil do membro ----------------
def test_formulario_tem_as_duas_perguntas_novas():
    ids = [q["id"] for q in QUESTIONS]
    assert "hours" in ids and "away" in ids
    horas = next(q for q in QUESTIONS if q["id"] == "hours")
    assert horas["min"] == 0 and horas["max"] == 40 and horas["suggestions"] == [2, 4, 6, 8, 10, 12]
    fora = next(q for q in QUESTIONS if q["id"] == "away")
    assert fora["min"] == 0 and fora["max"] == 12


def test_perfil_com_os_campos_novos():
    p = build_profile("Ana", {**RESPOSTAS, "weekly_hours": 4.5, "unavailable_weeks": 2})
    assert p["weekly_hours"] == 4.5 and p["unavailable_weeks"] == 2


def test_perfil_antigo_sem_os_campos_vale_8h_e_0_semanas():
    p = build_profile("Ana", RESPOSTAS)
    assert p["weekly_hours"] == 8.0 and p["unavailable_weeks"] == 0
    r = client.post("/api/profile/interpret", json={"name": "Ana", "answers": RESPOSTAS})
    assert r.status_code == 200
    assert r.json()["profile"]["weekly_hours"] == 8.0


@pytest.mark.parametrize("campos", [
    {"weekly_hours": -1}, {"weekly_hours": 41}, {"weekly_hours": "muitas"},
    {"unavailable_weeks": -1}, {"unavailable_weeks": 13}, {"unavailable_weeks": 1.5},
])
def test_perfil_com_horas_invalidas_e_recusado(campos):
    with pytest.raises(ProfileError):
        build_profile("Ana", {**RESPOSTAS, **campos})
    r = client.post("/api/profile/interpret", json={"name": "Ana", "answers": {**RESPOSTAS, **campos}})
    assert r.status_code == 422


def test_perfil_antigo_salvo_no_navegador_continua_valido_no_projeto():
    """Perfil guardado antes desta mudança (sem os campos) entra com 8 h."""
    antigo = {"name": "Perfil Antigo", "months_in_citi": 9, "skills": {"qa": 3}, "learning_goals": []}
    pessoas = team(custom(extra=[antigo]))
    assert pessoas["Perfil Antigo"]["weekly_hours"] == 8.0
    assert pessoas["Perfil Antigo"]["source"] == "perfil"


def test_perfil_do_chat_usa_as_horas_declaradas():
    novo = {"name": "Perfil Novo", "months_in_citi": 9, "skills": {"qa": 3}, "learning_goals": [],
            "weekly_hours": 3, "unavailable_weeks": 0}
    assert team(custom(extra=[novo]))["Perfil Novo"]["weekly_hours"] == 3.0
    ruim = {**novo, "weekly_hours": 50}
    assert client.post("/api/squads/build", json=custom(extra=[ruim])).status_code == 422


# ---------------- planilha ----------------
def test_csv_sem_as_colunas_novas_continua_funcionando():
    # Arquivo no formato antigo: o mesmo membros-teste.csv sem as duas últimas colunas.
    linhas = ler("membros-teste.csv").strip().split("\n")
    antigo = "\n".join([",".join(HEADER)] + [",".join(l.split(",")[:-2]) for l in linhas[1:]]) + "\n"
    r = parse_members_csv(antigo)
    assert r["ok"], r["errors"]
    assert all(m["weekly_hours"] == 8.0 and m["unavailable_weeks"] == 0 for m in r["members"])


def test_csv_com_as_colunas_novas():
    membros = {m["name"]: m for m in planilha_horas()}
    assert len(membros) == 14
    assert membros["Bruno Cavalcanti"]["weekly_hours"] == 4.0
    assert membros["Felipe Barros"]["weekly_hours"] == 7.5
    assert membros["Felipe Barros"]["unavailable_weeks"] == 2
    assert membros["Mateus Oliveira"]["weekly_hours"] == 8.0     # célula vazia = padrão
    assert membros["Mateus Oliveira"]["unavailable_weeks"] == 0


def test_csv_ponto_e_virgula_aceita_decimal_com_virgula():
    texto = ";".join(TEMPLATE_HEADER) + "\nAna;5;3;;;;;;;;;7,5;1\nBia;7;;2;;;;;;;;4;0\nCau;9;;;;;;;;4;;10;0\n"
    r = parse_members_csv(texto)
    assert r["ok"], r["errors"]
    assert r["members"][0]["weekly_hours"] == 7.5 and r["members"][0]["unavailable_weeks"] == 1


def test_modelo_traz_as_colunas_novas_e_e_valido():
    assert template_csv().splitlines()[0] == ",".join(TEMPLATE_HEADER)
    assert TEMPLATE_HEADER[-2:] == ["horas_livres_por_semana", "semanas_fora"]
    r = parse_members_csv(template_csv())
    assert r["ok"] and r["members"][1]["unavailable_weeks"] == 1


def test_csv_com_erros_de_horas_mostra_linha_e_coluna():
    r = parse_members_csv(ler("membros-horas-com-erros.csv"))
    assert r["ok"] is False and r["members"] == []
    por_linha = {e["line"]: e for e in r["errors"]}
    esperado = {
        2: ("horas_livres_por_semana", "negativo"),     # -3
        3: ("horas_livres_por_semana", "não é um número"),  # "muitas"
        4: ("horas_livres_por_semana", "limite de 40"),  # 45
        5: ("semanas_fora", "casas decimais"),           # 1.5
        6: ("semanas_fora", "limite de 12"),             # 20
        7: ("semanas_fora", "negativo"),                 # -1
    }
    assert set(por_linha) == set(esperado)
    for linha, (coluna, trecho) in esperado.items():
        erro = por_linha[linha]
        assert erro["column"] == coluna
        assert trecho in erro["message"]
        assert erro["message"].startswith(f"Linha {linha}, coluna '{coluna}'")


def test_csv_antigo_com_erros_continua_acusando_os_mesmos_erros():
    msgs = " | ".join(e["message"] for e in parse_members_csv(ler("membros-com-erros.csv"))["errors"])
    assert "repetido" in msgs and "nível '7'" in msgs and "nome está vazio" in msgs and "magia" in msgs
    assert "horas" not in msgs


# ---------------- cálculo ----------------
def test_duas_semanas_com_uma_fora_e_metade_das_horas():
    assert Availability(8, unavailable_weeks=1).effective_hours(2) == pytest.approx(4.0)
    sheet = [
        {"name": "Ana", "months_in_citi": 20, "skills": {"frontend": 3}, "learning_goals": [], "weekly_hours": 8, "unavailable_weeks": 1},
        {"name": "Bia", "months_in_citi": 20, "skills": {"backend": 3}, "learning_goals": [], "weekly_hours": 8, "unavailable_weeks": 0},
        {"name": "Cau", "months_in_citi": 20, "skills": {"qa": 3}, "learning_goals": [], "weekly_hours": 8, "unavailable_weeks": 0},
    ]
    body = custom(sheet=sheet, weeks=2)
    assert team(body)["Ana"]["available_hours"] == pytest.approx(4.0)
    segura = build(body)["squads"]["segura"]
    ana = next(l for l in segura["metrics"]["loads"] if l["member_id"] == "imp1")
    assert ana["capacity"] == pytest.approx(4.0)


def test_disponibilidade_da_planilha_entra_no_calculo():
    sheet = planilha_horas()
    data = build(custom(sheet=sheet))
    declaradas = {f"imp{i + 1}": m for i, m in enumerate(sheet)}
    for squad in data["squads"].values():
        for load in squad["metrics"]["loads"]:
            m = declaradas[load["member_id"]]
            esperado = Availability(m["weekly_hours"], m["unavailable_weeks"]).effective_hours(6)
            assert load["capacity"] == pytest.approx(round(esperado, 2))
        # Natália declarou 0 h: nunca é escolhida
        assert "imp13" not in squad["assignments"]


def test_sobrecarga_quando_horas_livres_sao_menores_que_as_exigidas():
    """Só 3 pessoas para 3 papéis, todas com poucas horas: o sistema acusa a sobrecarga."""
    sheet = [
        {"name": "Ana", "months_in_citi": 20, "skills": {"frontend": 3}, "learning_goals": [], "weekly_hours": 4},
        {"name": "Bia", "months_in_citi": 20, "skills": {"backend": 4}, "learning_goals": [], "weekly_hours": 6},
        {"name": "Cau", "months_in_citi": 20, "skills": {"qa": 3}, "learning_goals": [], "weekly_hours": 2},
    ]
    segura = build(custom(sheet=sheet))["squads"]["segura"]
    sobrecargas = [f for f in segura["metrics"]["factors"] if f["kind"] == "sobrecarga"]
    assert {f["member_id"] for f in sobrecargas} == {"imp1", "imp2", "imp3"}
    assert any("6h por semana e há 4.0h" in f["message"] for f in sobrecargas)


def test_ajuste_do_gerente_vence_o_declarado():
    sheet = planilha_horas()
    sem_ajuste = custom(sheet=sheet)
    com_ajuste = custom(sheet=sheet, availability={"imp2": {"weekly_hours": 20, "unavailable_weeks": 0}})
    assert team(sem_ajuste)["Bruno Cavalcanti"]["weekly_hours"] == 4.0
    assert team(com_ajuste)["Bruno Cavalcanti"]["weekly_hours"] == 20.0
    for squad in build(com_ajuste)["squads"].values():
        for load in squad["metrics"]["loads"]:
            if load["member_id"] == "imp2":
                assert load["capacity"] == 20.0


def test_ajuste_do_gerente_vale_para_membros_de_exemplo():
    body = custom(availability={"m02": {"weekly_hours": 0, "unavailable_weeks": 0}})
    assert team(body)["Rafael Teixeira"]["weekly_hours"] == 0
    for squad in build(body)["squads"].values():
        assert "m02" not in squad["assignments"]


@pytest.mark.parametrize("ajuste,status", [
    ({"zz9": {"weekly_hours": 5}}, 422),                              # membro que não existe
    ({"imp1": {"weekly_hours": 41}}, 422),
    ({"imp1": {"weekly_hours": 5, "unavailable_weeks": 13}}, 422),
])
def test_ajuste_invalido_e_recusado(ajuste, status):
    r = client.post("/api/squads/build", json=custom(sheet=planilha_horas(), availability=ajuste))
    assert r.status_code == status


def test_troca_aplicar_e_estresse_usam_as_mesmas_horas():
    """O corpo `custom` leva a disponibilidade; as outras telas chegam aos mesmos números."""
    body = custom(sheet=planilha_horas(), availability={"imp4": {"weekly_hours": 3, "unavailable_weeks": 0}})
    squad = build(body)["squads"]["balanceada"]
    state = {"profile": "balanceada", "assignments": squad["assignments"], "custom": body}

    w = client.post("/api/projects/custom/whatif", json={**state, "role_index": 0}).json()
    assert w["current"]["metrics"] == squad["metrics"]
    for sub in w["substitutes"]:
        load = next(l for l in sub["metrics"]["loads"] if l["member_id"] == sub["member_id"])
        if sub["member_id"] == "imp4":
            assert load["capacity"] == 3.0

    same = client.post("/api/projects/custom/apply",
                       json={**state, "role_index": 0, "member_id": squad["assignments"][0]}).json()
    assert same["squad"]["metrics"] == squad["metrics"]

    s = client.post("/api/projects/custom/stress", json=state).json()
    assert all(row["risco_before"] == squad["metrics"]["risco"] for row in s["results"])

    # Mesmo squad, com e sem o ajuste no corpo: as horas de quem foi ajustado mudam em todas as telas.
    alvo = squad["assignments"][1]
    ajustado = {**body, "availability": {alvo: {"weekly_hours": 1, "unavailable_weeks": 0}}}
    st2 = {**state, "custom": ajustado}
    caps = lambda m: {l["member_id"]: l["capacity"] for l in m["loads"]}
    w2 = client.post("/api/projects/custom/whatif", json={**st2, "role_index": 0}).json()
    a2 = client.post("/api/projects/custom/apply",
                     json={**st2, "role_index": 0, "member_id": squad["assignments"][0]}).json()
    s2 = client.post("/api/projects/custom/stress", json=st2).json()
    assert caps(squad["metrics"])[alvo] != 1.0
    assert caps(w2["current"]["metrics"])[alvo] == 1.0
    assert caps(a2["squad"]["metrics"])[alvo] == 1.0
    assert w2["current"]["metrics"] == a2["squad"]["metrics"]
    assert all(row["risco_before"] == w2["current"]["metrics"]["risco"] for row in s2["results"])


def test_aplicar_troca_por_pessoa_com_poucas_horas_acusa_sobrecarga():
    body = custom(sheet=planilha_horas())
    squad = build(body)["squads"]["segura"]
    i = next(k for k, r in enumerate(ROLES) if r["skill"] == "frontend")
    # Larissa (imp11) declarou 2 h; o papel de front-end pede 6 h
    r = client.post("/api/projects/custom/apply", json={
        "profile": "segura", "assignments": squad["assignments"], "role_index": i,
        "member_id": "imp11", "custom": body,
    }).json()
    msgs = [f["message"] for f in r["squad"]["metrics"]["factors"] if f["kind"] == "sobrecarga"]
    assert any("Larissa Vieira" in m and "2.0h" in m for m in msgs)


def test_tabela_da_equipe_lista_quem_esta_em_jogo():
    com_planilha = client.post("/api/squads/team", json=custom(sheet=planilha_horas())).json()
    assert len(com_planilha["members"]) == 14
    assert {m["source"] for m in com_planilha["members"]} == {"planilha"}
    sem_planilha = client.post("/api/squads/team", json=custom()).json()["members"]
    assert len(sem_planilha) == 24 and {m["source"] for m in sem_planilha} == {"exemplo"}


# ---------------- projetos prontos não mudam ----------------
def test_seis_projetos_prontos_tem_resultado_identico_ao_de_antes():
    antes = json.loads(ler("prontos_antes.json"))
    assert len(antes) == 6
    for project_id, esperado in antes.items():
        agora = client.get(f"/api/projects/{project_id}/squads").json()
        assert agora == esperado, project_id
