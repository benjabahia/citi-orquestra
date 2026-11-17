import { useEffect, useRef, useState } from "react";
import { api } from "./api";
import type { ChatMessage, CoherenceWarning, DraftSkill, Meta, Profile, Question } from "./types";

const MAX_CHARS = 1500;
const PRIVACY =
  "O que você escrever aqui é enviado ao modelo de IA (Groq) para montar o rascunho e não é guardado no servidor.";

type Step = "start" | "open" | "chat" | "review" | "noEvidence";

const NEGATIVE = /^(n|não|nao|nope|nunca|nada|ainda não|ainda nao|não sei|nao sei|não tenho|nao tenho)[.!\s]*$/i;

/** Entrevista com IA: a IA PROPÕE os níveis, a pessoa CONFIRMA. Só aparece com a IA real ligada. */
export default function Interview({ meta, questions, onSave, onUseForm }: {
  meta: Meta;
  questions: Question[];
  onSave: (profile: Profile) => void;
  onUseForm: () => void;
}) {
  const monthQ = questions.find((q) => q.id === "months");
  const goalQ = questions.find((q) => q.id === "goals");
  const anchors = questions.find((q) => q.id === "levels")?.options ?? [];

  const [step, setStep] = useState<Step>("start");
  const [name, setName] = useState("");
  const [months, setMonths] = useState<number | null>(null);
  const [history, setHistory] = useState<ChatMessage[]>([]);
  const [question, setQuestion] = useState<string | null>(null);
  const [answer, setAnswer] = useState("");
  const [draft, setDraft] = useState<DraftSkill[]>([]);
  const [levels, setLevels] = useState<Record<string, number>>({});
  const [warnings, setWarnings] = useState<CoherenceWarning[]>([]);
  const [noEvidence, setNoEvidence] = useState("");
  const [goals, setGoals] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const checkId = useRef(0);

  async function guard(job: () => Promise<void>) {
    setBusy(true);
    setError("");
    try {
      await job();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const who = () => ({ name: name.trim(), months_in_citi: months! });

  /** Manda a conversa e recebe a próxima pergunta; quando acaba, pede o rascunho. */
  const advance = (h: ChatMessage[]) =>
    guard(async () => {
      const next = await api.interviewNext({ ...who(), history: h });
      if (!next.done && next.question) {
        setHistory([...h, { role: "assistant", text: next.question }]);
        setQuestion(next.question);
        setStep("chat");
        return;
      }
      await propose(h);
    });

  async function propose(h: ChatMessage[]) {
    const r = await api.interviewPropose({ ...who(), history: h });
    setHistory(h);
    setQuestion(null);
    if (r.status === "sem_evidencia") {
      // Não é erro: a IA não achou evidência. A pessoa pode contar mais ou usar o formulário.
      setNoEvidence(r.message ?? "");
      setWarnings(r.warnings);
      setStep("noEvidence");
      return;
    }
    setDraft(r.skills);
    setLevels(Object.fromEntries(r.skills.map((s) => [s.skill, s.level])));
    setWarnings(r.warnings);
    setQuestion(null);
    setStep("review");
  }

  /** Volta à pergunta aberta mantendo o que a pessoa já escreveu (sem os "não"). */
  function tellMore() {
    const kept = history
      .filter((m) => m.role === "user" && !NEGATIVE.test(m.text.trim()))
      .map((m) => m.text)
      .join("\n");
    setAnswer(kept.slice(0, MAX_CHARS));
    setHistory([]);
    setWarnings([]);
    setNoEvidence("");
    setStep("open");
  }

  function send() {
    const text = answer.trim();
    if (!text) return;
    const h: ChatMessage[] = [...history, { role: "user", text }];
    setAnswer("");
    setHistory(h);
    advance(h);
  }

  // Quando a pessoa muda um nível, as regras de coerência (no servidor, sem IA) refazem os avisos.
  useEffect(() => {
    if (step !== "review" || months === null) return;
    const id = ++checkId.current;
    api.interviewCheck({ months_in_citi: months, skills: levels, history })
      .then((r) => { if (id === checkId.current) setWarnings(r.warnings); })
      .catch(() => undefined); // se falhar, os avisos anteriores continuam na tela
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [levels]);

  const remove = (skill: string) =>
    setLevels((l) => Object.fromEntries(Object.entries(l).filter(([k]) => k !== skill)));

  const save = () =>
    guard(async () => {
      const areas = Object.keys(levels);
      const r = await api.interpret(name.trim(), { areas, levels, months, goals, open: "" });
      onSave(r.profile);
    });

  const asked = history.filter((m) => m.role === "assistant").length;
  const kept = draft.filter((d) => d.skill in levels);
  const general = warnings.filter((w) => !w.skill);

  return (
    <div className="interview">
      <p className="muted small">
        Entrevista com IA: a IA faz algumas perguntas e propõe um rascunho. Você revisa e escolhe o nível final de cada
        habilidade.
      </p>

      {step === "start" && (
        <>
          <div className="q">
            <label htmlFor="iv-nome">Qual é o seu nome?</label>
            <input id="iv-nome" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          {monthQ && (
            <div className="q">
              <p className="qtext">{monthQ.text}</p>
              {monthQ.options!.map((o) => (
                <label key={o.value} className="radio">
                  <input type="radio" name="iv-months" checked={months === Number(o.value)} onChange={() => setMonths(Number(o.value))} />
                  {o.label}
                </label>
              ))}
            </div>
          )}
          <div className="row">
            <button className="primary" disabled={name.trim().length < 2 || months === null} onClick={() => setStep("open")}>
              Continuar
            </button>
          </div>
        </>
      )}

      {(step === "open" || step === "chat") && (
        <div className="q">
          <p className="privacy" role="note">{PRIVACY}</p>
          {history.length > 0 && (
            <ol className="chat" aria-label="Conversa">
              {history.map((m, i) => (
                <li key={i} className={m.role}>
                  <span className="who">{m.role === "user" ? "Você" : "IA"}</span>
                  {m.text}
                </li>
              ))}
            </ol>
          )}
          {!busy && !error && (
            <>
              <label htmlFor="iv-text" className="qtext">
                {step === "open" ? "Conte o que você já fez em tecnologia (projetos, cursos, estágio)" : question}
              </label>
              <textarea id="iv-text" rows={4} maxLength={MAX_CHARS} value={answer} onChange={(e) => setAnswer(e.target.value)} />
              <p className="muted small">
                {answer.length} de {MAX_CHARS} caracteres
                {step === "chat" && ` · pergunta ${asked} de no máximo 3`}
              </p>
              <div className="row">
                <button className="primary" disabled={!answer.trim()} onClick={send}>Enviar</button>
                {step === "chat" && (
                  <button className="ghost" onClick={() => guard(() => propose(history.slice(0, -1)))}>
                    Pular e ver o rascunho
                  </button>
                )}
              </div>
            </>
          )}
        </div>
      )}

      {busy && <p className="thinking" role="status">Pensando… isso pode levar alguns segundos.</p>}

      {step === "noEvidence" && (
        <div className="q" role="status">
          <p className="qtext">{noEvidence}</p>
          {warnings.map((w, i) => (
            <p key={i} className="warn-box"><span className="warn-tag">Vale revisar</span> {w.message}</p>
          ))}
          <div className="row">
            <button className="primary" onClick={tellMore}>Contar mais</button>
            <button className="ghost" onClick={onUseForm}>Usar o formulário</button>
          </div>
        </div>
      )}

      {step === "review" && (
        <div className="q">
          <p className="qtext">Confira o rascunho</p>
          <p className="muted small">
            A IA propôs um nível para cada habilidade que você citou. Troque o que não estiver certo ou remova. O nível
            que vale é o que você escolher aqui.
          </p>
          {general.map((w, i) => (
            <p key={i} className="warn-box"><span className="warn-tag">Vale revisar</span> {w.message}</p>
          ))}
          {kept.length === 0 && <p className="empty">Nenhuma habilidade no perfil. Use o formulário para adicionar.</p>}
          {kept.map((d) => {
            const own = warnings.filter((w) => w.skill === d.skill);
            return (
              <fieldset key={d.skill} className="draft">
                <legend>{d.skill_label}</legend>
                <p className="muted small">
                  A IA propôs: <strong className="proposed">{d.anchor}</strong>
                </p>
                {d.evidence && <p className="evidence">“{d.evidence}”</p>}
                <div className="row draft-row">
                  <select value={levels[d.skill]} aria-label={`Nível em ${d.skill_label}`}
                    onChange={(e) => setLevels((l) => ({ ...l, [d.skill]: Number(e.target.value) }))}>
                    {anchors.filter((o) => Number(o.value) > 0).map((o) => (
                      <option key={o.value} value={Number(o.value)}>{o.value} · {o.label}</option>
                    ))}
                  </select>
                  <button className="ghost" onClick={() => remove(d.skill)}>Remover</button>
                </div>
                {own.map((w, i) => (
                  <p key={i} className="warn-box"><span className="warn-tag">Vale revisar</span> {w.message}</p>
                ))}
              </fieldset>
            );
          })}

          {goalQ && (
            <div className="q">
              <p className="qtext">{goalQ.text}</p>
              <div className="chips">
                {goalQ.options!.map((o) => {
                  const v = String(o.value);
                  const on = goals.includes(v);
                  return (
                    <button key={v} className={`chip ${on ? "on" : ""}`} aria-pressed={on}
                      onClick={() => setGoals((g) => on ? g.filter((x) => x !== v) : g.length >= (goalQ.max ?? 2) ? g : [...g, v])}>
                      {o.label}
                    </button>
                  );
                })}
              </div>
              <p className="muted small">Pode pular se não tiver preferência.</p>
            </div>
          )}
          <p className="muted small">
            Os avisos não impedem nada: se o nível estiver certo, salve mesmo assim. Ao salvar, você concorda em usar
            esses dados para montar squads.
          </p>
          <div className="row">
            <button className="primary" disabled={busy || kept.length === 0} onClick={save}>Salvar perfil</button>
          </div>
        </div>
      )}

      {error && (
        <div className="sheet-errors" role="alert">
          <p>{error}</p>
          <div className="row">
            <button className="primary" onClick={onUseForm}>Usar o formulário</button>
            {step !== "start" && step !== "review" && (
              <button className="ghost" onClick={() => {
                // Tenta de novo a última etapa: se a conversa termina com a resposta da pessoa, reenvia.
                const last = history[history.length - 1];
                if (last?.role === "user") advance(history);
                else setError("");
              }}>
                Tentar de novo
              </button>
            )}
          </div>
        </div>
      )}

      {!error && step !== "review" && step !== "noEvidence" && (
        <button className="link" onClick={onUseForm}>Prefiro responder o formulário</button>
      )}
    </div>
  );
}
