# Diário de uso de IA (rascunho para revisão do Benja)

Ferramenta principal: Claude (Anthropic), usado para escrever o código; o Benja revisa, entende e decide.

| Dia | Objetivo | O que a IA propôs | Aceito / corrigido / recusado |
|---|---|---|---|
| Dom | Escolher a ideia e fechar decisões de produto | Brainstorming e entrevista de 31 perguntas | Benja escolheu a ideia e aceitou/ajustou cada decisão |
| Seg | Novo visual sóbrio, tabela comparativa, tela de detalhes (radar, carga, grafo de mentoria) e troca de pessoa com animação | Código, SVG próprio e 1 teste novo | Aceito após revisão visual por screenshot; grafo de mentoria refeito (setas curtas) |
| Seg | Redesenho no visual do site do CITi (fundo escuro, verde #00DB58, botões em pílula, menu flutuante) e radar refeito para comparar nível real × exigido | CSS e componentes | Benja pediu o redesenho tendo citi.org.br como referência e apontou que o radar era igual nas 3 squads; ambos corrigidos |
| Dom | API FastAPI (projetos, squads, substitutos, aplicar troca) | Endpoints e 5 testes | Aceito após revisão |
| Seg | Adaptador Groq com reserva simulada, leitura de briefing, chat de perfil, tela React | Código e 15 testes novos | Aceito após revisão; verificado por screenshot e fluxo completo no navegador |
| Dom | Núcleo em Python: dados, pontuação, alocação, trocas | Código inicial e testes | Corrigido várias vezes (ver abaixo) |

## Onde a IA errou e como foi corrigido
1. Sugeriu TypeScript/Next.js sem considerar que o Benja precisa revisar o código → trocado por Python/FastAPI.
2. Assumiu API paga → conferidos preços e adotado plano gratuito com resposta simulada de reserva.
3. Squads idênticas entre perfis → regra de exatamente 1 novato na Balanceada e exclusão de conjuntos repetidos.
4. Evolutiva escalava novatos sem horas → penalidade de sobrecarga na busca.
5. Projeto armadilha não mostrava risco ao remover o único back-end → pesos de papel crítico no risco e ajuste dos dados.
7. O resultado das squads aparecia abaixo da tela e parecia que o clique não funcionava → a página passou a rolar até ele.
8. O primeiro grafo de mentoria em círculo deixava setas curtas e rótulos sobrepostos → refeito em duas colunas (mentores e mentorados).
9. O radar de cobertura saía idêntico nas 3 squads (só mostrava se o mínimo era atingido) → passou a mostrar o nível real de cada pessoa contra o exigido. Erro apontado pelo Benja.
6. Substitutos sem nenhum nível na habilidade eram sugeridos → filtro de nível mínimo 1.

## Testes
34 testes (`test_scenarios.py`, `test_api.py`, `test_ai.py`), todos passando, sem internet e sem chave de IA.
