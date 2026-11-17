"""Testes da planilha de membros: validação do CSV e o fluxo completo pela API."""
from fastapi.testclient import TestClient

from app.api import app
from app.members_csv import HEADER, parse_members_csv, template_csv

client = TestClient(app)

CABECALHO = ",".join(HEADER)


def planilha(*linhas):
    return "\n".join([CABECALHO, *linhas]) + "\n"


BOA = planilha(
    "Ana Souza,18,3,1,0,2,0,0,0,0,backend;devops",
    "Bruno Lima,4,1,2,1,0,0,1,0,0,banco_dados",
    "Carla Dias,30,0,4,3,0,1,2,2,3,gestao",
    "Diego Reis,12,2,2,0,1,3,0,0,0,",
)


def erros(texto):
    r = parse_members_csv(texto)
    assert r["ok"] is False and r["members"] == []
    return r["errors"]


def mensagens(texto):
    return " | ".join(e["message"] for e in erros(texto))


# ---------------- arquivo bom ----------------
def test_arquivo_bom_gera_membros():
    r = parse_members_csv(BOA)
    assert r["ok"] and r["errors"] == []
    assert [m["name"] for m in r["members"]] == ["Ana Souza", "Bruno Lima", "Carla Dias", "Diego Reis"]
    ana = r["members"][0]
    assert ana["months_in_citi"] == 18
    assert ana["skills"] == {"frontend": 3, "backend": 1, "ux_ui": 2}  # níveis 0 não entram
    assert ana["learning_goals"] == ["backend", "devops"]
    assert r["members"][3]["learning_goals"] == []


def test_modelo_para_baixar_e_valido():
    r = parse_members_csv(template_csv())
    assert r["ok"] and len(r["members"]) == 3


def test_aceita_bom_excel_ponto_e_virgula_e_celula_vazia():
    texto = "﻿" + ";".join(HEADER) + "\nAna;5;3;;;;;;;;backend|qa\nBia;7;;2;;;;;;;\nCau;9;;;;;;;;4;\n"
    r = parse_members_csv(texto)
    assert r["ok"], r["errors"]
    assert r["members"][0]["skills"] == {"frontend": 3}
    assert r["members"][0]["learning_goals"] == ["backend", "qa"]


# ---------------- arquivos ruins ----------------
def test_nivel_fora_de_0_a_4_informa_linha_e_coluna():
    e = erros(BOA.replace("Bruno Lima,4,1,2", "Bruno Lima,4,1,7"))
    assert (e[0]["line"], e[0]["column"]) == (3, "backend")
    assert "de 0 a 4" in e[0]["message"] and "Linha 3" in e[0]["message"]


def test_nivel_nao_numerico_e_negativo():
    assert "de 0 a 4" in mensagens(BOA.replace("Bruno Lima,4,1,2", "Bruno Lima,4,alto,2"))
    assert "de 0 a 4" in mensagens(BOA.replace("Bruno Lima,4,1,2", "Bruno Lima,4,-1,2"))


def test_habilidade_desconhecida_na_meta():
    e = erros(BOA.replace("banco_dados\n", "cozinha\n"))
    assert (e[0]["line"], e[0]["column"]) == (3, "metas")
    assert "habilidade desconhecida 'cozinha'" in e[0]["message"]


def test_coluna_desconhecida_e_coluna_faltando():
    assert "coluna desconhecida" in mensagens(BOA.replace(",devops,", ",cozinha,", 1))
    sem_qa = BOA.replace(",qa", "", 1)
    assert "coluna 'qa'" in mensagens(sem_qa) or "'qa'" in mensagens(sem_qa)


def test_nome_vazio():
    e = erros(BOA.replace("Bruno Lima", ""))
    assert (e[0]["line"], e[0]["column"]) == (3, "nome")
    assert "vazio" in e[0]["message"]


def test_nome_repetido_mesmo_com_caixa_diferente():
    e = erros(BOA.replace("Diego Reis", "ana souza"))
    assert (e[0]["line"], e[0]["column"]) == (5, "nome")
    assert "repetido" in e[0]["message"] and "linha 2" in e[0]["message"]


def test_meses_invalidos():
    assert "meses_no_citi" in mensagens(BOA.replace("Ana Souza,18", "Ana Souza,muitos"))
    assert "meses_no_citi" in mensagens(BOA.replace("Ana Souza,18", "Ana Souza,"))


def test_menos_de_3_pessoas():
    dois = planilha("Ana,5,3,0,0,0,0,0,0,0,", "Bia,6,0,3,0,0,0,0,0,0,")
    assert "pelo menos 3" in mensagens(dois)
    assert "pelo menos 3" in mensagens(planilha())  # só cabeçalho


def test_mais_de_200_linhas():
    linhas = [f"Pessoa {i},10,2,0,0,0,0,0,0,0," for i in range(201)]
    assert "máximo é 200" in mensagens(planilha(*linhas))
    ok = [f"Pessoa {i},10,2,0,0,0,0,0,0,0," for i in range(200)]
    assert parse_members_csv(planilha(*ok))["ok"]


def test_arquivo_vazio_e_varios_erros_juntos():
    assert "vazio" in mensagens("   \n")
    assert "vazio" in mensagens(",,,\n")
    ruim = planilha("Ana,5,9,0,0,0,0,0,0,0,xx", "Ana,5,0,0,0,0,0,0,0,0,", ",3,0,0,0,0,0,0,0,0,")
    e = erros(ruim)
    assert len(e) >= 4  # nível, meta, nome repetido, nome vazio: tudo de uma vez


# ---------------- fluxo completo pela API ----------------
def corpo_projeto(membros):
    return {
        "name": "Projeto da planilha",
        "description": "",
        "duration_weeks": 6,
        "roles": [
            {"skill": "backend", "min_level": 3, "hours_per_week": 6, "critical": True},
            {"skill": "frontend", "min_level": 2, "hours_per_week": 5, "critical": False},
            {"skill": "gestao", "min_level": 2, "hours_per_week": 4, "critical": False},
        ],
        "extra_members": [],
        "replace_members": membros,
    }


def test_endpoint_de_importacao_e_modelo():
    ok = client.post("/api/members/import", json={"text": BOA}).json()
    assert ok["ok"] and len(ok["members"]) == 4
    ruim = client.post("/api/members/import", json={"text": BOA.replace("Bruno Lima,4,1,2", "Bruno Lima,4,1,9")}).json()
    assert not ruim["ok"] and ruim["errors"][0]["line"] == 3
    assert client.get("/api/members/template").json()["csv"].startswith(CABECALHO)


def test_fluxo_completo_planilha_substitui_os_24_de_exemplo():
    membros = client.post("/api/members/import", json={"text": BOA}).json()["members"]
    corpo = corpo_projeto(membros)
    r = client.post("/api/squads/build", json=corpo)
    assert r.status_code == 200
    dados = r.json()
    nomes_planilha = {m["name"] for m in membros}
    usados = {s["member_name"] for sq in dados["squads"].values() for s in sq["slots"] if s["member_name"]}
    assert usados and usados <= nomes_planilha  # ninguém dos 24 de exemplo aparece

    # trocar, aplicar e testar estresse também usam a planilha (projeto "custom")
    squad = dados["squads"]["segura"]
    base = {"profile": "segura", "assignments": squad["assignments"], "custom": corpo}
    sub = client.post("/api/projects/custom/whatif", json={**base, "role_index": 0}).json()
    assert all(s["name"] in nomes_planilha for s in sub["substitutes"])
    stress = client.post("/api/projects/custom/stress", json=base).json()
    assert {x["name"] for x in stress["results"]} <= nomes_planilha
    ap = client.post("/api/projects/custom/apply", json={**base, "role_index": 0, "member_id": None})
    assert ap.status_code == 200 and ap.json()["squad"]["assignments"][0] is None


def test_sem_planilha_continua_usando_os_dados_de_exemplo():
    corpo = corpo_projeto(None)
    dados = client.post("/api/squads/build", json=corpo).json()
    usados = {s["member_name"] for sq in dados["squads"].values() for s in sq["slots"] if s["member_name"]}
    exemplo = {m["name"] for m in client.get("/api/members").json()}
    assert usados and usados <= exemplo


def test_projetos_prontos_nao_mudam_e_planilha_pequena_e_rejeitada():
    antes = client.get("/api/projects/pagamentos/squads").json()
    client.post("/api/squads/build", json=corpo_projeto(parse_members_csv(BOA)["members"]))
    assert client.get("/api/projects/pagamentos/squads").json() == antes
    dois = parse_members_csv(BOA)["members"][:2]
    assert client.post("/api/squads/build", json=corpo_projeto(dois)).status_code == 422
