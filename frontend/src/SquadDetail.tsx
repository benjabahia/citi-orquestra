import { useMemo, useState } from "react";
import { api } from "./api";
import { MentorGraph, Radar } from "./charts";
import { Bar, Delta, LevelBar, num, riskTone, useTween } from "./ui";
import type { CustomBody, Squad, SquadsResponse, StressResponse, Substitute } from "./types";

const TITLES: Record<Squad["profile"], string> = { segura: "Segura", evolutiva: "Evolutiva", balanceada: "Balanceada" };

function BigMeter({ label, hint, value, base, kind }: {
  label: string; hint: string; value: number; base: number; kind: "good" | "risk";
}) {
  const [shown] = useTween([value]);
  return (
    <div className="big-meter">
      <div className="bm-head">
        <span>{label}</span>
        <span className="muted small">{hint}</span>
      </div>
      <div className="bm-value">
        <strong>{Math.round(shown)}</strong>
        {Math.abs(value - base) >= 0.05 && (
          <span className="small">
            <Delta value={value - base} goodWhen={kind === "good" ? "up" : "down"} /> desde a sugestão
          </span>
        )}
      </div>
      <Bar value={shown} tone={kind === "risk" ? riskTone(shown) : "ok"} />
    </div>
  );
}

export default function SquadDetail({ data, profile, custom, onBack }: {
  data: SquadsResponse; profile: Squad["profile"]; custom: CustomBody | null; onBack: () => void;
}) {
  const baseline = data.squads[profile];
  const [squad, setSquad] = useState<Squad>(baseline);
  const [role, setRole] = useState<number | null>(null);
  const [subs, setSubs] = useState<Substitute[] | null>(null);
  const [showAll, setShowAll] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [changes, setChanges] = useState(0);
  const [stress, setStress] = useState<StressResponse | null>(null);

  const projectId = custom ? "custom" : data.project.id;
  const m = squad.metrics;
  const levels = useTween(squad.slots.map((x) => x.member_level ?? 0));
  const names = useMemo(() => {
    const out: Record<string, string> = {};
    squad.slots.forEach((s) => { if (s.member_id) out[s.member_id] = s.member_name!; });
    return out;
  }, [squad]);

  async function guard(job: () => Promise<void>) {
    setBusy(true);
    setError("");
    try { await job(); } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }

  const openRole = (index: number) =>
    guard(async () => {
      setRole(index);
      setShowAll(false);
      const r = await api.whatIf(projectId, { profile, assignments: squad.assignments, role_index: index, custom });
      setSubs(r.substitutes);
    });

  const apply = (memberId: string | null) =>
    guard(async () => {
      if (role === null) return;
      const r = await api.apply(projectId, { profile, assignments: squad.assignments, role_index: role, custom, member_id: memberId });
      setSquad(r.squad);
      setStress(null); // o resultado antigo não vale mais para a nova squad
      setChanges((c) => c + 1);
      setRole(null);
      setSubs(null);
    });

  const runStress = () =>
    guard(async () => {
      setStress(await api.stress(projectId, { profile, assignments: squad.assignments, custom }));
    });

  const reset = () => { setSquad(baseline); setRole(null); setSubs(null); setChanges(0); setError(""); setStress(null); };
  const loadOf = (id: string | null) => m.loads.find((l) => l.member_id === id);
  const scale = Math.max(1, ...m.loads.map((l) => Math.max(l.capacity, l.demand)));
  const visible = subs ? (showAll ? subs : subs.slice(0, 6)) : [];
  const current = role !== null ? squad.slots[role] : null;

  return (
    <div className="detail">
      <div className="detail-head">
        <button className="link" onClick={onBack}>Voltar às 3 opções</button>
        <div>
          <h2>Squad {TITLES[profile]}</h2>
          <p className="muted">{data.project.name} · {data.project.duration_weeks} semanas</p>
        </div>
        <button className="btn" onClick={reset} disabled={changes === 0}>Voltar à sugestão</button>
      </div>

      <section className="meters" aria-label="Medidores da squad">
        <BigMeter label="Entrega" hint="quanto maior, melhor" value={m.entrega} base={baseline.metrics.entrega} kind="good" />
        <BigMeter label="Crescimento" hint="quanto maior, melhor" value={m.crescimento} base={baseline.metrics.crescimento} kind="good" />
        <BigMeter label="Risco" hint="quanto menor, melhor" value={m.risco} base={baseline.metrics.risco} kind="risk" />
      </section>

      {error && <p className="error" role="alert">{error}</p>}

      <div className="two">
        <section className="panel">
          <h3>Nível por habilidade</h3>
          <p className="muted small">Quanto mais a área verde passa da linha tracejada, mais folga a squad tem naquele papel.</p>
          <Radar levels={levels} slots={squad.slots} />
        </section>
        <section className="panel">
          <h3>Mentoria</h3>
          <MentorGraph squad={squad} />
        </section>
      </div>

      <section className="panel">
        <h3>Pessoas e carga de trabalho</h3>
        <p className="muted small">Horas por semana: o risco sobe quando o papel e a mentoria pedem mais do que a pessoa tem.</p>
        <div className="table-wrap">
          <table className="people">
            <thead>
              <tr><th>Papel</th><th>Pessoa</th><th>Nível</th><th>Carga (horas por semana)</th><th><span className="sr">Ação</span></th></tr>
            </thead>
            <tbody>
              {squad.slots.map((s) => {
                const l = loadOf(s.member_id);
                const over = l ? l.demand > l.capacity + 0.05 : false;
                return (
                  <tr key={s.index} className={role === s.index ? "sel" : ""}>
                    <td>{s.skill_label}<span className="muted small block">pede nível {s.min_level}+ · {s.hours_per_week} h{s.critical ? " · crítico" : ""}</span></td>
                    <td>{s.member_id ? <>{s.member_name}{s.is_novato && <span className="tag">novato</span>}</> : <span className="gap">Vaga em aberto</span>}</td>
                    <td>{s.member_id ? <LevelBar level={s.member_level ?? 0} need={s.min_level} /> : "—"}</td>
                    <td>
                      {l ? (
                        <div className="load" title={`Disponível: ${num(l.capacity)} h. Pedido: ${num(l.demand)} h (inclui ${num(l.mentoring_hours)} h de mentoria).`}>
                          <span className="track">
                            <i className={over ? "bad" : "ok"} style={{ width: `${(l.demand / scale) * 100}%` }} />
                            <b style={{ left: `${(l.capacity / scale) * 100}%` }} />
                          </span>
                          <span className={`small ${over ? "bad-text" : ""}`}>
                            {num(l.demand)} de {num(l.capacity)} h{over ? " · sobrecarga" : ""}
                          </span>
                        </div>
                      ) : "—"}
                    </td>
                    <td className="right">
                      <button className="btn" disabled={busy} onClick={() => openRole(s.index!)}>
                        {s.member_id ? "Trocar" : "Preencher"}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      {current && subs && (
        <section className="panel subs" aria-live="polite">
          <div className="subs-head">
            <div>
              <h3>Quem pode ocupar {current.skill_label}</h3>
              <p className="muted small">
                Ordenado pelo melhor impacto para a squad {TITLES[profile]}. O sistema avisa os efeitos, mas a decisão é sua.
              </p>
            </div>
            <div className="row">
              {current.member_id && <button className="btn" disabled={busy} onClick={() => apply(null)}>Deixar vaga em aberto</button>}
              <button className="btn" onClick={() => { setRole(null); setSubs(null); }}>Fechar</button>
            </div>
          </div>
          {subs.length === 0 ? (
            <p className="empty">Ninguém disponível tem experiência nessa habilidade.</p>
          ) : (
            <div className="table-wrap">
              <table className="people">
                <thead>
                  <tr>
                    <th>Pessoa</th><th>Nível em {current.skill_label}</th>
                    <th className="num">Entrega</th><th className="num">Crescimento</th><th className="num">Risco</th>
                    <th>O que muda</th><th><span className="sr">Ação</span></th>
                  </tr>
                </thead>
                <tbody>
                  {visible.map((s) => (
                    <tr key={s.member_id}>
                      <td>{s.name}{s.is_novato && <span className="tag">novato</span>}</td>
                      <td><LevelBar level={s.skill_level} need={current.min_level} /></td>
                      <td className="num"><Delta value={s.delta_entrega} goodWhen="up" /></td>
                      <td className="num"><Delta value={s.delta_crescimento} goodWhen="up" /></td>
                      <td className="num"><Delta value={s.delta_risco} goodWhen="down" /></td>
                      <td className="small effects">
                        {s.new_issues.length > 0 && (
                          <details>
                            <summary className="bad-text">{s.new_issues.length} alerta(s) novo(s)</summary>
                            <ul>{s.new_issues.map((t, i) => <li key={i}>{t}</li>)}</ul>
                          </details>
                        )}
                        {s.resolved_issues.length > 0 && (
                          <details>
                            <summary className="good-text">Resolve {s.resolved_issues.length} alerta(s)</summary>
                            <ul>{s.resolved_issues.map((t, i) => <li key={i}>{t}</li>)}</ul>
                          </details>
                        )}
                        {s.new_issues.length === 0 && s.resolved_issues.length === 0 && <span className="muted">Sem mudança nos alertas</span>}
                      </td>
                      <td className="right"><button className="btn primary-sm" disabled={busy} onClick={() => apply(s.member_id)}>Aplicar</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {subs.length > 6 && (
            <button className="link" onClick={() => setShowAll(!showAll)}>
              {showAll ? "Mostrar menos" : `Mostrar todos os ${subs.length}`}
            </button>
          )}
        </section>
      )}

      <section className="panel stress" aria-live="polite">
        <div className="subs-head">
          <div>
            <h3>Teste de estresse: e se alguém sair?</h3>
            <p className="muted small">
              Simula a saída de cada pessoa da squad e mostra o que acontece com o risco e a entrega, do pior caso ao melhor.
            </p>
          </div>
          <button className="btn" disabled={busy} onClick={runStress}>
            {stress ? "Refazer o teste" : "Testar a squad"}
          </button>
        </div>
        {stress && stress.results.length > 0 && (
          <>
            <p className="weakest">
              <span className="badge">Ponto mais frágil</span> {stress.weakest_sentence}
            </p>
            <div className="table-wrap">
              <table className="people stress-table">
                <thead>
                  <tr>
                    <th>Pessoa</th><th>Papel</th><th>Risco depois da saída</th>
                    <th className="num">Risco</th><th className="num">Entrega</th>
                  </tr>
                </thead>
                <tbody>
                  {stress.results.map((r, i) => (
                    <tr key={r.member_id} className={i === 0 ? "frail" : ""}>
                      <td>{r.name}</td>
                      <td>{r.skill_label}{r.critical && <span className="muted small"> · crítico</span>}</td>
                      <td>
                        <div className="meter-cell">
                          <strong>{Math.round(r.risco_after)}</strong>
                          <Bar value={r.risco_after} tone={riskTone(r.risco_after)} />
                        </div>
                      </td>
                      <td className="num"><Delta value={r.delta_risco} goodWhen="down" /></td>
                      <td className="num">
                        <Delta value={r.delta_entrega} goodWhen="up" />
                        <Bar value={r.entrega_after} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </section>

      <section className="panel">
        <h3>Pontos de atenção</h3>
        {m.factors.length === 0 ? (
          <p className="muted">Nenhum ponto de atenção nesta squad.</p>
        ) : (
          <ul className="factors">{m.factors.map((f, i) => <li key={i} className={f.kind}>{f.message}</li>)}</ul>
        )}
        {changes > 0 && <p className="muted small">{changes} troca(s) aplicada(s) em relação à sugestão. {Object.keys(names).length} pessoas na squad.</p>}
      </section>
    </div>
  );
}
