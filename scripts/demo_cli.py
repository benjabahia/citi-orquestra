"""Mostra no terminal os 3 squads de um projeto (para você ver o motor funcionando).

Uso (a partir da pasta citi-orquestra):
    python scripts/demo_cli.py                 # projeto padrão
    python scripts/demo_cli.py pagamentos      # outro projeto (id)
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.config import SKILL_LABELS  # noqa: E402
from app.data import load_scenario  # noqa: E402
from app.allocator import build_squads  # noqa: E402


def main(project_id: str) -> None:
    sc = load_scenario()
    members = sc.members_by_id()
    project = sc.project(project_id)
    availability = sc.availability[project.id]

    t0 = time.perf_counter()
    squads = build_squads(project, members, availability)
    elapsed = time.perf_counter() - t0

    print(f"\n=== {project.name} ({project.duration_weeks} semanas) ===")
    for profile, squad in squads.items():
        m = squad.metrics
        print(f"\n--- Squad {profile.upper()} | entrega {m.entrega} | crescimento {m.crescimento} | risco {m.risco}")
        for role, mid in zip(project.roles, squad.assignments):
            who = members[mid].name if mid else "(vago)"
            print(f"   {SKILL_LABELS[role.skill]:<18} nível {role.min_level}  ->  {who}")
        for ms in m.mentorships:
            print(f"   mentoria: {members[ms.mentor_id].name} -> {members[ms.mentee_id].name} ({SKILL_LABELS[ms.skill]})")
        for f in m.factors:
            print(f"   ! {f.message}")
        for note in squad.notes:
            print(f"   * {note}")
    print(f"\n(tempo de cálculo: {elapsed:.2f}s)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "agenda-clinica")
