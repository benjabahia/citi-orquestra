<p align="center">
  <img src="assets/logo.png" alt="Logo CITi Orquestra" width="260">
</p>

<h1 align="center">CITi Orquestra</h1>

<p align="center"><b>Monte o squad certo e veja o impacto antes de decidir.</b></p>

Ferramenta interna do CITi que monta 3 squads por projeto (Segura, Evolutiva e Balanceada) a partir das habilidades e da disponibilidade dos membros, e mostra o impacto de cada troca de pessoa antes da decisão.

**Site no ar:** https://citi-orquestra.onrender.com
**Uso de IA no desenvolvimento:** [AI_LOG.md](AI_LOG.md)

> Status: site publicado e em refinamento. A documentação final e o link do vídeo entram ao fim do projeto.

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

## Rodar o site completo
O site (React) já vem construído em `frontend/dist` e é servido pela própria API:
```
cd backend
pip install -r requirements.txt
python -m uvicorn app.api:app
```
Abra http://127.0.0.1:8000. Para alterar o front-end: `cd frontend && npm install && npm run build`.

## IA (opcional)
Sem configuração, o site funciona em **modo simulado** (regras simples) e avisa isso na tela.
Para usar o modelo do Groq, crie `backend/.env` (arquivo ignorado pelo Git) com `GROQ_API_KEY=sua_chave`.
A IA só interpreta texto; quem decide as squads e os níveis é o algoritmo.
