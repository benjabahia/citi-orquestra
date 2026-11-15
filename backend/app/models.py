"""Modelos de dados do CITi Orquestra.

São só "caixinhas" de dados (dataclasses). A lógica fica em scoring.py,
allocator.py e whatif.py.
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Member:
    """Um membro do CITi e o perfil que ele preencheu no chat."""

    id: str
    name: str
    months_in_citi: int
    skills: dict                       # habilidade -> nível (0 a 4)
    learning_goals: tuple = ()         # o que a pessoa quer aprender neste ciclo

    def level(self, skill: str) -> int:
        return self.skills.get(skill, 0)

    def is_novato(self, novato_months: int) -> bool:
        return self.months_in_citi < novato_months


@dataclass(frozen=True)
class Availability:
    """Disponibilidade de UMA pessoa para UM projeto (decisão Q5)."""

    weekly_hours: float
    unavailable_weeks: int = 0

    def effective_hours(self, duration_weeks: int) -> float:
        """Horas por semana "médias" ao longo do projeto.

        Se a pessoa está fora 1 de 4 semanas, a média cai para 75% das horas.
        """
        if duration_weeks <= 0:
            return 0.0
        free_weeks = max(0, duration_weeks - self.unavailable_weeks)
        return self.weekly_hours * free_weeks / duration_weeks


@dataclass(frozen=True)
class Role:
    """Um papel que o projeto precisa (ex.: 'back-end nível 3, 8 h/semana')."""

    skill: str
    min_level: int
    hours_per_week: float
    weight: float = 1.0
    critical: bool = False             # papel crítico: precisa de redundância


@dataclass(frozen=True)
class Project:
    id: str
    name: str
    description: str
    duration_weeks: int
    roles: tuple                       # tuple[Role, ...]

    @property
    def team_size(self) -> int:
        return len(self.roles)


@dataclass(frozen=True)
class Scenario:
    """Tudo que o sistema precisa: pessoas, projetos e disponibilidades."""

    members: tuple
    projects: tuple
    # availability[project_id][member_id] -> Availability
    availability: dict = field(default_factory=dict)

    def members_by_id(self) -> dict:
        return {m.id: m for m in self.members}

    def project(self, project_id: str) -> Project:
        for p in self.projects:
            if p.id == project_id:
                return p
        raise KeyError(project_id)


# ---------------------------------------------------------------------------
# Resultados
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Factor:
    """Um motivo de risco, já em português (serve de explicação no app)."""

    kind: str                          # lacuna, spof, sobrecarga, sem_mentor, nivel_abaixo
    points: float
    message: str
    member_id: Optional[str] = None
    skill: Optional[str] = None

    def key(self) -> tuple:
        """Identidade do fator, para comparar antes e depois de uma troca."""
        return (self.kind, self.member_id, self.skill)


@dataclass(frozen=True)
class Mentorship:
    mentor_id: str
    mentee_id: str
    skill: str


@dataclass(frozen=True)
class MemberLoad:
    """Dados para o gráfico de barras de carga."""

    member_id: str
    role_index: int
    capacity: float                    # horas/semana que a pessoa tem
    demand: float                      # horas/semana que o papel + mentoria pedem
    mentoring_hours: float


@dataclass(frozen=True)
class Metrics:
    entrega: float                     # 0 a 100 (quanto maior, melhor)
    crescimento: float                 # 0 a 100 (quanto maior, melhor)
    risco: float                       # 0 a 100 (quanto MENOR, melhor)
    factors: tuple = ()                # tuple[Factor, ...]
    loads: tuple = ()                  # tuple[MemberLoad, ...]
    mentorships: tuple = ()            # tuple[Mentorship, ...]
    role_coverage: tuple = ()          # cobertura (0 a 1) de cada papel, para o radar


@dataclass(frozen=True)
class Squad:
    profile: str
    # assignments[i] = id do membro no papel i (ou None se ficou vago)
    assignments: tuple
    metrics: Metrics
    objective: float
    notes: tuple = ()                  # avisos (ex.: restrição relaxada)
