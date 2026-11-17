import { useEffect, useState } from "react";
import { api } from "./api";
import { loadSavedMembers, STORAGE_KEY } from "./Manager";
import type { Meta, Mode, Profile, Question } from "./types";

interface Answers {
  areas: string[];
  levels: Record<string, number>;
  months: number | null;
  goals: string[];
  open: string;
}

const EMPTY: Answers = { areas: [], levels: {}, months: null, goals: [], open: "" };

export default function Member({ meta }: { meta: Meta }) {
  const [questions, setQuestions] = useState<Question[]>([]);
  const [name, setName] = useState("");
  const [answers, setAnswers] = useState<Answers>(EMPTY);
  const [step, setStep] = useState(0); // 0 = nome, 1..n = perguntas, n+1 = confirmação
  const [review, setReview] = useState<{
    profile: Profile;
    suggested_skills: { skill: string; skill_label: string }[];
    summary: string;
    mode: Mode;
  } | null>(null);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  useEffect(() => {
    api.questions().then((r) => setQuestions(r.questions)).catch((e) => setError(e.message));
  }, []);

  const total = questions.length;
  const q = step >= 1 && step <= total ? questions[step - 1] : null;

  function canAdvance(): boolean {
    if (step === 0) return name.trim().length > 1;
    if (!q) return false;
    if (q.id === "areas") return answers.areas.length > 0;
    if (q.id === "levels") return answers.areas.every((a) => answers.levels[a] !== undefined);
    if (q.id === "months") return answers.months !== null;
    return true; // metas e pergunta aberta são opcionais
  }

  const toggle = (list: string[], value: string, max?: number) =>
    list.includes(value) ? list.filter((v) => v !== value) : max && list.length >= max ? list : [...list, value];

  async function next() {
    setError("");
    if (step < total) return setStep(step + 1);
    try {
      setReview(await api.interpret(name.trim(), answers));
      setStep(total + 1);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  function addSuggestion(skill: string) {
    setAnswers((a) => ({ ...a, areas: a.areas.includes(skill) ? a.areas : [...a.areas, skill] }));
    setReview(null);
    setStep(questions.findIndex((x) => x.id === "levels") + 1);
  }

  function save() {
    if (!review) return;
    const others = loadSavedMembers().filter((m) => m.name !== review.profile.name);
    localStorage.setItem(STORAGE_KEY, JSON.stringify([...others, review.profile]));
    setDone(true);
  }

  if (done) {
    return (
      <section className="panel narrow">
        <h2>Perfil salvo</h2>
        <p>
          Obrigado, {name.trim()}. Seu perfil já entra nas próximas squads montadas na aba do gerente. Você pode
          refazer o chat quando mudar de nível.
        </p>
        <button className="primary" onClick={() => { setAnswers(EMPTY); setName(""); setStep(0); setReview(null); setDone(false); }}>
          Responder de novo
        </button>
      </section>
    );
  }

  return (
    <section className="panel narrow">
      <p className="muted small">
        Só você e o gerente do projeto veem o resultado (níveis, disponibilidade e objetivo), nunca o texto bruto.
      </p>
      {total > 0 && <p className="muted small">{step <= total ? `Passo ${step + 1} de ${total + 2}` : `Passo ${total + 2} de ${total + 2}`}</p>}

      {step === 0 && (
        <div className="q">
          <label htmlFor="nome">Qual é o seu nome?</label>
          <input id="nome" value={name} onChange={(e) => setName(e.target.value)} />
        </div>
      )}

      {q?.type === "multi" && (
        <div className="q">
          <p className="qtext">{q.text}</p>
          <div className="chips">
            {q.options!.map((o) => {
              const list = q.id === "areas" ? answers.areas : answers.goals;
              const on = list.includes(String(o.value));
              return (
                <button
                  key={o.value}
                  className={`chip ${on ? "on" : ""}`}
                  aria-pressed={on}
                  onClick={() =>
                    setAnswers((a) =>
                      q.id === "areas"
                        ? { ...a, areas: toggle(a.areas, String(o.value)) }
                        : { ...a, goals: toggle(a.goals, String(o.value), q.max) },
                    )
                  }
                >
                  {o.label}
                </button>
              );
            })}
          </div>
          {q.optional !== false && q.id === "goals" && <p className="muted small">Pode pular se não tiver preferência.</p>}
        </div>
      )}

      {q?.type === "levels" && (
        <div className="q">
          <p className="qtext">{q.text}</p>
          {answers.areas.map((area) => (
            <fieldset key={area}>
              <legend>{meta.skills[area]}</legend>
              {q.options!.map((o) => (
                <label key={o.value} className="radio">
                  <input
                    type="radio"
                    name={`lvl-${area}`}
                    checked={answers.levels[area] === Number(o.value)}
                    onChange={() => setAnswers((a) => ({ ...a, levels: { ...a.levels, [area]: Number(o.value) } }))}
                  />
                  {o.label}
                </label>
              ))}
            </fieldset>
          ))}
        </div>
      )}

      {q?.type === "choice" && (
        <div className="q">
          <p className="qtext">{q.text}</p>
          {q.options!.map((o) => (
            <label key={o.value} className="radio">
              <input type="radio" name="months" checked={answers.months === Number(o.value)} onChange={() => setAnswers((a) => ({ ...a, months: Number(o.value) }))} />
              {o.label}
            </label>
          ))}
        </div>
      )}

      {q?.type === "open" && (
        <div className="q">
          <label htmlFor="open" className="qtext">{q.text}</label>
          <textarea id="open" rows={4} value={answers.open} onChange={(e) => setAnswers((a) => ({ ...a, open: e.target.value }))} placeholder="Opcional" />
        </div>
      )}

      {step === total + 1 && review && (
        <div className="q">
          <p className="qtext">Confira o que o sistema entendeu</p>
          <ul className="summary">
            <li>{review.profile.name}, {review.profile.months_in_citi < 6 ? "novato(a)" : "com mais de 6 meses de CITi"}.</li>
            {Object.entries(review.profile.skills).map(([s, l]) => (
              <li key={s}>{meta.skills[s]}: nível {l} ({meta.levels[String(l)]})</li>
            ))}
            {review.profile.learning_goals.length > 0 && (
              <li>Quer aprender: {review.profile.learning_goals.map((g) => meta.skills[g]).join(", ")}</li>
            )}
          </ul>
          {review.summary && <p className="muted">{review.summary}</p>}
          {review.suggested_skills.length > 0 && (
            <div className="suggest">
              <p>
                Pelo seu texto, você também pode ter experiência em outras áreas. Quer adicionar e escolher o
                nível?
              </p>
              <div className="chips">
                {review.suggested_skills.map((s) => (
                  <button key={s.skill} className="chip" onClick={() => addSuggestion(s.skill)}>
                    Adicionar {s.skill_label}
                  </button>
                ))}
              </div>
            </div>
          )}
          <p className="muted small">
            Os níveis vêm das frases que você escolheu. A IA não define nível de ninguém. Ao salvar, você
            concorda em usar esses dados para montar squads.
          </p>
        </div>
      )}

      {error && <p className="error" role="alert">{error}</p>}

      <div className="row">
        {step > 0 && step <= total + 1 && (
          <button className="ghost" onClick={() => setStep(step - 1)}>Voltar</button>
        )}
        {step <= total && (
          <button className="primary" disabled={!canAdvance()} onClick={next}>
            {step === total ? "Revisar" : "Continuar"}
          </button>
        )}
        {step === total + 1 && <button className="primary" onClick={save}>Salvar perfil</button>}
      </div>
    </section>
  );
}
