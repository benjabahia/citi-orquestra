import { useMemo, useRef, useState } from "react";
import { api } from "./api";
import { MentorGraph, Radar } from "./charts";
import { Bar, Delta, HOURS_HELP, HoursLine, LevelBar, num, riskTone, shortOfHours, useTween } from "./ui";
import { ReportButton } from "./Report";
import type { CustomBody, Recommendation, Squad, SquadsResponse, StressResponse, Substitute } from "./types";

const TITLES: Record<Squad["profile"], string> = { segura: "Seguro", evolutiva: "Evolutivo", balanceada: "Balanceado" };

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

export default function SquadDetail({ data, profile, custom, recommendation, onBack }: {
  data: SquadsResponse; profile: Squad["profile"]; custom: CustomBody | null;
  recommendation: Recommendation | null; onBack: () => void;
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

  // Resumo para colar no chat: aviso de "copiado" por 3 s ou, se o navegador bloquear, o texto para copiar à mão.
  const [copied, setCopied] = useState(false);
  const [copyFallback, setCopyFallback] = useState<string | null>(null);
  const copiedTimer = useRef<number | undefined>(undefined);

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
      setStress(null); // o resultado antigo não vale mais para o novo squad
      setChanges((c) => c + 1);
      setRole(null);
      setSubs(null);
    });

  const runStress = () =>
    guard(async () => {
      setStress(await api.stress(projectId, { profile, assignments: squad.assignments, custom }));
    });

  const copySummary = () =>
    guard(async () => {
      setCopied(false);
      setCopyFallback(null);
      // O texto é montado no servidor (igual em todos os caminhos). O ponto mais frágil só entra se o teste já foi feito.
      const r = await api.summary({
        project_id: projectId, profile, assignments: squad.assignments, custom, include_weakest: stress !== null,
      });
      try {
        await navigator.clipboard.writeText(r.text);
        setCopied(true);
        window.clearTimeout(copiedTimer.current);
        copiedTimer.current = window.setTimeout(() => setCopied(false), 3000);
      } catch {
        setCopyFallback(r.text);
      }
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
        <div className="head-actions">
          <ReportButton project={data.project} profile={profile} squads={{ ...data.squads, [profile]: squad }}
            recommendation={recommendation} custom={custom !== null} />
          <button className="btn" onClick={copySummary} disabled={busy}>Copiar resumo</button>
          <button className="btn" onClick={reset} disabled={changes === 0}>Voltar à sugestão</button>
        </div>
      </div>
      <p className="sr" role="status">{copied ? "Resumo copiado" : ""}</p>
      {copied && <p className="copy-ok" aria-hidden="true">Resumo copiado</p>}
      {copyFallback !== null && (
        <div className="copy-fail" role="alert">
          Não consegui copiar sozinho: o navegador bloqueou o acesso à área de transferência. Selecione o texto abaixo e copie com Ctrl+C.
          <textarea readOnly value={copyFallback} onFocus={(e) => e.currentTarget.select()} aria-label="Resumo do squad" />
        </div>
      )}

      <section className="meters" aria-label="Medidores do squad">
        <BigMeter label="Entrega" hint="quanto maior, melhor" value={m.entrega} base={baseline.metrics.entrega} kind="good" />
        <BigMeter label="Crescimento" hint="quanto maior, melhor" value={m.crescimento} base={baseline.metrics.crescimento} kind="good" />
        <BigMeter label="Risco" hint="quanto menor, melhor" value={m.risco} base={baseline.metrics.risco} kind="risk" />
      </section>

      {error && <p className="error" role="alert">{error}</p>}

      <div className="two">
        <section className="panel">
          <h3>Nível por habilidade</h3>
          <p className="muted small">Quanto mais a área verde passa da linha tracejada, mais folga o squad tem naquele papel.</p>
          <Radar levels={levels} slots={squad.slots} />
        </section>
        <section className="panel">
          <h3>Mentoria</h3>
          <MentorGraph squad={squad} />
        </section>
      </div>

      <section className="panel">
        <h3>Pessoas e carga de trabalho</h3>
        <p className="muted small">Horas por semana: o risco sobe quando as horas exigidas passam das horas livres.</p>
        <p className="muted small load-help">{HOURS_HELP}</p>
        <p className="muted small load-help">
          {custom ? "Disponibilidade declarada pelos membros; o sistema não verifica as horas." : "Horas de exemplo (fictícias)."}
        </p>
        {shortOfHours(m.loads) > 0 && (
          <p className="short-summary">
            {shortOfHours(m.loads) === 1 ? "1 pessoa sem horas suficientes" : `${shortOfHours(m.loads)} pessoas sem horas suficientes`}
          </p>
        )}
        <div className="table-wrap">
          <table className="people">
            <thead>
              <tr><th>Papel</th><th>Pessoa</th><th>Nível</th><th>Horas livres × exigidas (por semana)</th><th><span className="sr">Ação</span></th></tr>
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
                        <div className="load" title={`Livres: ${num(l.capacity)} h. Exigidas: ${num(l.demand)} h (inclui ${num(l.mentoring_hours)} h de mentoria).`}>
                          <span className="track">
                            <i className={over ? "bad" : "ok"} style={{ width: `${(l.demand / scale) * 100}%` }} />
                            <b style={{ left: `${(l.capacity / scale) * 100}%` }} />
                          </span>
                          <HoursLine free={l.capacity} needed={l.demand} />
                          {l.mentoring_hours > 0 && (
                            <span className="muted small">inclui {num(l.mentoring_hours)} h de mentoria</span>
                          )}
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
                Ordenado pelo melhor impacto para o squad {TITLES[profile]}. O sistema avisa os efeitos, mas a decisão é sua.
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
              Simula a saída de cada pessoa do squad e mostra o que acontece com o risco e a entrega, do pior caso ao melhor.
            </p>
          </div>
          <button className="btn" disabled={busy} onClick={runStress}>
            {stress ? "Refazer o teste" : "Testar o squad"}
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
          <p className="muted">Nenhum ponto de atenção neste squad.</p>
        ) : (
          <ul className="factors">{m.factors.map((f, i) => <li key={i} className={f.kind}>{f.message}</li>)}</ul>
        )}
        {changes > 0 && <p className="muted small">{changes} troca(s) aplicada(s) em relação à sugestão. {Object.keys(names).length} pessoas no squad.</p>}
      </section>
    </div>
  );
}
