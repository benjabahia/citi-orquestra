# CITi Orquestra

Ferramenta interna do CITi que monta 3 squads por projeto (Segura, Evolutiva e Balanceada) a partir das habilidades e da disponibilidade dos membros, e mostra o impacto de cada troca de pessoa antes da decisão.

> Status: núcleo em Python e API (FastAPI) prontos, com 18 testes. Interface, chat com IA e deploy vêm nas próximas etapas.

## Como o núcleo funciona
- **O algoritmo decide, a IA só interpreta e explica.** Pontuação + restrições + busca local (hill climbing).
- Três medidores de 0 a 100: **Entrega**, **Crescimento** e **Risco**.
- Mentoria: novato (menos de 6 meses) ou pessoa 2+ níveis abaixo do exigido precisa de mentor nível 3+ na mesma habilidade (máx. 2 mentorados por mentor).
- Troca de pessoa: lista de substitutos ordenada por impacto, com variação dos medidores. Avisa, mas não bloqueia.
- Tudo configurável em `backend/app/config.py`.

## Rodar os testes
```
cd backend
pip install -r requirements.txt
python -m pytest -q
python scripts/demo_cli.py pagamentos
```
Dados: 24 membros e 6 projetos sintéticos (incluindo o projeto "pagamentos", onde só uma pessoa domina back-end).

## Rodar a API
```
cd backend
pip install -r requirements.txt
uvicorn app.api:app --reload
```
Documentação interativa: http://127.0.0.1:8000/docs
