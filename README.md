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
- Perfil do membro: formulário com frases-âncora ou, com a IA ativa, entrevista com IA. Nos dois casos o nível final é o que a pessoa confirma.

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

### Entrevista com IA (aba Membro)
Só aparece com a IA ativa; sem ela, a aba Membro mostra o formulário de sempre e avisa o modo.
1. A pessoa informa nome e tempo de CITi e conta o que já fez em tecnologia.
2. A IA faz de 1 a 3 perguntas curtas de acompanhamento, uma por vez (fez sozinho? foi projeto real? ensinou alguém?).
3. A IA propõe um rascunho: habilidade, nível (uma das 5 frases-âncora) e um trecho do texto como evidência.
4. A pessoa revisa, troca ou remove cada nível, escolhe até 2 metas e salva. O perfil é igual ao do formulário.

Avisos amarelos "Vale revisar" aparecem quando algo não bate (nível 4 em 3 ou mais áreas, nível 3 ou 4 sem evidência no texto, novato com nível alto sem entrega real). Quem decide os avisos são regras em Python, não a IA, e eles não impedem o salvamento.

Segurança: toda resposta da IA é validada (habilidade existente, nível de 0 a 4, evidência curta); se vier fora do formato, a tela volta ao formulário. O texto da pessoa é tratado como dado, nunca como instrução, e não é guardado no servidor. O nome não é enviado à IA.

Endpoints: `POST /api/profile/interview/next`, `POST /api/profile/interview/propose` e `POST /api/profile/interview/check` (refaz os avisos, sem IA). Limites: 3 perguntas, 1500 caracteres por resposta, 10 mensagens. Código em `backend/app/ai/interview.py`.
