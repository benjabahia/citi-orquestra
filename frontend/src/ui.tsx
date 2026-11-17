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
