import { Bar, LevelBar, riskTone } from "./ui";
import type { Squad, SquadsResponse } from "./types";

type Key = Squad["profile"];

const PROFILES: { key: Key; title: string; text: string }[] = [
  { key: "segura", title: "Segura", text: "Só quem já tem experiência." },
  { key: "evolutiva", title: "Evolutiva", text: "Novatos com mentores." },
  { key: "balanceada", title: "Balanceada", text: "Um novato com mentor." },
];

const METERS: { id: "entrega" | "crescimento" | "risco"; label: string; hint: string }[] = [
  { id: "entrega", label: "Entrega", hint: "quanto maior, melhor" },
  { id: "crescimento", label: "Crescimento", hint: "quanto maior, melhor" },
  { id: "risco", label: "Risco", hint: "quanto menor, melhor" },
];

/** Tabela comparativa: as três squads lado a lado, com as linhas alinhadas por papel. */
export default function SquadBoard({ data, onDetail }: { data: SquadsResponse; onDetail: (p: Key) => void }) {
  const roles = data.project.roles;
  return (
    <div className="table-wrap">
      <table className="compare">
        <caption className="sr">Comparação das três opções de squad para {data.project.name}</caption>
        <thead>
          <tr>
            <td />
            {PROFILES.map((p) => (
              <th key={p.key} scope="col">
                <div className="col-title">{p.title}</div>
                <div className="muted small">{p.text}</div>
                <button className="btn" onClick={() => onDetail(p.key)}>Ver detalhes</button>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {METERS.map((m) => {
            const values = PROFILES.map((p) => data.squads[p.key].metrics[m.id]);
            const best = m.id === "risco" ? Math.min(...values) : Math.max(...values);
            return (
              <tr key={m.id} className="meter-row">
                <th scope="row">
                  {m.label}
                  <span className="muted small block">{m.hint}</span>
                </th>
                {PROFILES.map((p, i) => (
                  <td key={p.key}>
                    <div className="meter-cell">
                      <strong className={values[i] === best ? "best" : ""}>{Math.round(values[i])}</strong>
                      <Bar value={values[i]} tone={m.id === "risco" ? riskTone(values[i]) : "ok"} />
                    </div>
                  </td>
                ))}
              </tr>
            );
          })}

          {roles.map((role) => (
            <tr key={role.index} className="role-row">
              <th scope="row">
                {role.skill_label}
                <span className="muted small block">nível {role.min_level}+{role.critical ? " · crítico" : ""}</span>
              </th>
              {PROFILES.map((p) => {
                const slot = data.squads[p.key].slots[role.index!];
                return (
                  <td key={p.key}>
                    {slot.member_id ? (
                      <div className="person-cell">
                        <span>
                          {slot.member_name}
                          {slot.is_novato && <span className="tag">novato</span>}
                        </span>
                        <LevelBar level={slot.member_level ?? 0} need={slot.min_level} />
                      </div>
                    ) : (
                      <span className="gap">Vaga em aberto</span>
                    )}
                  </td>
                );
              })}
            </tr>
          ))}

          <tr className="text-row">
            <th scope="row">Mentoria</th>
            {PROFILES.map((p) => {
              const sq = data.squads[p.key];
              const name = (id: string) => sq.slots.find((s) => s.member_id === id)?.member_name;
              return (
                <td key={p.key}>
                  {sq.metrics.mentorships.length === 0 ? (
                    <span className="muted">Não precisa</span>
                  ) : (
                    <ul>{sq.metrics.mentorships.map((x, i) => <li key={i}>{name(x.mentor_id)} ensina {name(x.mentee_id)}</li>)}</ul>
                  )}
                </td>
              );
            })}
          </tr>

          <tr className="text-row">
            <th scope="row">Pontos de atenção</th>
            {PROFILES.map((p) => {
              const f = data.squads[p.key].metrics.factors;
              return (
                <td key={p.key}>
                  {f.length === 0 ? (
                    <span className="muted">Nenhum</span>
                  ) : (
                    <ul className="factors">{f.map((x, i) => <li key={i} className={x.kind}>{x.message}</li>)}</ul>
                  )}
                </td>
              );
            })}
          </tr>
        </tbody>
      </table>
    </div>
  );
}
