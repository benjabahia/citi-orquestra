"""Configurações do CITi Orquestra.

Tudo que é "regra do negócio" e pode ser ajustado fica aqui, num lugar só.
Assim o gerente (ou você, na revisão) enxerga os números sem caçar no código.
"""
from dataclasses import dataclass

# As 8 habilidades do perfil (decisão Q20).
SKILLS = (
    "frontend",
    "backend",
    "banco_dados",
    "ux_ui",
    "gestao",
    "qa",
    "dados_ia",
    "devops",
)

SKILL_LABELS = {
    "frontend": "Front-end",
    "backend": "Back-end",
    "banco_dados": "Banco de dados",
    "ux_ui": "UX/UI Design",
    "gestao": "Gestão de projeto",
    "qa": "QA/Testes",
    "dados_ia": "Dados/IA",
    "devops": "DevOps/Infra",
}

# Os 5 níveis (decisão Q20). 3 ou mais = pode ser mentor.
LEVEL_LABELS = {
    0: "nenhum",
    1: "iniciante",
    2: "intermediário",
    3: "avançado",
    4: "referência",
}

# Os 3 tipos de squad (decisão Q2).
PROFILES = ("segura", "evolutiva", "balanceada")


@dataclass(frozen=True)
class Config:
    """Valores padrão configuráveis (decisões Q9 e Q17)."""

    # --- Mentoria (Q9) ---
    novato_months: int = 6              # menos que isso no CITi = novato
    mentor_min_level: int = 3           # nível mínimo na habilidade para ser mentor
    max_mentees_per_mentor: int = 2     # cada mentor atende no máximo 2 pessoas
    mentoring_hours_per_mentee: float = 2.0  # horas/semana que a mentoria consome
    mentor_level_boost: int = 1         # com mentor, o nível efetivo sobe 1 (ao medir o RISCO)
    mentor_delivery_boost: float = 0.5  # ...mas na ENTREGA a ajuda do mentor vale só meio nível
    mentoring_delivery_cost: float = 2.0  # pontos de entrega perdidos por pessoa mentorada (tempo do mentor)
    evolutiva_min_novatos: int = 2      # a Evolutiva leva pelo menos 2 novatos (ou metade dos papéis, se for maior)

    # --- Cobertura ---
    backup_min_level: int = 2           # nível mínimo para "cobrir" uma habilidade

    # --- Medidor de risco: pontos de penalidade (Q17) ---
    risk_spof: float = 12.0             # ponto único de falha em papel crítico
    risk_overload: float = 10.0         # por pessoa sobrecarregada
    risk_novato_sem_mentor: float = 15.0
    risk_lacuna: float = 25.0           # papel sem ninguém (x peso do papel; crítico = 1,5x)
    risk_per_level_gap: float = 5.0     # por nível abaixo do exigido (x peso do papel)

    # --- Medidor de crescimento (Q17) ---
    growth_goal_weight: float = 0.6     # papel bate com a meta de aprendizado
    growth_mentor_weight: float = 0.4   # aprende com apoio de um mentor

    # --- Busca das squads ---
    unmentored_penalty: float = 30.0    # na busca, novato sem mentor é muito ruim
    overload_search_penalty: float = 8.0  # na busca, evita pôr gente sem horas suficientes


DEFAULT_CONFIG = Config()


@dataclass(frozen=True)
class ProfileWeights:
    """Quanto cada tipo de squad valoriza cada medidor."""

    entrega: float
    crescimento: float
    risco: float


PROFILE_WEIGHTS = {
    "segura": ProfileWeights(entrega=0.60, crescimento=0.0, risco=0.40),
    "evolutiva": ProfileWeights(entrega=0.30, crescimento=0.45, risco=0.25),
    "balanceada": ProfileWeights(entrega=0.40, crescimento=0.35, risco=0.25),
}

PROFILE_TITLES = {"segura": "Segura", "evolutiva": "Evolutiva", "balanceada": "Balanceada"}


# --- Recomendação por prioridade (recommend.py) ---
# Aqui o peso do risco vale para "100 - risco" (risco baixo soma pontos).
PRIORITY_WEIGHTS = {
    "prazo": ProfileWeights(entrega=0.50, crescimento=0.0, risco=0.50),
    "formar": ProfileWeights(entrega=0.15, crescimento=0.70, risco=0.15),
    "equilibrio": ProfileWeights(entrega=1 / 3, crescimento=1 / 3, risco=1 / 3),
}


@dataclass(frozen=True)
class RecommendConfig:
    # Em "prazo apertado", squad com risco mais de 15 pontos acima do menor risco não é recomendada.
    prazo_max_risk_gap: float = 15.0


RECOMMEND_CONFIG = RecommendConfig()
