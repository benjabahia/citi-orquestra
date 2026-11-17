"""Testes de cenário do CITi Orquestra (decisão Q28).

Cada teste prova uma promessa do produto. A docstring de cada um vira uma
linha da tabela "o que foi testado" na documentação.
"""
import pytest

from app.allocator import build_squads
from app.config import DEFAULT_CONFIG, PROFILES
from app.data import TRAP_PROJECT_ID, load_scenario
from app.models import Availability
from app.whatif import apply_substitution, rank_substitutes, remove_member

CFG = DEFAULT_CONFIG


@pytest.fixture(scope="module")
def scenario():
    return load_scenario()


@pytest.fixture(scope="module")
def members(scenario):
    return scenario.members_by_id()


@pytest.fixture(scope="module")
def all_squads(scenario, members):
    """As 3 squads de cada um dos 6 projetos (calculado uma vez só)."""
    return {
        p.id: build_squads(p, members, scenario.availability[p.id])
        for p in scenario.projects
    }


def _novatos(squad, members):
    return [
        a for a in squad.assignments
        if a is not None and members[a].is_novato(CFG.novato_months)
    ]


# 1 ---------------------------------------------------------------------------
def test_horas_efetivas_consideram_semanas_indisponiveis():
    """Quem fica 1 de 4 semanas fora tem 75% das horas semanais em média."""
    a = Availability(weekly_hours=8, unavailable_weeks=1)
    assert a.effective_hours(4) == pytest.approx(6.0)
    assert Availability(weekly_hours=8).effective_hours(4) == pytest.approx(8.0)
    assert Availability(weekly_hours=8, unavailable_weeks=9).effective_hours(4) == 0.0


# 2 ---------------------------------------------------------------------------
def test_medidores_ficam_entre_0_e_100(all_squads):
    """Entrega, crescimento e risco sempre ficam na faixa de 0 a 100."""
    for squads in all_squads.values():
        for squad in squads.values():
            m = squad.metrics
            assert 0 <= m.entrega <= 100
            assert 0 <= m.crescimento <= 100
            assert 0 <= m.risco <= 100


# 3 ---------------------------------------------------------------------------
def test_as_tres_squads_sao_diferentes(all_squads):
    """Em todo projeto, as 3 opções têm conjuntos de pessoas diferentes."""
    for project_id, squads in all_squads.items():
        conjuntos = {
            frozenset(a for a in s.assignments if a is not None) for s in squads.values()
        }
        assert len(conjuntos) == 3, project_id


# 4 ---------------------------------------------------------------------------
def test_squad_segura_nao_tem_novatos(all_squads, members):
    """A squad Segura nunca inclui novatos."""
    for squads in all_squads.values():
        assert _novatos(squads["segura"], members) == []


# 5 ---------------------------------------------------------------------------
def test_squad_balanceada_tem_exatamente_um_novato(all_squads, members):
    """A squad Balanceada tem exatamente 1 novato (há novatos disponíveis)."""
    for squads in all_squads.values():
        assert len(_novatos(squads["balanceada"], members)) == 1


# 6 ---------------------------------------------------------------------------
def test_squad_evolutiva_nunca_deixa_novato_sem_mentor(all_squads, members):
    """Na squad Evolutiva, todo novato tem mentor na própria squad."""
    for project_id, squads in all_squads.items():
        squad = squads["evolutiva"]
        assert len(_novatos(squad, members)) >= 1, project_id
        assert not [f for f in squad.metrics.factors if f.kind == "sem_mentor"], project_id


# 7 ---------------------------------------------------------------------------
def test_regras_de_mentoria(all_squads, members):
    """Mentor tem nível 3+ na habilidade, atende no máx. 2 e está na mesma squad."""
    for squads in all_squads.values():
        for squad in squads.values():
            ids = {a for a in squad.assignments if a is not None}
            atendidos = {}
            mentorandos = {ms.mentee_id for ms in squad.metrics.mentorships}
            for ms in squad.metrics.mentorships:
                assert ms.mentor_id in ids and ms.mentee_id in ids
                assert ms.mentor_id != ms.mentee_id
                assert ms.mentor_id not in mentorandos  # quem é mentorado não mentora
                assert members[ms.mentor_id].level(ms.skill) >= CFG.mentor_min_level
                atendidos[ms.mentor_id] = atendidos.get(ms.mentor_id, 0) + 1
            assert all(n <= CFG.max_mentees_per_mentor for n in atendidos.values())


# 8 ---------------------------------------------------------------------------
def test_cada_tipo_de_squad_faz_o_que_promete(all_squads):
    """Segura tem a melhor entrega e o menor risco; Evolutiva, o maior crescimento."""
    for project_id, squads in all_squads.items():
        seg, evo = squads["segura"].metrics, squads["evolutiva"].metrics
        assert seg.entrega >= evo.entrega, project_id
        assert seg.risco <= evo.risco, project_id
        assert evo.crescimento >= seg.crescimento, project_id


def test_as_tres_squads_formam_uma_escada_clara(all_squads):
    """Entrega cai de Segura a Evolutiva e crescimento sobe, sem empate entre os tipos."""
    for project_id, squads in all_squads.items():
        seg, bal, evo = (squads[k].metrics for k in ("segura", "balanceada", "evolutiva"))
        assert seg.entrega > bal.entrega > evo.entrega, project_id
        assert seg.crescimento < bal.crescimento < evo.crescimento, project_id
        assert seg.risco <= bal.risco <= evo.risco, project_id


def test_evolutiva_leva_mais_novatos_que_a_balanceada(all_squads, members):
    """Evolutiva: pelo menos 2 novatos; Balanceada: exatamente 1; Segura: nenhum."""
    for project_id, squads in all_squads.items():
        assert len(_novatos(squads["evolutiva"], members)) >= 2, project_id
        assert len(_novatos(squads["balanceada"], members)) == 1, project_id
        assert len(_novatos(squads["segura"], members)) == 0, project_id


def test_novato_com_mentor_nao_rende_como_veterano():
    """A entrega considera que quem aprende com mentor ainda rende menos."""
    from app.config import DEFAULT_CONFIG as C
    assert C.mentor_delivery_boost < C.mentor_level_boost


# 9 ---------------------------------------------------------------------------
def test_projeto_armadilha_tirar_a_unica_referencia_de_backend_dispara_o_risco(
    scenario, members, all_squads
):
    """No projeto armadilha, remover o único back-end nível 4 faz o risco disparar."""
    project = scenario.project(TRAP_PROJECT_ID)
    availability = scenario.availability[TRAP_PROJECT_ID]
    squad = all_squads[TRAP_PROJECT_ID]["segura"]
    backend_role = next(i for i, r in enumerate(project.roles) if r.skill == "backend")
    assert squad.assignments[backend_role] == "m02"  # Rafael, o único nível 4 livre

    # o sistema já alerta o ponto único de falha ANTES da remoção
    assert any(f.kind == "spof" for f in squad.metrics.factors)

    sem_rafael = remove_member(project, squad, backend_role, members, availability)
    assert sem_rafael.metrics.risco >= squad.metrics.risco * 2  # o risco pelo menos dobra
    assert any(f.kind == "lacuna" for f in sem_rafael.metrics.factors)

    # e nenhum substituto disponível alcança o nível 4 de back-end
    substitutos = rank_substitutes(project, squad, backend_role, members, availability)
    assert substitutos, "deve haver candidatos"
    assert all(members[s.member_id].level("backend") < 4 for s in substitutos)
    assert all(members[s.member_id].level("backend") >= 1 for s in substitutos)  # só quem conhece o assunto
    assert all(s.delta_entrega < 0 for s in substitutos)  # toda troca piora a entrega


# 10 --------------------------------------------------------------------------
def test_sem_gente_suficiente_gera_lacuna_e_nao_erro(scenario, members):
    """Se faltam pessoas, o sistema mostra a lacuna em vez de falhar."""
    project = scenario.project("app-logistica")  # pede 6 papéis
    pouca_gente = {
        mid: av
        for mid, av in scenario.availability[project.id].items()
        if mid in {"m02", "m03"}
    }
    squads = build_squads(project, members, pouca_gente)
    for squad in squads.values():
        assert sum(1 for a in squad.assignments if a is None) >= 4
        assert any(f.kind == "lacuna" for f in squad.metrics.factors)
        assert 0 <= squad.metrics.risco <= 100


# 11 --------------------------------------------------------------------------
def test_substitutos_vem_ordenados_pelo_impacto_e_deltas_batem(scenario, members, all_squads):
    """A lista de substitutos vem do melhor ao pior, com deltas coerentes."""
    project = scenario.project("agenda-clinica")
    availability = scenario.availability[project.id]
    squad = all_squads[project.id]["evolutiva"]
    lista = rank_substitutes(project, squad, 0, members, availability)
    assert len(lista) >= 3
    impactos = [s.objective_delta for s in lista]
    assert impactos == sorted(impactos, reverse=True)
    for s in lista:
        assert s.delta_risco == pytest.approx(s.metrics.risco - squad.metrics.risco, abs=0.11)
        assert s.member_id not in squad.assignments


# 12 --------------------------------------------------------------------------
def test_aplicar_troca_recalcula_os_medidores(scenario, members, all_squads):
    """Ao aplicar uma troca, os medidores refletem a nova squad."""
    project = scenario.project("agenda-clinica")
    availability = scenario.availability[project.id]
    squad = all_squads[project.id]["segura"]
    melhor = rank_substitutes(project, squad, 0, members, availability)[0]
    nova = apply_substitution(project, squad, 0, melhor.member_id, members, availability)
    assert nova.assignments[0] == melhor.member_id
    assert nova.metrics.entrega == pytest.approx(melhor.metrics.entrega)
    assert nova.metrics.risco == pytest.approx(melhor.metrics.risco)


# 13 --------------------------------------------------------------------------
def test_resultado_e_deterministico(scenario, members):
    """Mesma entrada e mesma seed geram exatamente as mesmas squads."""
    project = scenario.project("loja-cosmeticos")
    availability = scenario.availability[project.id]
    a = build_squads(project, members, availability, seed=3)
    b = build_squads(project, members, availability, seed=3)
    for profile in PROFILES:
        assert a[profile].assignments == b[profile].assignments
        assert a[profile].metrics == b[profile].metrics
