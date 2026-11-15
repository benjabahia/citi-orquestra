"""Dados SINTÉTICOS do CITi Orquestra.

Todos os nomes e perfis abaixo são inventados para o protótipo (decisão Q7).
Nenhuma pessoa real do CITi aparece aqui. O cenário é determinístico: rodar
duas vezes gera exatamente os mesmos dados.

Composição: 24 membros (8 novatos, 10 intermediários, 6 veteranos) e 6 projetos.
O projeto "pagamentos" é o "projeto armadilha" do demo: só UMA pessoa com
nível de referência em back-end está disponível. Remover essa pessoa faz o
risco disparar.
"""
import random

from .models import Availability, Member, Project, Role, Scenario

TRAP_PROJECT_ID = "pagamentos"

# (id, nome, meses no CITi, habilidades, metas de aprendizado, horas/semana típicas)
_MEMBER_ROWS = [
    # --- Veteranos (6) ---
    ("m01", "Marina Alves", 34, {"gestao": 4, "ux_ui": 2, "qa": 2}, ("dados_ia",), 10),
    ("m02", "Rafael Teixeira", 28, {"backend": 4, "banco_dados": 3, "devops": 3, "frontend": 2}, ("dados_ia",), 12),
    ("m03", "Camila Duarte", 26, {"frontend": 4, "ux_ui": 3, "backend": 2}, ("ux_ui",), 10),
    ("m04", "Lucas Barros", 22, {"dados_ia": 4, "backend": 3, "banco_dados": 3}, ("devops",), 8),
    ("m05", "Beatriz Nogueira", 30, {"ux_ui": 4, "frontend": 3, "gestao": 2}, ("gestao",), 9),
    ("m06", "Eduardo Lima", 20, {"devops": 4, "backend": 3, "qa": 3, "banco_dados": 2}, ("gestao",), 8),
    # --- Intermediários (10) ---
    ("m07", "Júlia Monteiro", 14, {"frontend": 3, "ux_ui": 2}, ("backend",), 10),
    ("m08", "Pedro Henrique", 12, {"backend": 3, "banco_dados": 2}, ("devops",), 10),
    ("m09", "Ana Clara Pires", 10, {"qa": 3, "frontend": 2}, ("backend",), 8),
    ("m10", "Gabriel Souza", 16, {"backend": 2, "dados_ia": 3}, ("banco_dados",), 9),
    ("m11", "Larissa Campos", 9, {"ux_ui": 3, "frontend": 2}, ("gestao",), 8),
    ("m12", "Thiago Ramos", 18, {"gestao": 3, "backend": 2}, ("dados_ia",), 7),
    ("m13", "Isabela Freitas", 7, {"frontend": 2, "ux_ui": 2, "qa": 2}, ("backend",), 10),
    ("m14", "Felipe Araújo", 11, {"devops": 2, "backend": 2, "banco_dados": 3}, ("devops",), 6),
    ("m15", "Mariana Costa", 13, {"dados_ia": 2, "banco_dados": 2, "backend": 2}, ("dados_ia",), 9),
    ("m16", "Vinícius Prado", 8, {"frontend": 3, "backend": 1}, ("backend",), 8),
    # --- Novatos (8) ---
    ("m17", "Davi Oliveira", 2, {"frontend": 1, "ux_ui": 1}, ("frontend",), 8),
    ("m18", "Sofia Carvalho", 3, {"ux_ui": 2, "frontend": 1}, ("ux_ui",), 6),
    ("m19", "Henrique Melo", 1, {"backend": 1}, ("backend",), 10),
    ("m20", "Laura Pinheiro", 4, {"qa": 1, "frontend": 1}, ("qa",), 8),
    ("m21", "Gustavo Rocha", 5, {"backend": 1, "banco_dados": 1}, ("banco_dados",), 7),
    ("m22", "Alice Ferraz", 2, {"dados_ia": 1, "backend": 1}, ("dados_ia",), 8),
    ("m23", "Matheus Cunha", 3, {"gestao": 1, "qa": 1}, ("gestao",), 6),
    ("m24", "Bruna Lopes", 1, {"frontend": 1, "ux_ui": 1}, ("ux_ui",), 10),
]

_TYPICAL_HOURS = {row[0]: row[5] for row in _MEMBER_ROWS}

# Papel(skill, nível mínimo, horas/semana, peso, crítico)
_PROJECT_ROWS = [
    (
        "agenda-clinica",
        "Sistema de Agendamento para Clínica",
        "Agenda online com lembretes automáticos para pacientes e painel da recepção.",
        6,
        [
            Role("frontend", 3, 8),
            Role("backend", 3, 8, weight=1.5, critical=True),
            Role("ux_ui", 2, 5),
            Role("gestao", 2, 5),
        ],
    ),
    (
        "loja-cosmeticos",
        "Loja Virtual para Marca de Cosméticos",
        "E-commerce com catálogo, carrinho, pagamento e painel de pedidos.",
        8,
        [
            Role("frontend", 3, 8),
            Role("backend", 3, 8, weight=1.5, critical=True),
            Role("banco_dados", 2, 5),
            Role("ux_ui", 3, 6),
            Role("qa", 2, 5),
        ],
    ),
    (
        "painel-industria",
        "Painel de Indicadores para Indústria",
        "Dashboards com dados de produção em tempo quase real.",
        4,
        [
            Role("dados_ia", 3, 8, weight=1.5, critical=True),
            Role("frontend", 2, 6),
            Role("banco_dados", 3, 6),
            Role("gestao", 2, 5),
        ],
    ),
    (
        "app-logistica",
        "Aplicativo de Logística com Rastreio",
        "App para motoristas e central, com rastreio de entregas e rotas.",
        10,
        [
            Role("backend", 4, 10, weight=1.5, critical=True),
            Role("devops", 3, 6),
            Role("frontend", 3, 8),
            Role("qa", 2, 5),
            Role("ux_ui", 2, 5),
            Role("gestao", 3, 6),
        ],
    ),
    (
        "site-institucional",
        "Site Institucional com Blog",
        "Site simples de apresentação, com blog e formulário de contato.",
        2,
        [
            Role("frontend", 2, 8),
            Role("ux_ui", 2, 6),
            Role("gestao", 1, 4),
        ],
    ),
    (
        TRAP_PROJECT_ID,
        "Plataforma de Pagamentos para Fintech",
        "API de pagamentos com alta exigência de segurança e disponibilidade.",
        6,
        [
            Role("backend", 4, 10, weight=1.5, critical=True),
            Role("frontend", 3, 8),
            Role("qa", 3, 6),
            Role("gestao", 2, 5),
        ],
    ),
]

# No projeto armadilha, quem tem back-end sólido (ou serve de reserva dele)
# está ocupado em outros projetos: só Rafael (m02) tem back-end de referência
# livre e ninguém cobre a falta dele.
_TRAP_BUSY = {"m03", "m04", "m06", "m08", "m12"}


def _build_availability(project: Project, rng: random.Random) -> dict:
    """Simula as respostas de disponibilidade dadas para este projeto."""
    result = {}
    for member_id, base in _TYPICAL_HOURS.items():
        r = rng.random()
        factor = 1.0 if r < 0.55 else 0.75 if r < 0.80 else 0.5 if r < 0.92 else 0.0
        unavailable = 1 if (rng.random() < 0.15 and project.duration_weeks >= 4) else 0
        result[member_id] = Availability(
            weekly_hours=round(base * factor, 1), unavailable_weeks=unavailable
        )
    if project.id == TRAP_PROJECT_ID:
        for member_id in _TRAP_BUSY:
            result[member_id] = Availability(weekly_hours=0.0)
        # Rafael está inteiramente disponível, mas é o único.
        result["m02"] = Availability(weekly_hours=12.0)
    return result


def load_scenario() -> Scenario:
    members = tuple(
        Member(
            id=row[0],
            name=row[1],
            months_in_citi=row[2],
            skills=dict(row[3]),
            learning_goals=tuple(row[4]),
        )
        for row in _MEMBER_ROWS
    )
    projects = tuple(
        Project(id=pid, name=name, description=desc, duration_weeks=weeks, roles=tuple(roles))
        for pid, name, desc, weeks, roles in _PROJECT_ROWS
    )
    availability = {
        p.id: _build_availability(p, random.Random(f"disponibilidade-{p.id}"))
        for p in projects
    }
    return Scenario(members=members, projects=projects, availability=availability)
