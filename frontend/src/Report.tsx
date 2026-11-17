import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { num } from "./ui";
import type { Priority, Project, Recommendation, Squad } from "./types";

type Key = Squad["profile"];

export const TITLES: Record<Key, string> = { segura: "Seguro", evolutiva: "Evolutivo", balanceada: "Balanceado" };
const ORDER: Key[] = ["segura", "evolutiva", "balanceada"];
const PRIORITY_LABEL: Record<Priority, string> = {
  prazo: "Prazo apertado", formar: "Formar gente", equilibrio: "Equilíbrio",
};
const DECLARED_NOTE = "Disponibilidade declarada pelos membros; o sistema não verifica as horas.";
const EXAMPLE_NOTE = "Dados e horas de exemplo (fictícios).";

/** "faltam 2 h" quando as horas exigidas passam das livres (mesma regra da tela). */
function shortLabel(free: number, needed: number): string | null {
  const missing = needed - free;
  if (missing <= 0.05) return null;
  return `${missing <= 1.05 ? "falta" : "faltam"} ${num(missing)} h`;
}

function RBar({ value, tone }: { value: number; tone: "ok" | "warn" | "bad" }) {
  return (
    <span className="rp-bar"><i className={tone} style={{ width: `${Math.max(0, Math.min(100, value))}%` }} /></span>
  );
}

const riskTone = (v: number): "ok" | "warn" | "bad" => (v >= 30 ? "bad" : v >= 12 ? "warn" : "ok");

/**
 * Relatório para impressão (A4, fundo branco). Fica escondido na tela e só aparece ao imprimir.
 * Recebe o squad ATUAL (com as trocas já aplicadas) e os outros dois como estão na tela.
 */
function Report({ project, profile, squads, recommendation, custom }: {
  project: Project; profile: Key; squads: Record<Key, Squad>;
  recommendation: Recommendation | null; custom: boolean;
}) {
  const squad = squads[profile];
  const m = squad.metrics;
  const name = (id: string) => squad.slots.find((s) => s.member_id === id)?.member_name ?? "";
  const loadOf = (id: string | null) => m.loads.find((l) => l.member_id === id);
  const meters = [
    { label: "Entrega", hint: "quanto maior, melhor", value: m.entrega, tone: "ok" as const },
    { label: "Crescimento", hint: "quanto maior, melhor", value: m.crescimento, tone: "ok" as const },
    { label: "Risco", hint: "quanto menor, melhor", value: m.risco, tone: riskTone(m.risco) },
  ];
  return (
    <div id="print-root">
      <header className="rp-head">
        <img src="/logo.png" alt="" width="64" height="64" />
        <div>
          <p className="rp-brand">CITi Orquestra</p>
          <h1>{project.name}</h1>
          <p className="rp-sub">
            Squad {TITLES[profile]} · {project.duration_weeks} semanas · {new Date().toLocaleDateString("pt-BR")}
          </p>
        </div>
      </header>

      <section className="rp-meters">
        {meters.map((x) => (
          <div key={x.label} className="rp-meter">
            <span className="rp-label">{x.label}</span>
            <strong>{Math.round(x.value)}</strong>
            <RBar value={x.value} tone={x.tone} />
            <span className="rp-hint">{x.hint}</span>
          </div>
        ))}
      </section>

      <h2>Comparação dos três squads</h2>
      <table className="rp-table">
        <thead>
          <tr><th>Squad</th><th>Entrega</th><th>Crescimento</th><th>Risco</th></tr>
        </thead>
        <tbody>
          {ORDER.map((k) => {
            const mm = squads[k].metrics;
            const isRec = recommendation?.profile === k;
            return (
              <tr key={k} className={k === profile ? "current" : ""}>
                <td>
                  <strong>{TITLES[k]}</strong>
                  {k === profile && <span className="rp-note"> (este squad)</span>}
                  {isRec && recommendation && (
                    <span className="rp-badge">Recomendado · {PRIORITY_LABEL[recommendation.priority]}</span>
                  )}
                </td>
                <td>{Math.round(mm.entrega)}</td>
                <td>{Math.round(mm.crescimento)}</td>
                <td>{Math.round(mm.risco)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>

      <h2>Pessoas</h2>
      <table className="rp-table">
        <thead>
          <tr><th>Papel</th><th>Pessoa</th><th>Nível</th><th>Horas por semana</th></tr>
        </thead>
        <tbody>
          {squad.slots.map((s) => {
            const l = loadOf(s.member_id);
            const short = l ? shortLabel(l.capacity, l.demand) : null;
            return (
              <tr key={s.index}>
                <td>
                  {s.skill_label}
                  <span className="rp-note block">pede nível {s.min_level}+{s.critical ? " · crítico" : ""}</span>
                </td>
                <td>{s.member_id ? <>{s.member_name}{s.is_novato && <span className="rp-note"> (novato)</span>}</> : <em>Vaga em aberto</em>}</td>
                <td>{s.member_id ? `${s.member_level ?? 0} de 4` : "—"}</td>
                <td>
                  {l ? (
                    <>
                      {num(l.capacity)} h livres · {num(l.demand)} h exigidas
                      {short && <span className="rp-short"> {short}</span>}
                      {l.mentoring_hours > 0 && <span className="rp-note block">inclui {num(l.mentoring_hours)} h de mentoria</span>}
                    </>
                  ) : "—"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      <h2>Mentorias</h2>
      {m.mentorships.length === 0 ? (
        <p>Este squad não precisa de mentoria.</p>
      ) : (
        <ul>
          {m.mentorships.map((x, i) => (
            <li key={i}>{name(x.mentor_id)} ensina {name(x.mentee_id)} ({project.roles.find((r) => r.skill === x.skill)?.skill_label ?? x.skill})</li>
          ))}
        </ul>
      )}

      <h2>Alertas de risco</h2>
      {m.factors.length === 0 ? (
        <p>Nenhum ponto de atenção neste squad.</p>
      ) : (
        <ul>{m.factors.map((f, i) => <li key={i}>{f.message}</li>)}</ul>
      )}

      <footer className="rp-foot">{custom ? DECLARED_NOTE : EXAMPLE_NOTE}</footer>
    </div>
  );
}

/**
 * Botão "Baixar PDF": monta o relatório, abre a caixa de impressão do navegador
 * (escolha "Salvar como PDF") e remove o relatório quando a impressão termina.
 */
export function ReportButton({ project, profile, squads, recommendation, custom, className = "btn" }: {
  project: Project; profile: Key; squads: Record<Key, Squad>;
  recommendation: Recommendation | null; custom: boolean; className?: string;
}) {
  const [printing, setPrinting] = useState(false);

  useEffect(() => {
    if (!printing) return;
    const oldTitle = document.title;
    let cancelled = false;
    const finish = () => { document.title = oldTitle; setPrinting(false); };
    // O nome sugerido para o arquivo PDF vem do título da página.
    document.title = `Squad ${TITLES[profile]} - ${project.name}`;
    window.addEventListener("afterprint", finish, { once: true });
    // Espera a logo carregar para ela sair no PDF.
    const img = document.querySelector<HTMLImageElement>("#print-root img");
    const ready = !img || img.complete
      ? Promise.resolve()
      : new Promise<void>((done) => { img.onload = () => done(); img.onerror = () => done(); });
    ready.then(() => { if (!cancelled) window.print(); });
    return () => {
      cancelled = true;
      window.removeEventListener("afterprint", finish);
      document.title = oldTitle;
    };
  }, [printing, profile, project.name]);

  return (
    <>
      <button className={className} onClick={() => setPrinting(true)} disabled={printing}
        aria-label={`Baixar PDF do squad ${TITLES[profile]}`}>
        Baixar PDF
      </button>
      {printing && createPortal(
        <Report project={project} profile={profile} squads={squads} recommendation={recommendation} custom={custom} />,
        document.body,
      )}
    </>
  );
}
