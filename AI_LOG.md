# Diário de uso de IA no desenvolvimento

Como a IA foi usada para construir o CITi Orquestra: o que ela propôs, o que eu aceitei, corrigi ou recusei, e onde ela errou.

> Texto em primeira pessoa, escrito a partir do que aconteceu em cada dia. Sujeito à minha revisão final antes da entrega.

## Ferramentas

- **Claude (Anthropic), no aplicativo Claude:** conversa de planejamento, escrita e revisão do código, testes, capturas de tela do site e implantação.
- **Claude Code, no terminal do VS Code:** usado nos recursos da terça (recomendação por prioridade, teste de estresse, importar planilha e entrevista com IA), com os pedidos que eu escrevi a partir de decisões minhas.
- **Groq (modelo `openai/gpt-oss-120b`):** IA **dentro do produto** (briefing e entrevista de perfil), com reserva simulada quando não está disponível.

**Divisão de papéis:** eu defini o problema, as regras de produto e as prioridades, testei o site no navegador e apontei erros. A IA escreveu o código e eu o revisei. Sei Python, mas não TypeScript, então peço explicações simples e confiro o resultado no uso.

## Linha do tempo

| Dia | Objetivo | O que a IA propôs | Aceito / corrigido / recusado |
|---|---|---|---|
| Dom 15/11 | Escolher a ideia e fechar decisões de produto | Brainstorming de ideias e uma entrevista de 31 perguntas | Escolhi o CITi Orquestra e aceitei ou ajustei cada decisão |
| Dom 15/11 | Núcleo em Python: dados, pontuação, alocação, trocas | Código inicial e testes | Corrigido várias vezes (ver erros abaixo) |
| Dom 15/11 | API FastAPI (projetos, squads, substitutos, aplicar troca) | Endpoints e 5 testes | Aceito após revisão |
| Seg 16/11 | Adaptador do Groq com reserva simulada, leitura de briefing, chat de perfil, tela React | Código e 15 testes novos | Aceito após revisão; verificado por captura de tela e fluxo completo no navegador |
| Seg 16/11 | Visual sóbrio, tabela comparativa, tela de detalhes (radar, carga, grafo de mentoria) e troca com animação | Código, SVG próprio e testes | Aceito após revisão visual; grafo de mentoria refeito |
| Seg 16/11 | Redesenho no estilo do site do CITi (fundo escuro, verde, botões em pílula) e radar de nível real × exigido | CSS e componentes | Pedi o redesenho com citi.org.br como referência e apontei que o radar saía igual nas 3 squads; ambos corrigidos |
| Seg 16/11 | Publicação no Render e monitor de disponibilidade | Configuração do serviço e passo a passo | Aceito; o monitor acusou erro e foi corrigido (ver erro 10) |
| Ter 17/11 | IA sugere o nome do projeto a partir do briefing | Mudança pequena em back-end e front-end | Aceito |
| Ter 17/11 | Logo própria no menu, na aba do navegador e no README | Recortes e tamanhos a partir da minha arte | Recusei duas decisões da IA (ver erros 13 e 14) |
| Ter 17/11 | Escada clara entre Segura, Balanceada e Evolutiva | Nova conta de entrega, regra de novatos e pesos | Apontei o defeito; aceito após ver os 6 projetos e 3 testes novos |
| Ter 17/11 | Recomendação por prioridade | Regra em Python, frases-modelo, botões e selo (Claude Code) | Testei no navegador e aprovei |
| Ter 17/11 | Teste de estresse "e se alguém sair?" | Endpoint, tabela e frase do ponto mais frágil (Claude Code) | Testei e aprovei |
| Ter 17/11 | Importar planilha de membros em CSV | Leitura, validação com linha e coluna, tela de importação (Claude Code) | Pedi arquivos de teste (um válido e um com erros de propósito) e aprovei |
| Ter 17/11 | Entrevista com IA e checagem de coerência no perfil do membro | Entrevista adaptativa, rascunho com evidências, regras de coerência (Claude Code) | Testei com texto exagerado e apontei problemas (ver erro 15); corrigido e aprovado |
| Ter 17/11 | Disponibilidade real de horas (Claude Code) | Horas no perfil e na planilha, ajuste do gerente, "h livres · h exigidas" nas telas, 29 testes novos e uma cópia do resultado dos projetos prontos para provar que não mudaram | Defini as regras e os testes; a revisar no navegador |
| Ter 17/11 | Exportar PDF e resumo (Claude Code) | Botão "Baixar PDF" com relatório A4 próprio para impressão, botão "Copiar resumo" e texto montado no servidor (`summary.py`), 17 testes novos | A revisar no navegador (impressão em PDF) |

## Onde a IA errou e como foi corrigido

1. **Stack inadequada.** Sugeriu TypeScript e Next.js sem considerar que eu precisava revisar o código. Trocado por Python e FastAPI.
2. **Custo.** Assumiu API paga. Conferidos os preços e adotado plano gratuito, com resposta simulada de reserva.
3. **Squads idênticas** entre perfis. Criada a regra de exatamente 1 novato na Balanceada e a exclusão de conjuntos repetidos.
4. **Evolutiva sobrecarregava novatos.** Entrou uma penalidade de sobrecarga na busca.
5. **O projeto armadilha não mostrava risco** ao remover o único back-end. Entraram pesos de papel crítico e ajuste dos dados.
6. **Substitutos sem nenhum nível** na habilidade eram sugeridos. Criado o filtro de nível mínimo 1.
7. **Resultado abaixo da tela.** O site parecia travado, porque o resultado das squads aparecia fora da área visível. A página agora rola até ele e mostra um texto de carregamento.
8. **Grafo de mentoria em círculo**, com setas curtas e rótulos sobrepostos. Refeito em duas colunas (mentores e mentorados).
9. **Radar de cobertura idêntico nas 3 squads.** Só mostrava se o mínimo era atingido. Passou a mostrar o nível real de cada pessoa contra o exigido. *Erro que eu apontei ao testar.*
10. **Monitor de disponibilidade acusava "404".** O endereço de saúde só aceitava o método GET, e o monitor usa HEAD. Passou a aceitar os dois.
11. **Entrega "estourava" em 100 e Evolutiva igual à Balanceada.** Um novato com mentor contava como se já tivesse o nível exigido, e as duas squads tinham o mesmo número de novatos. Mentoria passou a valer meio nível na entrega e a custar tempo do mentor; a Evolutiva ganhou pelo menos 2 novatos. *Erro que eu apontei ao testar a Clínica.*
12. **Balanceada pior que a Evolutiva** no projeto do Painel de Indicadores, achado durante a investigação do erro 11. Pesos dos tipos de squad ajustados e um teste novo garante a escada em todos os projetos.
13. **A IA simplificou minha logo sem eu pedir.** Trocou o meu desenho por uma forma sólida, porque as linhas finas se misturavam em tamanho pequeno. Eu tinha pedido para usar a minha arte. Refeito com o desenho original, só recortado.
14. **Logo no rodapé.** Ela foi colocada lá por iniciativa da IA e eu não gostei. Removida: a logo ficou só no menu, na aba do navegador e no README.
15. **Entrevista com IA com perguntas genéricas e erro enganoso.** Ao testar com "sou expert em tudo", a IA repetiu três vezes uma pergunta vaga e a tela mostrou "fora do formato esperado", que parecia falha técnica. Pedi a correção: mensagens distintas para "resposta inválida" e "sem evidência", perguntas que citam o que a pessoa disse, e aviso de coerência para afirmações amplas sem exemplo.

## O que eu mantive sob controle

- **A IA nunca decide as squads nem os níveis.** Squads, medidores, mentoria, trocas, recomendação e teste de estresse são código determinístico e testado. A IA só interpreta texto e propõe rascunhos que a pessoa confirma.
- **Toda saída da IA é validada** (habilidades existentes, níveis de 0 a 4, tamanhos máximos) e o texto do usuário é tratado como dado, não como instrução.
- **Há reserva simulada.** Sem chave ou com falha, o produto continua funcionando e o modo ativo aparece na tela.
- **A chave da IA nunca foi para o repositório:** fica só em variável de ambiente no servidor e em um arquivo local ignorado pelo Git.
- **Dados fictícios.** Nenhum dado real de membros do CITi foi usado.

## Testes

186 testes automatizados (`backend/tests/`), todos passando, sem internet e sem chave de IA. Cobrem regras de alocação, API, IA (com respostas falsas), recomendação, teste de estresse, importação de planilha, entrevista com IA, disponibilidade de horas e exportação do resumo. Os detalhes por grupo estão no [README](README.md#testes).
