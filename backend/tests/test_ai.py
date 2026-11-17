"""Testes da parte de IA: sempre sem internet e sem chave (o modo simulado deve bastar)."""
import pytest
from fastapi.testclient import TestClient

from app.ai import briefing, llm, profile_chat
from app.api import app

client = TestClient(app)

BRIEFING = (
    "App web para clínica: agendamento online com login, API de integração, telas "
    "responsivas com protótipo no Figma, banco de dados de pacientes e testes de "
    "qualidade. Prazo de 2 meses, reunião semanal com o cliente."
)


@pytest.fixture(autouse=True)
def sem_chave(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)


def test_briefing_simulado_propoe_papeis_validos():
    """Sem chave de IA, o briefing gera de 3 a 6 papéis válidos e avisa 'simulado'."""
    r = briefing.parse_briefing(BRIEFING)
    assert r["mode"] == "simulado"
    assert 3 <= len(r["roles"]) <= 6
    assert r["duration_weeks"] == 8
    assert sum(x["critical"] for x in r["roles"]) <= 1
    assert {x["skill"] for x in r["roles"]} >= {"frontend", "backend", "banco_dados"}


def test_briefing_curto_ainda_gera_o_minimo_de_papeis():
    """Um briefing vago não quebra: o sistema completa com papéis básicos."""
    r = briefing.parse_briefing("Precisamos de algo simples para a loja.")
    assert len(r["roles"]) >= 3


def test_resposta_da_ia_real_e_validada(monkeypatch):
    """Se a IA responde no formato certo, o modo vira 'ia_real'."""
    boa = {"duration_weeks": 5, "roles": [
        {"skill": "backend", "min_level": 3, "hours_per_week": 8, "critical": True, "reason": "API"},
        {"skill": "frontend", "min_level": 2, "hours_per_week": 6, "critical": False, "reason": "Telas"},
        {"skill": "qa", "min_level": 2, "hours_per_week": 4, "critical": False, "reason": "Testes"},
    ]}
    monkeypatch.setattr(llm, "ask_json", lambda system, user: boa)
    r = briefing.parse_briefing(BRIEFING)
    assert r["mode"] == "ia_real" and r["duration_weeks"] == 5


def test_resposta_ruim_da_ia_cai_no_simulado(monkeypatch):
    """Se a IA inventa habilidade ou manda formato errado, usamos o simulado."""
    monkeypatch.setattr(llm, "ask_json", lambda s, u: {"roles": [{"skill": "magia"}]})
    assert briefing.parse_briefing(BRIEFING)["mode"] == "simulado"
    monkeypatch.setattr(llm, "ask_json", lambda s, u: None)  # falha de rede/limite
    assert briefing.parse_briefing(BRIEFING)["mode"] == "simulado"


def test_json_embrulhado_em_texto_e_lido():
    """O leitor aceita JSON mesmo com texto antes e depois."""
    assert llm._extract_json('claro! {"a": 1} pronto') == {"a": 1}
    assert llm._extract_json("sem json") is None


RESPOSTAS = {
    "areas": ["backend", "qa"],
    "levels": {"backend": 3, "qa": 1},
    "months": 9,
    "goals": ["devops"],
    "open": "Fiz o deploy de uma API com Docker e escrevi os testes.",
}


def test_nivel_vem_das_ancoras_e_nao_da_ia():
    """O nível de cada área é exatamente o da frase escolhida."""
    p = profile_chat.build_profile("Ana", RESPOSTAS)
    assert p["skills"] == {"backend": 3, "qa": 1}
    assert p["months_in_citi"] == 9 and p["learning_goals"] == ["devops"]


@pytest.mark.parametrize("mudanca", [
    {"goals": ["devops", "qa", "backend"]},
    {"months": 5},
    {"areas": ["magia"]},
    {"levels": {"backend": 7, "qa": 1}},
    {"levels": {"backend": 3}},
])
def test_perfil_invalido_e_rejeitado(mudanca):
    """Respostas fora do combinado viram erro claro, não perfil quebrado."""
    with pytest.raises(profile_chat.ProfileError):
        profile_chat.build_profile("Ana", {**RESPOSTAS, **mudanca})


def test_pergunta_aberta_sugere_mas_nao_define_nivel():
    """O texto livre só sugere habilidades que a pessoa não marcou."""
    r = client.post("/api/profile/interpret", json={"name": "Ana", "answers": RESPOSTAS}).json()
    assert r["mode"] == "simulado"
    assert [s["skill"] for s in r["suggested_skills"]] == ["devops"]
    assert "devops" not in r["profile"]["skills"]


def test_endpoint_de_briefing_e_status():
    """A API expõe o modo atual da IA e a leitura do briefing."""
    assert client.get("/api/ai/status").json() == {"mode": "simulado"}
    assert client.post("/api/briefing/parse", json={"text": BRIEFING}).json()["roles"]
    assert client.post("/api/briefing/parse", json={"text": "curto"}).status_code == 422


def test_projeto_novo_monta_tres_squads_com_membro_novo():
    """Do briefing às 3 squads, incluindo alguém que acabou de responder o chat."""
    papeis = briefing.parse_briefing(BRIEFING)["roles"]
    corpo = {
        "name": "App da Clínica", "duration_weeks": 8, "roles": papeis,
        "extra_members": [{"name": "Ana", "months_in_citi": 2,
                           "skills": {"backend": 1}, "learning_goals": ["backend"]}],
    }
    r = client.post("/api/squads/build", json=corpo)
    assert r.status_code == 200
    squads = r.json()["squads"]
    assert set(squads) == {"segura", "evolutiva", "balanceada"}
    assert all(0 <= s["metrics"]["risco"] <= 100 for s in squads.values())
    # projeto inválido
    assert client.post("/api/squads/build", json={**corpo, "roles": papeis[:2]}).status_code == 422


def test_troca_de_pessoa_tambem_funciona_em_projeto_novo():
    """Projeto vindo de briefing também aceita simular e aplicar trocas."""
    papeis = briefing.parse_briefing(BRIEFING)["roles"]
    custom = {"name": "App da Clínica", "duration_weeks": 8, "roles": papeis, "extra_members": []}
    squad = client.post("/api/squads/build", json=custom).json()["squads"]["segura"]
    corpo = {"profile": "segura", "assignments": squad["assignments"], "role_index": 0, "custom": custom}
    lista = client.post("/api/projects/custom/whatif", json=corpo).json()["substitutes"]
    assert lista and {"skill_level", "is_novato", "delta_risco"} <= set(lista[0])
    novo = client.post(
        "/api/projects/custom/apply", json={**corpo, "member_id": lista[0]["member_id"]}
    ).json()["squad"]
    assert novo["slots"][0]["member_id"] == lista[0]["member_id"]
