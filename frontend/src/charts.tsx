import type { Slot, Squad } from "./types";

const SHORT: Record<string, string> = {
  frontend: "Front-end", backend: "Back-end", banco_dados: "Banco de dados", ux_ui: "UX/UI",
  gestao: "Gestão", qa: "QA", dados_ia: "Dados/IA", devops: "DevOps",
};

const anchor = (c: number) => (c > 0.3 ? "start" : c < -0.3 ? "end" : "middle");

/** Radar de níveis: cada ponta é um papel (escala de 0 a 4).
 *  A linha tracejada é o nível mínimo que o projeto exige; a área verde é o nível de quem ocupa o papel. */
export function Radar({ levels, slots }: { levels: number[]; slots: Slot[] }) {
  const n = slots.length;
  const cx = 220, cy = 168, R = 100, MAX = 4;
  const at = (i: number, level: number): [number, number] => {
    const a = -Math.PI / 2 + (2 * Math.PI * i) / n;
    const f = Math.max(0, Math.min(MAX, level)) / MAX;
    return [cx + R * f * Math.cos(a), cy + R * f * Math.sin(a)];
  };
  const ring = (level: number) => Array.from({ length: n }, (_, i) => at(i, level).join(",")).join(" ");
  const squadShape = levels.map((v, i) => at(i, Math.max(0.08, v)).join(",")).join(" ");
  const needShape = slots.map((s, i) => at(i, s.min_level).join(",")).join(" ");
  return (
    <div>
      <svg viewBox="0 0 440 330" className="chart" role="img"
        aria-label={`Radar de níveis: ${slots.map((s, i) => `${SHORT[s.skill]} nível ${Math.round(levels[i] * 10) / 10} de 4, o projeto pede ${s.min_level}`).join("; ")}`}>
        {[1, 2, 3, 4].map((l) => <polygon key={l} points={ring(l)} className="grid" />)}
        {slots.map((_, i) => { const [x, y] = at(i, MAX); return <line key={i} x1={cx} y1={cy} x2={x} y2={y} className="grid" />; })}
        {[1, 2, 3, 4].map((l) => <text key={l} x={cx + 4} y={cy - (R * l) / MAX + 3} className="ring-label">{l}</text>)}
        <polygon points={needShape} className="need" />
        <polygon points={squadShape} className="cover" />
        {slots.map((s, i) => {
          const [vx, vy] = at(i, Math.max(0.08, levels[i]));
          const [lx, ly] = at(i, MAX * 1.3);
          const ang = -Math.PI / 2 + (2 * Math.PI * i) / n;
          const c = Math.cos(ang);
          const dy = Math.abs(c) <= 0.3 ? (Math.sin(ang) < 0 ? -2 : 12) : 4;
          return (
            <g key={i}>
              <circle cx={vx} cy={vy} r={4} className="dot">
                <title>{`${s.skill_label}: ${s.member_name ? `${s.member_name}, nível ${Math.round(levels[i])}` : "sem ninguém"}. O projeto pede nível ${s.min_level}.`}</title>
              </circle>
              <text x={lx} y={ly + dy} textAnchor={anchor(c)} className="axis">{SHORT[s.skill]}</text>
            </g>
          );
        })}
      </svg>
      <p className="legend">
        <span><i className="sw cover" /> Nível de quem ocupa o papel</span>
        <span><i className="sw need" /> Nível que o projeto exige</span>
      </p>
    </div>
  );
}

const initials = (name: string) => name.split(" ").filter(Boolean).slice(0, 2).map((p) => p[0]).join("").toUpperCase();

/** Quem ensina quem: setas do mentor para o mentorado. */
export function MentorGraph({ squad }: { squad: Squad }) {
  const people = squad.slots.filter((s) => s.member_id);
  const links = squad.metrics.mentorships;
  if (links.length === 0) {
    return <p className="empty">Esta squad não precisa de mentoria: ninguém está abaixo do nível exigido.</p>;
  }
  // Mentores na coluna da esquerda, mentorados na da direita: as setas ficam longas e legíveis.
  const mentorIds = [...new Set(links.map((l) => l.mentor_id))];
  const menteeIds = [...new Set(links.map((l) => l.mentee_id))];
  const rows = Math.max(mentorIds.length, menteeIds.length);
  const H = 70 + rows * 64;
  const r = 19;
  const pos: Record<string, { x: number; y: number; name: string; novato: boolean; left: boolean }> = {};
  const place = (ids: string[], x: number, left: boolean) =>
    ids.forEach((id, i) => {
      const p = people.find((q) => q.member_id === id)!;
      pos[id] = { x, y: 45 + ((i + 0.5) * (H - 70)) / ids.length, name: p.member_name!, novato: p.is_novato, left };
    });
  place(mentorIds, 130, true);
  place(menteeIds, 310, false);
  const mentors = new Set(mentorIds);
  return (
    <div>
      <svg viewBox={`0 0 440 ${H}`} className="chart" role="img"
        aria-label={links.map((l) => `${pos[l.mentor_id]?.name} ensina ${pos[l.mentee_id]?.name}`).join(". ")}>
        <defs>
          <marker id="seta" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M0,0 L10,5 L0,10 z" className="arrow-head" />
          </marker>
        </defs>
        <text x={130} y={18} textAnchor="middle" className="edge">Ensina</text>
        <text x={310} y={18} textAnchor="middle" className="edge">Aprende</text>
        {links.map((l, i) => {
          const a = pos[l.mentor_id], b = pos[l.mentee_id];
          if (!a || !b) return null;
          const dx = b.x - a.x, dy = b.y - a.y, d = Math.hypot(dx, dy) || 1;
          const x1 = a.x + (dx / d) * (r + 3), y1 = a.y + (dy / d) * (r + 3);
          const x2 = b.x - (dx / d) * (r + 5), y2 = b.y - (dy / d) * (r + 5);
          return (
            <g key={i}>
              <line x1={x1} y1={y1} x2={x2} y2={y2} className="arrow" markerEnd="url(#seta)" />
              <text x={(x1 + x2) / 2} y={(y1 + y2) / 2 - 7} textAnchor="middle" className="edge">{SHORT[l.skill] ?? l.skill}</text>
            </g>
          );
        })}
        {Object.entries(pos).map(([id, p]) => (
          <g key={id}>
            <circle cx={p.x} cy={p.y} r={r} className={`node ${mentors.has(id) ? "mentor" : ""} ${p.novato ? "novato" : ""}`}>
              <title>{p.name}{p.novato ? " (novato)" : ""}{mentors.has(id) ? " (mentor)" : ""}</title>
            </circle>
            <text x={p.x} y={p.y + 4} textAnchor="middle" className="ini">{initials(p.name)}</text>
            <text x={p.x + (p.left ? -(r + 8) : r + 8)} y={p.y + 4} textAnchor={p.left ? "end" : "start"} className="axis">{p.name.split(" ")[0]}</text>
          </g>
        ))}
      </svg>
      <p className="legend">
        <span><i className="sw mentor" /> Mentor</span>
        <span><i className="sw novato" /> Novato</span>
        <span>A seta vai de quem ensina para quem aprende.</span>
      </p>
    </div>
  );
}
