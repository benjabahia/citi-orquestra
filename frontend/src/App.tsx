import { useEffect, useState } from "react";
import { api } from "./api";
import type { Meta, Mode } from "./types";
import Manager from "./Manager";
import Member from "./Member";

type Tab = "gerente" | "membro";

export default function App() {
  const [tab, setTab] = useState<Tab>("gerente");
  const [meta, setMeta] = useState<Meta | null>(null);
  const [mode, setMode] = useState<Mode | null>(null);

  useEffect(() => {
    api.meta().then(setMeta).catch(() => undefined);
    api.aiStatus().then((s) => setMode(s.mode)).catch(() => undefined);
  }, []);

  return (
    <>
      <div className="glow" aria-hidden="true" />
      <header className="nav-wrap">
        <nav className="nav" aria-label="Principal">
          <span className="brand">
            <span className="mark" aria-hidden="true" />
            CITi <span className="light">Orquestra</span>
          </span>
          <div className="tabs" role="tablist" aria-label="Perfil de uso">
            <button role="tab" aria-selected={tab === "gerente"} className={tab === "gerente" ? "on" : ""} onClick={() => setTab("gerente")}>
              Gerente de projeto
            </button>
            <button role="tab" aria-selected={tab === "membro"} className={tab === "membro" ? "on" : ""} onClick={() => setTab("membro")}>
              Membro
            </button>
          </div>
          {mode && (
            <span className={`mode ${mode}`} title={mode === "simulado"
              ? "A leitura de briefing e do chat usa regras simples, sem IA. A montagem das squads é a mesma nos dois modos."
              : "A leitura de briefing e do chat usa um modelo de linguagem. A montagem das squads é feita pelo algoritmo."}>
              {mode === "simulado" ? "IA em modo simulado" : "IA ativa"}
            </span>
          )}
        </nav>
      </header>

      <div className="shell">
        <section className="hero">
          {tab === "gerente" ? (
            <>
              <h1>Monte o squad certo <span className="light">e veja o impacto antes de decidir.</span></h1>
              <p>
                Cole o briefing, revise os papéis e compare três opções de squad por entrega, crescimento e risco.
                Troque pessoas e acompanhe o efeito na hora.
              </p>
            </>
          ) : (
            <>
              <h1>Seu perfil <span className="light">em cinco perguntas.</span></h1>
              <p>Você escolhe a frase que descreve onde está hoje. Os níveis saem das suas respostas, nunca da IA.</p>
            </>
          )}
          {mode === "simulado" && (
            <p className="note">
              Modo simulado: briefing e chat são lidos por regras simples. Com a chave da IA no servidor, um modelo de
              linguagem assume essa parte. A montagem das squads é a mesma nos dois modos.
            </p>
          )}
        </section>

        <main>{meta && (tab === "gerente" ? <Manager meta={meta} /> : <Member meta={meta} />)}</main>

        <footer className="foot">
          <span>CITi Orquestra · protótipo para o desafio O Escopo é Seu</span>
          <span>Dados de membros e projetos são fictícios.</span>
        </footer>
      </div>
    </>
  );
}
