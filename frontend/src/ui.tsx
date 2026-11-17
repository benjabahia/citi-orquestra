import { useEffect, useRef, useState } from "react";

export const reduceMotion = () =>
  typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/** Anima de um conjunto de números até o novo (usado nos medidores e no radar). */
export function useTween(target: number[], ms = 450): number[] {
  const [value, setValue] = useState(target);
  const current = useRef(target);
  useEffect(() => {
    const from = current.current;
    if (reduceMotion() || from.length !== target.length) {
      current.current = target;
      setValue(target);
      return;
    }
    let frame = 0;
    const start = performance.now();
    const step = (now: number) => {
      const t = Math.min(1, (now - start) / ms);
      const eased = 1 - Math.pow(1 - t, 3);
      const next = target.map((v, i) => from[i] + (v - from[i]) * eased);
      current.current = next;
      setValue(next);
      if (t < 1) frame = requestAnimationFrame(step);
    };
    frame = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frame);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target.join("|")]);
  return value;
}

export const num = (n: number, digits = 1) =>
  n.toLocaleString("pt-BR", { maximumFractionDigits: digits });

export function signed(n: number): string {
  if (Math.abs(n) < 0.05) return "0";
  return `${n > 0 ? "+" : "−"}${num(Math.abs(n))}`;
}

/** Cor do risco: faixas simples e iguais em todo o site. */
export const riskTone = (v: number) => (v >= 30 ? "bad" : v >= 12 ? "warn" : "ok");

/** Quatro segmentos: nível 0 a 4. Fácil de comparar de relance. */
export function LevelBar({ level, need }: { level: number; need?: number }) {
  return (
    <span className="levelbar" role="img" aria-label={`Nível ${level} de 4${need ? `, o papel pede ${need}` : ""}`}>
      {[1, 2, 3, 4].map((n) => (
        <i key={n} className={n <= level ? (need && level < need ? "on low" : "on") : ""} />
      ))}
    </span>
  );
}

export function Bar({ value, tone = "ok" }: { value: number; tone?: string }) {
  return (
    <span className="bar" aria-hidden="true">
      <i className={tone} style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
    </span>
  );
}

export function Delta({ value, goodWhen }: { value: number; goodWhen: "up" | "down" }) {
  if (Math.abs(value) < 0.05) return <span className="delta zero">0</span>;
  const good = goodWhen === "up" ? value > 0 : value < 0;
  return <span className={`delta ${good ? "good" : "bad"}`}>{signed(value)}</span>;
}

/** Texto de ajuda usado na tabela comparativa e na tela de detalhes. */
export const HOURS_HELP =
  "Livres: horas por semana que a pessoa tem neste projeto (o que foi declarado, descontadas as semanas fora). " +
  "Exigidas: horas do papel mais 2 h por semana para cada pessoa que ela mentora.";

/** "4 h livres · 6 h exigidas", com a etiqueta "faltam 2 h" quando as exigidas passam das livres. */
export function HoursLine({ free, needed }: { free: number; needed: number }) {
  const short = needed - free;
  return (
    <span className="hours-line">
      <span><strong>{num(free)} h</strong> livres · {num(needed)} h exigidas</span>
      {short > 0.05 && <span className="short-tag">{short <= 1.05 ? "falta" : "faltam"} {num(short)} h</span>}
    </span>
  );
}

/** Pessoas cujas horas exigidas passam das livres. */
export const shortOfHours = (loads: { capacity: number; demand: number }[]) =>
  loads.filter((l) => l.demand > l.capacity + 0.05).length;

/** Campo de número com botões de sugestão rápida (ex.: 2, 4, 6 h). */
export function NumberField({ id, value, onChange, min, max, step = 1, unit, suggestions = [], label }: {
  id: string; value: number | null; onChange: (v: number | null) => void;
  min: number; max: number; step?: number; unit?: string; suggestions?: number[]; label?: string;
}) {
  const invalid = value !== null && (value < min || value > max || (step === 1 && !Number.isInteger(value)));
  return (
    <div className="number-field">
      <div className="number-row">
        <input id={id} type="number" min={min} max={max} step={step} value={value ?? ""} aria-label={label}
          aria-invalid={invalid}
          onChange={(e) => onChange(e.target.value === "" ? null : Number(e.target.value))} />
        {unit && <span className="muted small">{unit}</span>}
      </div>
      {suggestions.length > 0 && (
        <div className="chips">
          {suggestions.map((s) => (
            <button key={s} type="button" className={`chip ${value === s ? "on" : ""}`} aria-pressed={value === s}
              onClick={() => onChange(s)}>
              {s}
            </button>
          ))}
        </div>
      )}
      {invalid && (
        <p className="error small">
          Use {step === 1 ? "um número inteiro" : "um número"} de {min} a {max}.
        </p>
      )}
    </div>
  );
}

export const validNumber = (v: number | null, min: number, max: number, integer = false) =>
  v !== null && !Number.isNaN(v) && v >= min && v <= max && (!integer || Number.isInteger(v));
