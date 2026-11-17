import { useRef, useState } from "react";
import { api } from "./api";
import type { ImportError, Profile } from "./types";

export const SHEET_KEY = "citi-orquestra-planilha";

export function loadSheet(): Profile[] | null {
  try {
    const data = JSON.parse(localStorage.getItem(SHEET_KEY) || "null");
    return Array.isArray(data) && data.length >= 3 ? data : null;
  } catch {
    return null;
  }
}

export function saveSheet(members: Profile[] | null) {
  try {
    if (members) localStorage.setItem(SHEET_KEY, JSON.stringify(members));
    else localStorage.removeItem(SHEET_KEY);
  } catch {
    /* sem armazenamento: a planilha vale só até fechar a página */
  }
}

/** Importar planilha de membros (CSV). Só vale para projetos criados por briefing. */
export default function ImportSheet({ members, onChange }: {
  members: Profile[] | null;
  onChange: (m: Profile[] | null) => void;
}) {
  const input = useRef<HTMLInputElement>(null);
  const [errors, setErrors] = useState<ImportError[]>([]);
  const [more, setMore] = useState(0);
  const [busy, setBusy] = useState(false);
  const [fileError, setFileError] = useState("");

  async function downloadTemplate() {
    setFileError("");
    try {
      const { csv } = await api.membersTemplate();
      const url = URL.createObjectURL(new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8" }));
      const link = document.createElement("a");
      link.href = url;
      link.download = "modelo-membros.csv";
      link.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setFileError((e as Error).message);
    }
  }

  async function onFile(file: File | undefined) {
    if (!file) return;
    setErrors([]);
    setMore(0);
    setFileError("");
    setBusy(true);
    try {
      const result = await api.importMembers(await file.text());
      if (result.ok) {
        onChange(result.members);
      } else {
        setErrors(result.errors);
        setMore(result.more_errors);
      }
    } catch (e) {
      setFileError((e as Error).message);
    } finally {
      setBusy(false);
      if (input.current) input.current.value = ""; // permite escolher o mesmo arquivo de novo
    }
  }

  return (
    <div className="sheet">
      <h3>Usar a minha planilha de membros</h3>
      {members ? (
        <div className="sheet-on" role="status">
          <strong>Usando {members.length} membros da sua planilha</strong>
          <button className="btn" onClick={() => { setErrors([]); onChange(null); }}>Voltar aos dados de exemplo</button>
        </div>
      ) : (
        <p className="muted small">
          Sem planilha, os squads usam os 24 membros de exemplo. Importe um CSV para montar este projeto com a sua equipe.
        </p>
      )}
      <div className="row">
        <button className="btn" onClick={downloadTemplate}>Baixar modelo</button>
        <button className="btn" disabled={busy} onClick={() => input.current?.click()}>
          {busy ? "Lendo..." : members ? "Trocar planilha" : "Importar planilha (CSV)"}
        </button>
        <input ref={input} type="file" accept=".csv,text/csv" hidden aria-label="Arquivo CSV de membros"
          onChange={(e) => onFile(e.target.files?.[0])} />
      </div>
      <p className="muted small">
        Colunas: nome, meses_no_citi, as 8 habilidades (nível de 0 a 4) e metas (habilidades separadas por ponto e vírgula).
        Aceita de 3 a 200 pessoas. Os dados ficam só neste navegador e não são salvos no servidor.
      </p>
      {fileError && <p className="error" role="alert">{fileError}</p>}
      {errors.length > 0 && (
        <div className="sheet-errors" role="alert">
          <strong>A planilha não foi importada. Corrija e envie de novo:</strong>
          <ul>{errors.map((e, i) => <li key={i}>{e.message}</li>)}</ul>
          {more > 0 && <p className="small">...e mais {more} erro(s).</p>}
        </div>
      )}
    </div>
  );
}
