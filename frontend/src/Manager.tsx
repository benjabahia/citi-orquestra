import { useEffect, useRef, useState } from "react";
import { api } from "./api";
import ImportSheet, { loadSheet, saveSheet } from "./ImportSheet";
import SquadBoard from "./SquadBoard";
import SquadDetail from "./SquadDetail";
import type { CustomBody, Hours, Meta, Mode, Priority, Profile, Project, Role, Squad, SquadsResponse, TeamMember } from "./types";
import { num, validNumber } from "./ui";

export const STORAGE_KEY = "citi-orquestra-membros";

export function loadSavedMembers(): Profile[] {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
  } catch {
    return [];
  }
}

const WEEK_CHIPS = [2, 4, 6, 8, 12];
const SOURCE_LABEL: Record<TeamMember["source"], string> = {
  planilha: "planilha", perfil: "perfil do membro", exemplo: "exemplo (fictício)",
};
export const DECLARED_NOTE = "Disponibilidade declarada pelos membros; o sistema não verifica as horas.";

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
  const [priority, setPriority] = useState<Priority | null>(null);
  const rolesRef = useRef<HTMLElement>(null);
  const resultRef = useRef<HTMLElement>(null);
  const saved = loadSavedMembers();
  const [sheet, setSheet] = useState<Profile[] | null>(loadSheet);
  // Equipe em jogo (com as horas declaradas) e os ajustes que o gerente fez por cima.
  const [team, setTeam] = useState<TeamMember[] | null>(null);
  const [overrides, setOverrides] = useState<Record<string, Hours>>({});
  const savedKey = JSON.stringify(saved);

  // Trocar ou remover a planilha invalida o resultado que está na tela (ele usava a equipe antiga).
  const changeSheet = (members: Profile[] | null) => {
    saveSheet(members);
    setSheet(members);
    setOverrides({}); // os ajustes eram para a equipe antiga
    if (custom) { setResult(null); setDetail(null); setCustom(null); setPriority(null); }
  };

  /** O projeto por briefing como o servidor espera (sem os ajustes de horas). */
  const baseBody = (): CustomBody | null => {
    if (!roles) return null;
    return {
      name: name.trim().length >= 2 ? name.trim() : "Projeto novo",
      description: briefing.slice(0, 300),
      duration_weeks: weeks,
      roles: roles.map(({ skill, min_level, hours_per_week, critical }) => ({
        skill, min_level, hours_per_week, critical,
      })),
      extra_members: saved,
      replace_members: sheet,
    };
  };

  // Busca quem está em jogo e as horas declaradas. As horas de exemplo dependem do nome e da duração.
  useEffect(() => {
    const body = baseBody();
    if (!body || !validNumber(weeks, 1, 26, true)) return;
    const timer = setTimeout(() => {
      api.team(body).then((r) => setTeam(r.members)).catch(() => setTeam(null));
    }, 300);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [roles !== null, name, weeks, sheet, savedKey]);

  const hoursOf = (m: TeamMember): Hours =>
    overrides[m.id] ?? { weekly_hours: m.weekly_hours, unavailable_weeks: m.unavailable_weeks };
  const setHours = (m: TeamMember, patch: Partial<Hours>) =>
    setOverrides((o) => ({ ...o, [m.id]: { ...hoursOf(m), ...patch } }));
  // Só vão para o servidor os ajustes que mudam algo.
  const changed = (team ?? []).filter((m) => {
    const h = overrides[m.id];
    return h && (h.weekly_hours !== m.weekly_hours || h.unavailable_weeks !== m.unavailable_weeks);
  });
  const invalidHours = changed.some((m) =>
    !validNumber(overrides[m.id].weekly_hours, 0, 40) || !validNumber(overrides[m.id].unavailable_weeks, 0, 12, true));

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
      setPriority(null);
      setResult(await api.squads(id));
    });

  const proposeRoles = () =>
    run(async () => {
      const r = await api.parseBriefing(briefing);
      setRoles(r.roles);
      setOverrides({});
      if (r.name && !name.trim()) setName(r.name);
      setWeeks(r.duration_weeks);
      setParseMode(r.mode);
      setOpenId(null);
      setResult(null);
    });

  const build = () =>
    run(async () => {
      const base = baseBody();
      if (!base) return;
      // A disponibilidade ajustada viaja no corpo "custom": troca, aplicar e teste de estresse usam a mesma.
      const body: CustomBody = {
        ...base,
        availability: Object.fromEntries(changed.map((m) => [m.id, overrides[m.id]])),
      };
      setCustom(body);
      setDetail(null);
      setPriority(null);
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
            <div className="weeks-field">
              <label htmlFor="weeks">Duração (semanas)</label>
              <input id="weeks" type="number" min={1} max={26} value={weeks} onChange={(e) => setWeeks(Number(e.target.value))} />
              <div className="chips" role="group" aria-label="Duração rápida">
                {WEEK_CHIPS.map((w) => (
                  <button key={w} type="button" className={`chip ${weeks === w ? "on" : ""}`} aria-pressed={weeks === w}
                    onClick={() => setWeeks(w)}>
                    {w} sem.
                  </button>
                ))}
              </div>
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
            <button className="primary" disabled={busy || invalidHours} onClick={build}>{busy ? "Montando..." : "Montar squads"}</button>
          </div>
          {invalidHours && (
            <p className="error small">Corrija as horas da equipe: de 0 a 40 h por semana e de 0 a 12 semanas fora (número inteiro).</p>
          )}
          <ImportSheet members={sheet} onChange={changeSheet} />
          {team && team.length > 0 && (
            <details className="team">
              <summary>Ajustar disponibilidade da equipe</summary>
              <p className="muted small declared">{DECLARED_NOTE}</p>
              <p className="muted small">
                {sheet
                  ? "Horas vindas da sua planilha (8 h e 0 semanas para quem não informou)."
                  : "Sem planilha, os 24 membros de exemplo usam horas de exemplo (fictícias); quem respondeu o perfil usa o que declarou."}{" "}
                As alterações valem ao montar as squads. A média é o que sobra por semana ao longo de {weeks} semana(s),
                descontadas as semanas fora.
              </p>
              <div className="table-wrap">
                <table className="people">
                  <thead>
                    <tr>
                      <th>Pessoa</th><th>Horas livres por semana</th><th>Semanas fora</th>
                      <th className="num">Média no projeto</th>
                    </tr>
                  </thead>
                  <tbody>
                    {team.map((m) => {
                      const h = hoursOf(m);
                      const avg = validNumber(weeks, 1, 26, true) && validNumber(h.weekly_hours, 0, 40)
                        && validNumber(h.unavailable_weeks, 0, 12, true)
                        ? (h.weekly_hours * Math.max(0, weeks - h.unavailable_weeks)) / weeks : null;
                      return (
                        <tr key={m.id} className={changed.includes(m) ? "changed" : ""}>
                          <td>
                            {m.name}{m.is_novato && <span className="tag">novato</span>}
                            <span className="source block">{SOURCE_LABEL[m.source]}</span>
                          </td>
                          <td>
                            <input type="number" min={0} max={40} step={0.5}
                              value={Number.isNaN(h.weekly_hours) ? "" : h.weekly_hours}
                              aria-label={`Horas livres por semana de ${m.name}`}
                              onChange={(e) => setHours(m, { weekly_hours: e.target.value === "" ? NaN : Number(e.target.value) })} />
                          </td>
                          <td>
                            <input type="number" min={0} max={12} step={1}
                              value={Number.isNaN(h.unavailable_weeks) ? "" : h.unavailable_weeks}
                              aria-label={`Semanas fora de ${m.name}`}
                              onChange={(e) => setHours(m, { unavailable_weeks: e.target.value === "" ? NaN : Number(e.target.value) })} />
                          </td>
                          <td className="num">{avg === null ? "—" : `${num(avg)} h`}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              {changed.length > 0 && (
                <div className="row">
                  <span className="muted small">{changed.length} pessoa(s) com horas ajustadas.</span>
                  <button className="btn" onClick={() => setOverrides({})}>Desfazer ajustes</button>
                </div>
              )}
            </details>
          )}
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
            <p className="muted small hours-note">{custom ? DECLARED_NOTE : "Horas de exemplo (fictícias)."}</p>
          </div>
          <SquadBoard
            data={result}
            priority={priority}
            onPriority={setPriority}
            onDetail={(p) => { setDetail(p); window.scrollTo({ top: 0 }); }}
          />
        </section>
      )}
    </div>
  );
}
