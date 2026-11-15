# Diário de uso de IA (rascunho para revisão do Benja)

Ferramenta principal: Claude (Anthropic), usado para escrever o código; o Benja revisa, entende e decide.

| Dia | Objetivo | O que a IA propôs | Aceito / corrigido / recusado |
|---|---|---|---|
| Dom | Escolher a ideia e fechar decisões de produto | Brainstorming e entrevista de 31 perguntas | Benja escolheu a ideia e aceitou/ajustou cada decisão |
| Dom | Núcleo em Python: dados, pontuação, alocação, trocas | Código inicial e testes | Corrigido várias vezes (ver abaixo) |

## Onde a IA errou e como foi corrigido
1. Sugeriu TypeScript/Next.js sem considerar que o Benja precisa revisar o código → trocado por Python/FastAPI.
2. Assumiu API paga → conferidos preços e adotado plano gratuito com resposta simulada de reserva.
3. Squads idênticas entre perfis → regra de exatamente 1 novato na Balanceada e exclusão de conjuntos repetidos.
4. Evolutiva escalava novatos sem horas → penalidade de sobrecarga na busca.
5. Projeto armadilha não mostrava risco ao remover o único back-end → pesos de papel crítico no risco e ajuste dos dados.
6. Substitutos sem nenhum nível na habilidade eram sugeridos → filtro de nível mínimo 1.

## Testes
13 testes de cenário em `backend/tests/test_scenarios.py` (todos passando).
