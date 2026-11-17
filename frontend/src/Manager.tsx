import { useEffect, useRef, useState } from "react";
import { api } from "./api";
import SquadBoard from "./SquadBoard";
import SquadDetail from "./SquadDetail";
import type { CustomBody, Meta, Mode, Profile, Project, Role, Squad, SquadsResponse } from "./types";

export const STORAGE_KEY = "citi-orquestra-membros";

export function loadSavedMembers(): Profile[] {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
  } catch {
    return [];
  }
}

const EXAMPLE_BRIEFING =
  "App web para uma clínica de fisioterapia: agendamento online com login, API de integração " +
  "com o sistema atual, telas responsivas com protótipo no Figma, banco de dados de pacientes e " +
  "testes de qualidade. Prazo de 2 meses, reunião semanal com o cliente.";

export default function Manager({ meta }: { meta: Meta }) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [briefing, setBriefing] = useState("");
  const [name, setName] = useState("");
  const [weeks, setWeeks] = useState(6);
  const [roles, setRoles] = useState<Role[] | null>(null);
  const [parseMode, setParseMode] = useState<Mode | null>(null);
  const [result, setResult] = useState<SquadsResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [openId, setOpenId] = useState<string | null>(null);
  const [custom, setCustom] = useState<CustomBody | null>(null);
  const [detail, setDetail] = useState<Squad["profile"] | null>(null);
  const rolesRef = useRef<HTMLElement>(null);
  const resultRef = useRef<HTMLElement>(null);
  const saved = loadSavedMembers();

  // Leva a tela até o que acabou de aparecer (antes o resultado ficava fora da vista).
  const reduceMotion =
    typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const goTo = (el: HTMLElement | null) =>
    el?.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "start" });
  useEffect(() => { if (result) goTo(resultRef.current); }, [result]);
  useEffect(() => { if (roles && !result) goTo(rolesRef.current); }, [roles]);

  useEffect(() => {
    api.projects().then(setProjects).catch((e) => setError(e.message));
  }, []);

  async function run<T>(job: () => Promise<T>): Promise<T | undefined> {
    setBusy(true);
    setError("");
    try {
      return await job();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const openExample = (id: string) =>
    run(async () => {
      setRoles(null);
      setOpenId(id);
      setCustom(null);
      setDetail(null);
      setResult(await api.squads(id));
    });

  const proposeRoles = () =>
    run(async () => {
      const r = await api.parseBriefing(briefing);
      setRoles(r.roles);
      if (r.name && !name.trim()) setName(r.name);
      setWeeks(r.duration_weeks);
      setParseMode(r.mode);
      setOpenId(null);
      setResult(null);
    });

  const build = () =>
    run(async () => {
      if (!roles) return;
      const body: CustomBody = {
        name: name.trim() || "Projeto novo",
        description: briefing.slice(0, 300),
        duration_weeks: weeks,
        roles: roles.map(({ skill, min_level, hours_per_week, critical }) => ({
          skill, min_level, hours_per_week, critical,
        })),
        extra_members: saved,
      };
      setCustom(body);
      setDetail(null);
      setResult(await api.buildCustom(body));
    });

  const updateRole = (i: number, patch: Partial<Role>) =>
    setRoles((rs) => rs && rs.map((r, k) => (k === i ? { ...r, ...patch } : r)));

  const setCritical = (i: number) =>
    setRoles((rs) => rs && rs.map((r, k) => ({ ...r, critical: k === i ? !r.critical : false })));

  const addRole = () =>
    setRoles((rs) => {
      if (!rs || rs.length >= 6) return rs;
      const free = Object.keys(meta.skills).find((s) => !rs.some((r) => r.skill === s));
      return free
        ? [...rs, { skill: free, skill_label: meta.skills[free], min_level: 2, hours_per_week: 6, critical: false }]
        : rs;
    });

  if (result && detail) {
    return (
      <SquadDetail
        key={`${result.project.id}-${detail}`}
        data={result}
        profile={detail}
        custom={custom}
        onBack={() => { setDetail(null); setTimeout(() => window.scrollTo({ top: 0 }), 0); }}
      />
    );
  }

  return (
    <div className="stack">
      <section className="panel">
        <h2>1. Descreva o projeto</h2>
        <p className="muted">
          Cole o briefing e o sistema propõe os papéis. Você revisa antes de montar as squads.
        </p>
        <label htmlFor="briefing">Briefing do projeto</label>
        <textarea
          id="briefing"
          rows={5}
          value={briefing}
          onChange={(e) => setBriefing(e.target.value)}
          placeholder="Cole aqui o texto do cliente ou o escopo do projeto"
        />
        <div className="row">
          <button className="primary" disabled={busy || briefing.trim().length < 10} onClick={proposeRoles}>
            {busy ? "Propondo papéis..." : "Propor papéis"}
          </button>
          <button className="ghost" onClick={() => setBriefing(EXAMPLE_BRIEFING)}>
            Usar briefing de exemplo
          </button>
        </div>
        <div className="examples">
          <span className="muted small">Ou abra um projeto pronto:</span>
          {projects.map((p) => (
            <button key={p.id} className={`chip ${openId === p.id ? "on" : ""}`} aria-pressed={openId === p.id} disabled={busy} onClick={() => openExample(p.id)}>
              {p.name}
            </button>
          ))}
        </div>
        {error && <p className="error" role="alert">{error}</p>}
      </section>

      {roles && (
        <section className="panel" ref={rolesRef}>
          <h2>2. Confira os papéis</h2>
          <p className="muted">
            {parseMode === "ia_real"
              ? "Proposta feita por um modelo de linguagem."
              : "Proposta feita por regras simples (modo simulado)."}{" "}
            Ajuste o que quiser. Marque como crítico o papel sem o qual o projeto trava.
          </p>
          <div className="row fields">
            <div>
              <label htmlFor="pname">Nome do projeto</label>
              <input id="pname" value={name} onChange={(e) => setName(e.target.value)} placeholder="Ex.: App da clínica" />
            </div>
            <div>
              <label htmlFor="weeks">Duração (semanas)</label>
              <input id="weeks" type="number" min={1} max={26} value={weeks} onChange={(e) => setWeeks(Number(e.target.value))} />
            </div>
          </div>
          <table className="roles">
            <thead>
              <tr>
                <th>Habilidade</th>
                <th>Nível mínimo</th>
                <th>Horas por semana</th>
                <th>Crítico</th>
                <th><span className="sr">Remover</span></th>
              </tr>
            </thead>
            <tbody>
              {roles.map((r, i) => (
                <tr key={i}>
                  <td>
                    <select
                      value={r.skill}
                      onChange={(e) => updateRole(i, { skill: e.target.value, skill_label: meta.skills[e.target.value] })}
                      aria-label="Habilidade"
                    >
                      {Object.entries(meta.skills).map(([k, v]) => (
                        <option key={k} value={k} disabled={roles.some((o, j) => j !== i && o.skill === k)}>{v}</option>
                      ))}
                    </select>
                    {r.reason && <div className="muted small">{r.reason}</div>}
                  </td>
                  <td>
                    <select value={r.min_level} onChange={(e) => updateRole(i, { min_level: Number(e.target.value) })} aria-label="Nível mínimo">
                      {[1, 2, 3, 4].map((n) => (
                        <option key={n} value={n}>{n} · {meta.levels[String(n)]}</option>
                      ))}
                    </select>
                  </td>
                  <td>
                    <input type="number" min={1} max={20} value={r.hours_per_week} onChange={(e) => updateRole(i, { hours_per_week: Number(e.target.value) })} aria-label="Horas por semana" />
                  </td>
                  <td>
                    <input type="checkbox" checked={r.critical} onChange={() => setCritical(i)} aria-label="Papel crítico" />
                  </td>
                  <td>
                    <button className="ghost" disabled={roles.length <= 3} onClick={() => setRoles(roles.filter((_, k) => k !== i))}>
                      Remover
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="row">
            <button className="ghost" disabled={roles.length >= 6} onClick={addRole}>Adicionar papel</button>
            <button className="primary" disabled={busy} onClick={build}>{busy ? "Montando..." : "Montar squads"}</button>
          </div>
          {saved.length > 0 && (
            <p className="muted small">
              {saved.length} membro(s) que responderam o chat entram no sorteio: {saved.map((m) => m.name).join(", ")}.
            </p>
          )}
        </section>
      )}

      {result && (
        <section ref={resultRef} className="result">
          <div className="result-head">
            <h2>{result.project.name}</h2>
            <p className="muted">
              {result.project.duration_weeks} semanas · {result.project.roles.length} papéis. Compare as três
              opções e abra os detalhes da que preferir.
            </p>
          </div>
          <SquadBoard data={result} onDetail={(p) => { setDetail(p); window.scrollTo({ top: 0 }); }} />
        </section>
      )}
    </div>
  );
}
