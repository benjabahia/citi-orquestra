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
| Ter | Entrevista com IA na aba Membro e checagem de coerência do perfil | Módulo `ai/interview.py`, 3 endpoints, tela `Interview.tsx` e 44 testes novos | Aguardando revisão do Benja |

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

## Entrevista com IA: como a regra "a IA propõe, a pessoa confirma" foi mantida
- A IA faz de 1 a 3 perguntas e propõe um rascunho de níveis; o nível que vale é o que a pessoa escolhe na tela de revisão.
- Toda saída da IA passa por validação estrita (habilidade existe, nível inteiro de 0 a 4, evidência com até 160 caracteres); se algo vier errado, o rascunho inteiro é recusado e a tela volta ao formulário.
- O texto da pessoa vai para a IA como dado (dentro de um JSON) e o prompt manda ignorar ordens escritas nele. O nome da pessoa não é enviado.
- Os avisos "Vale revisar" são decididos só por regras em Python (nível 4 em 3+ áreas; nível 3 ou 4 sem evidência no texto; novato com nível alto sem entrega real). Não bloqueiam o salvamento.
- Limitação conhecida: a busca de evidência é por palavras-chave e não entende negação ("nunca fiz projeto real" conta como entrega real).

## Testes
124 testes (`test_scenarios.py`, `test_api.py`, `test_ai.py`, `test_recommend.py`, `test_stress.py`, `test_members_csv.py`, `test_interview.py`), todos passando, sem internet e sem chave de IA (nos testes da entrevista a resposta da IA é simulada).
