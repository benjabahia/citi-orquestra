"""Leitura e validação da planilha de membros (CSV) enviada pelo gerente.

Sem IA: só regras. Cada erro diz a linha e a coluna, em português, para a
pessoa conseguir corrigir o arquivo sozinha.

Colunas (nesta ordem, com este cabeçalho):
    nome, meses_no_citi, frontend, backend, banco_dados, ux_ui, gestao, qa,
    dados_ia, devops, metas
- níveis de 0 a 4 (célula vazia vale 0);
- metas: habilidades separadas por ponto e vírgula (ou "|").
"""
import csv
import io
import re

from .config import SKILLS

MIN_MEMBERS = 3
MAX_MEMBERS = 200
MAX_ERRORS = 25          # mostra só os primeiros erros, para a lista não ficar enorme
MAX_NAME = 60
MAX_MONTHS = 120

HEADER = ["nome", "meses_no_citi", *SKILLS, "metas"]

TEMPLATE_ROWS = [
    ["Ana Souza", "18", "3", "1", "0", "2", "0", "0", "0", "0", "backend;devops"],
    ["Bruno Lima", "4", "1", "2", "1", "0", "0", "1", "0", "0", "banco_dados"],
    ["Carla Dias", "30", "0", "4", "3", "0", "1", "2", "2", "3", "gestao"],
]


def template_csv() -> str:
    """CSV de exemplo (o botão "Baixar modelo" gera o mesmo conteúdo)."""
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(HEADER)
    writer.writerows(TEMPLATE_ROWS)
    return out.getvalue()


def _error(errors: list, line, column, text: str) -> None:
    where = []
    if line is not None:
        where.append(f"linha {line}")
    if column:
        where.append(f"coluna '{column}'")
    prefix = (", ".join(where) + ": ") if where else ""
    errors.append({"line": line, "column": column, "message": (prefix[:1].upper() + prefix[1:]) + text})


def _to_int(raw: str):
    raw = raw.strip()
    return int(raw) if re.fullmatch(r"\d+", raw) else None


def _detect_delimiter(header_line: str) -> str:
    # Excel em português costuma salvar com ponto e vírgula; o modelo usa vírgula.
    return "," if header_line.count(",") >= header_line.count(";") else ";"


def parse_members_csv(text: str) -> dict:
    """Devolve {"ok", "members", "errors", "more_errors"}.

    `members` já vem no formato do perfil (nome, meses, níveis > 0, metas).
    """
    text = (text or "").lstrip("﻿")
    errors: list = []

    if not text.strip():
        _error(errors, None, None, "O arquivo está vazio.")
        return _result([], errors)

    first_line = next(line for line in text.splitlines() if line.strip())
    reader = csv.reader(io.StringIO(text), delimiter=_detect_delimiter(first_line))

    header = None
    rows = []                      # (linha no arquivo, células)
    for cells in reader:
        if not any(c.strip() for c in cells):
            continue               # linha em branco
        if header is None:
            header = [c.strip().lower() for c in cells]
        else:
            rows.append((reader.line_num, cells))

    if header is None:
        _error(errors, None, None, "O arquivo está vazio.")
        return _result([], errors)

    # --- Cabeçalho ---
    for col in header:
        if col and col not in HEADER:
            _error(errors, 1, col, "coluna desconhecida. "
                   f"Use só estas colunas: {', '.join(HEADER)}.")
    for col in HEADER:
        if col not in header:
            _error(errors, 1, col, "coluna obrigatória não encontrada no cabeçalho. "
                   "Baixe o modelo para ver o formato.")
    if errors:
        return _result([], errors)
    pos = {col: header.index(col) for col in HEADER}

    # --- Quantidade ---
    if len(rows) > MAX_MEMBERS:
        _error(errors, None, None, f"A planilha tem {len(rows)} pessoas; o máximo é {MAX_MEMBERS}.")
        return _result([], errors)

    members, seen = [], {}
    for line, cells in rows:
        if len(cells) > len(header):
            _error(errors, line, None, "a linha tem mais colunas do que o cabeçalho.")
            continue

        def cell(col):
            i = pos[col]
            return cells[i].strip() if i < len(cells) else ""

        ok = True

        name = " ".join(cell("nome").split())
        if not name:
            _error(errors, line, "nome", "o nome está vazio.")
            ok = False
        elif len(name) > MAX_NAME:
            _error(errors, line, "nome", f"o nome passa de {MAX_NAME} caracteres.")
            ok = False
        else:
            key = name.casefold()
            if key in seen:
                _error(errors, line, "nome", f"o nome '{name}' está repetido (já aparece na linha {seen[key]}).")
                ok = False
            else:
                seen[key] = line

        raw_months = cell("meses_no_citi")
        months = _to_int(raw_months)
        if months is None:
            _error(errors, line, "meses_no_citi",
                   "informe um número inteiro de meses (ex.: 6)." if raw_months
                   else "o campo está vazio; informe quantos meses a pessoa tem no CITi.")
            ok = False
        elif months > MAX_MONTHS:
            _error(errors, line, "meses_no_citi", f"{months} meses passa do máximo de {MAX_MONTHS}.")
            ok = False

        skills = {}
        for skill in SKILLS:
            raw = cell(skill)
            if raw == "":
                continue           # vazio = nível 0
            level = _to_int(raw)
            if level is None or level > 4:
                _error(errors, line, skill, f"nível '{raw}' inválido; use um número inteiro de 0 a 4.")
                ok = False
            elif level > 0:
                skills[skill] = level

        goals = []
        for part in re.split(r"[;|]", cell("metas")):
            goal = part.strip().lower()
            if not goal:
                continue
            if goal not in SKILLS:
                _error(errors, line, "metas",
                       f"habilidade desconhecida '{part.strip()}'. Use: {', '.join(SKILLS)}.")
                ok = False
            elif goal not in goals:
                goals.append(goal)

        if ok:
            members.append({"name": name, "months_in_citi": months, "skills": skills, "learning_goals": goals})

    if len(rows) < MIN_MEMBERS:
        _error(errors, None, None,
               f"A planilha tem {len(rows)} pessoa(s); são necessárias pelo menos {MIN_MEMBERS}.")

    return _result(members, errors)


def _result(members: list, errors: list) -> dict:
    if errors:
        return {
            "ok": False,
            "members": [],
            "errors": errors[:MAX_ERRORS],
            "more_errors": max(0, len(errors) - MAX_ERRORS),
        }
    return {"ok": True, "members": members, "errors": [], "more_errors": 0}
