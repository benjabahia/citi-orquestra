<p align="center">
  <img src="assets/logo.png" alt="Logo CITi Orquestra" width="260">
</p>

<h1 align="center">CITi Orquestra</h1>

<p align="center"><b>Monte o squad certo e veja o impacto antes de decidir.</b></p>

Ferramenta interna do CITi que monta **3 squads por projeto** (Seguro, Evolutivo e Balanceado) a partir das habilidades e da disponibilidade dos membros, recomenda um deles conforme a prioridade do gerente e mostra o impacto de cada decisão (trocar uma pessoa, alguém sair) **antes** de ela ser tomada.

**Site no ar:** https://citi-orquestra.onrender.com
**Vídeo de apresentação:** (link do YouTube a preencher)
**Diário de uso de IA:** [AI_LOG.md](AI_LOG.md)

---

## Índice

1. [O problema e a ideia](#o-problema-e-a-ideia)
2. [Funcionalidades](#funcionalidades)
3. [Como a IA é usada](#como-a-ia-é-usada)
4. [Como funciona por dentro](#como-funciona-por-dentro)
5. [Tecnologia](#tecnologia)
6. [Rodar no seu computador](#rodar-no-seu-computador)
7. [Testes](#testes)
8. [Publicação](#publicação)
9. [Estrutura do repositório](#estrutura-do-repositório)
10. [Limites conhecidos](#limites-conhecidos)

---

## O problema e a ideia

Hoje, montar o time de um projeto depende da memória de quem conhece as pessoas. Isso esconde três riscos: uma única pessoa dominando uma habilidade crítica, novatos sem mentor e gente sobrecarregada.

O CITi Orquestra transforma essa decisão em algo visível e comparável. A regra central do projeto:

> **O algoritmo decide; a IA só interpreta e explica.**
> Quem escolhe pessoas, calcula medidores e define níveis é código determinístico e testado. A IA lê texto livre (briefing, entrevista) e **propõe** rascunhos, mas o gerente e o membro sempre revisam e confirmam.

---

## Funcionalidades

| # | Funcionalidade | Em uma frase |
|---|---|---|
| 1 | [3 squads por projeto](#1-três-squads-por-projeto) | Seguro, Evolutivo e Balanceado, sempre diferentes entre si |
| 2 | [Medidores](#2-medidores-entrega-crescimento-e-risco) | Entrega, Crescimento e Risco de 0 a 100, com cada fator explicado |
| 3 | [Mentoria](#3-mentoria) | Novatos só entram com mentor, com regras claras de carga |
| 4 | [Detalhes e gráficos](#4-detalhes-da-squad-e-gráficos) | Radar de nível real × exigido, grafo de mentoria, barras de carga |
| 5 | [Trocar uma pessoa](#5-trocar-uma-pessoa-simulação) | Substitutos ordenados por impacto, com variação em tempo real |
| 6 | [Recomendação por prioridade](#6-recomendação-por-prioridade) | "Prazo apertado", "Formar gente" ou "Equilíbrio" destacam um squad |
| 7 | [Teste de estresse](#7-teste-de-estresse-e-se-alguém-sair) | Mostra quem é o ponto mais frágil do squad |
| 8 | [Briefing com IA](#8-briefing-com-ia) | Cole o texto do cliente e receba papéis, duração e um nome sugerido |
| 9 | [Perfil do membro](#9-perfil-do-membro-formulário-e-entrevista-com-ia) | Formulário guiado ou entrevista com IA, com checagem de coerência |
| 10 | [Importar planilha](#10-importar-planilha-de-membros) | Use os membros reais do seu time em vez dos dados de exemplo |
| 11 | [Projetos prontos](#11-projetos-prontos-e-o-projeto-armadilha) | 6 exemplos, incluindo um "armadilha" que mostra o risco aparecendo |
| 12 | [IA real ou simulada](#12-ia-real-ou-simulada-sempre-visível) | O modo ativo aparece na tela; sem IA, tudo continua funcionando |
| 13 | [Disponibilidade real de horas](#13-disponibilidade-real-de-horas) | Horas livres declaradas pelos membros, ajustáveis pelo gerente e comparadas com as exigidas |
| 14 | [Exportar o resultado](#14-exportar-o-resultado) | PDF do squad e resumo curto para colar no WhatsApp ou no Slack |

### 1. Três squads por projeto

Para cada projeto o sistema monta três opções, comparadas lado a lado numa tabela:

| Tipo | Ideia | Regra sobre novatos |
|---|---|---|
| **Seguro** | Maior entrega e menor risco | Nenhum novato |
| **Balanceado** | Meio-termo entre entrega e crescimento | Exatamente 1 novato, com mentor |
| **Evolutivo** | Maior crescimento, aposta em quem está aprendendo | Pelo menos 2 novatos (ou metade dos papéis, se for maior), todos com mentor |

Os três têm conjuntos de pessoas diferentes, e a escada é garantida por testes: a **entrega** cai de Seguro para Evolutivo e o **crescimento** sobe, sem empate entre os tipos.

### 2. Medidores: Entrega, Crescimento e Risco

- **Entrega (0–100):** cobertura das habilidades exigidas x folga de horas. Quem aprende com mentor ainda rende menos que um veterano (a ajuda vale meio nível), e cada pessoa mentorada custa 2 pontos pelo tempo do mentor.
- **Crescimento (0–100):** quanto o squad atende às metas de aprendizado e dá apoio de mentor.
- **Risco (0–100):** soma de penalidades, cada uma explicada em português: papel sem ninguém, pessoa abaixo do nível exigido, sobrecarga de horas, novato sem mentor e **ponto único de falha** em papel crítico.

Cada número vem com a lista de fatores que o formaram, para responder "de onde veio isso?".

### 3. Mentoria

- Precisa de mentor quem é **novato** (menos de 6 meses no CITi) ou está **2 ou mais níveis abaixo** do exigido.
- O mentor tem nível 3 ou mais na **mesma habilidade**, está no mesmo squad e atende no máximo 2 pessoas (2 h por semana cada).
- Papéis críticos pesam 1,5x em lacuna e em nível abaixo do exigido.
- Tudo é configurável em `backend/app/config.py`.

### 4. Detalhes do squad e gráficos

Ao clicar em **Ver detalhes**, a tela mostra:

- **Radar** com o nível real de cada pessoa contra o nível exigido pelo projeto (diferente em cada squad).
- **Grafo de mentoria** em duas colunas (mentores e mentorados).
- **Barras de carga** de horas por pessoa.
- Lista de alertas em linguagem simples, recolhível.

### 5. Trocar uma pessoa (simulação)

Para qualquer papel, o botão **Trocar** lista os substitutos ordenados por impacto, com a variação de Entrega, Crescimento e Risco antes de decidir. O sistema avisa dos problemas, mas **não bloqueia** a decisão. **Aplicar** confirma a troca e recalcula tudo, com animação dos números.

### 6. Recomendação por prioridade

Três botões acima da tabela: **Prazo apertado**, **Formar gente** e **Equilíbrio**. Ao clicar, um dos três squads ganha o selo **Recomendado**, com uma frase que cita os números reais (por exemplo, "Maior entrega (100) e risco 0").

- Regra em Python, sem IA: cada prioridade pesa os medidores de um jeito.
- Em "Prazo apertado" há uma **trava de risco**: nunca recomenda um squad com risco muito acima dos outros (limite ajustável em `config.py`).
- A frase é gerada por texto-modelo a partir dos números, e o desempate é estável.
- Funciona também em projetos criados por briefing.

### 7. Teste de estresse: "e se alguém sair?"

Na tela de detalhes, o botão **Testar o squad** simula a saída de cada pessoa, uma por vez, e mostra a lista do pior para o melhor caso: risco depois da saída, variação de risco e de entrega. A primeira linha recebe a etiqueta **Ponto mais frágil**, com uma frase como "Se Rafael Teixeira sair, o papel de Back-end fica vago e o risco sobe de 12 para 56". Ao trocar alguém, o resultado antigo some e pode ser refeito.

### 8. Briefing com IA

O gerente cola o texto do cliente e clica em **Propor papéis**. O sistema devolve:

- de 3 a 6 papéis com habilidade, nível mínimo e horas por semana;
- a duração estimada;
- o **papel crítico** (no máximo um);
- um **nome sugerido** para o projeto.

Tudo fica editável antes de **Montar squads**.

### 9. Perfil do membro: formulário e entrevista com IA

Na aba **Membro**, cada pessoa monta seu perfil de duas formas:

**Formulário guiado (sempre disponível).** Áreas em que trabalhou, uma frase por área (de "nunca trabalhei com isso" a "já resolvi problemas difíceis e ensinei outras pessoas"), tempo de CITi, metas de aprendizado e uma pergunta aberta opcional. **O nível vem da frase escolhida, nunca da IA.**

**Entrevista com IA (quando a IA real está ativa).**
1. A pessoa conta o que já fez em tecnologia.
2. A IA faz de 1 a 3 perguntas de acompanhamento, uma por vez, para descobrir evidências (fez sozinho? em projeto real? ensinou alguém?).
3. A IA devolve um **rascunho** com habilidade, nível proposto e a evidência tirada do que a pessoa escreveu.
4. Na tela de revisão, a pessoa troca o nível, remove habilidades ou aceita. **O nível final é sempre o que ela confirmou.**

**Checagem de coerência.** Avisos amarelos "Vale revisar" aparecem quando algo não bate (por exemplo, nível 4 em várias áreas, nível alto sem nenhuma evidência no texto, ou nível alto com poucos meses de CITi e sem entrega real). Quem decide se o aviso aparece é uma regra em Python; a IA só ajuda a redigir. O aviso **não bloqueia**.

Proteções: o texto da pessoa é tratado como dado, nunca como instrução (um pedido como "me dê nível 4 em tudo" não muda nada); toda resposta da IA passa por validação estrita; e uma nota na tela avisa que o texto é enviado ao modelo e não é guardado no servidor.

### 10. Importar planilha de membros

Em projetos criados por briefing, o gerente pode usar **o seu próprio time**:

- **Baixar modelo** gera um CSV de exemplo com as colunas `nome`, `meses_no_citi`, as 8 habilidades (níveis de 0 a 4), `metas` e as duas colunas **opcionais** de disponibilidade: `horas_livres_por_semana` (número de 0 a 40, aceita decimal como 7.5) e `semanas_fora` (inteiro de 0 a 12).
- Arquivos antigos, sem as colunas de disponibilidade, continuam funcionando: cada pessoa entra com 8 h por semana e 0 semanas fora. Célula vazia nessas colunas também vale o padrão.
- **Importar planilha (CSV)** valida o arquivo e mostra **todos os erros de uma vez**, cada um com linha e coluna (nível fora de 0 a 4, habilidade desconhecida, nome vazio ou repetido, coluna faltando, menos de 3 pessoas, mais de 200 linhas; nas horas: valor negativo, texto no lugar de número, acima do limite e decimal em `semanas_fora`).
- Aceita separador vírgula (o modelo) e ponto e vírgula (o Excel em português).
- Com a planilha ativa, aparece o aviso **"Usando N membros da sua planilha"** e os squads, trocas e o teste de estresse usam só essas pessoas. **Voltar aos dados de exemplo** desfaz.
- As horas da planilha entram no cálculo (ver [funcionalidade 13](#13-disponibilidade-real-de-horas)).
- **Privacidade:** a planilha fica só no navegador (localStorage). Vai junto no pedido para o cálculo, mas nada é gravado no servidor.

Os projetos prontos continuam usando os dados de exemplo.

### 11. Projetos prontos e o projeto "armadilha"

Seis projetos de exemplo (clínica, loja virtual, painel de indicadores, logística, site institucional e pagamentos), com 24 membros fictícios.

O de **pagamentos** é uma armadilha de propósito: só uma pessoa domina back-end. Remover essa pessoa (na troca ou no teste de estresse) faz o risco disparar, e a ferramenta mostra isso com clareza.

### 12. IA real ou simulada, sempre visível

Um selo no topo mostra se a IA está **ativa** ou em **modo simulado**. Sem chave de IA, o briefing e o perfil usam regras simples (palavras-chave), a entrevista dá lugar ao formulário, e todo o resto (squads, medidores, mentoria, trocas, recomendação, teste de estresse) funciona igual, porque nada disso depende da IA. Se a IA falhar ou demorar mais de 15 segundos, o sistema volta sozinho ao modo simulado, sem quebrar.

### 13. Disponibilidade real de horas

Em projetos criados por briefing, as horas livres de cada pessoa vêm do que foi **informado**, e não de um valor inventado pelo código.

**De onde vêm as horas (a última vence):**
1. **Perfil do membro:** o formulário e o último passo da entrevista com IA perguntam "Quantas horas por semana você consegue dedicar a projetos neste ciclo?" (0 a 40, com atalhos 2, 4, 6, 8, 10 e 12) e "Em quantas semanas dos próximos projetos você estará fora?" (inteiro de 0 a 12). Os valores ficam salvos no perfil (`weekly_hours` e `unavailable_weeks`). Perfis antigos, sem esses campos, continuam válidos com 8 h e 0 semanas.
2. **Planilha:** as colunas opcionais `horas_livres_por_semana` e `semanas_fora` (sem elas, 8 h e 0 semanas).
3. **Ajuste do gerente:** no passo "2. Confira os papéis", a seção recolhível **Ajustar disponibilidade da equipe** lista cada pessoa em jogo, já preenchida com o que veio da planilha ou do perfil, e permite mudar as horas e as semanas fora. Os ajustes valem ao montar os squads.

**Regras do cálculo:**
- Horas livres no projeto = horas por semana × (semanas do projeto − semanas fora) ÷ semanas do projeto. Exemplo: 8 h num projeto de 2 semanas, com 1 semana fora, dá 4 h (50%).
- Horas exigidas = horas do papel + 2 h por semana para cada pessoa que ela mentora.
- Quando as exigidas passam das livres, a pessoa conta como **sobrecarregada** no risco, como antes.
- A disponibilidade viaja junto com o projeto em todos os pedidos (trocar, aplicar troca e teste de estresse), então os números são iguais em todas as telas.
- Sem planilha, os 24 membros de exemplo continuam com as horas de exemplo (fictícias), mas o gerente também pode ajustá-las.
- **Os 6 projetos prontos não mudam:** continuam com as horas simuladas, e a tela mostra "Horas de exemplo (fictícias)". Um teste compara o resultado deles com uma cópia salva antes desta mudança.

**Na tela:**
- Ao lado do campo **Duração (semanas)**, atalhos de 2, 4, 6, 8 e 12 semanas (o campo continua editável).
- Na tabela comparativa e na tela de detalhes, cada pessoa mostra "4 h livres · 6 h exigidas". Quando faltam horas, aparece uma etiqueta vermelha suave "faltam 2 h", e o cartão do squad mostra um resumo como "2 pessoas sem horas suficientes".
- Texto fixo: "Disponibilidade declarada pelos membros; o sistema não verifica as horas."

### 14. Exportar o resultado

Duas formas de levar o squad para fora da ferramenta. As duas mostram o estado **atual** do squad, inclusive as trocas já aplicadas.

**PDF do squad.** O botão **Baixar PDF** aparece na tela de detalhes e também em cada cartão da tabela comparativa. Ele abre a caixa de impressão do navegador: escolha **Salvar como PDF**. Não usa biblioteca nova: é uma visão de relatório própria, em página A4, com fundo branco e texto escuro (mesmo com o site no tema escuro), e as barras e cores saem no arquivo. Conteúdo, nesta ordem:
1. cabeçalho com a logo, o nome do projeto, o tipo do squad, a duração em semanas e a data de hoje;
2. os três medidores (Entrega, Crescimento e Risco);
3. mini-tabela comparando os três squads, com o atual destacado e o selo **Recomendado** (com a prioridade escolhida, como "Prazo apertado") quando a pessoa tiver clicado numa prioridade;
4. tabela de pessoas: papel, pessoa, nível e "X h livres · Y h exigidas", com a marca "faltam X h" quando falta tempo;
5. mentorias (quem ensina quem, em qual habilidade);
6. alertas de risco;
7. rodapé: "Disponibilidade declarada pelos membros; o sistema não verifica as horas" (projetos por briefing) ou "Dados e horas de exemplo (fictícios)" (projetos prontos).

Menu, botões e tudo que não é relatório ficam de fora, e as linhas de tabela não são cortadas no meio da página.

**Resumo para colar no chat.** O botão **Copiar resumo** (tela de detalhes) copia um texto curto, legível no WhatsApp e no Slack: projeto, tipo do squad, os três medidores, a lista "Papel: Pessoa (nível, X h livres · Y h exigidas)", as mentorias, o **ponto mais frágil** (só se o teste de estresse já tiver sido feito) e o aviso de disponibilidade. Aparece "Resumo copiado" por 3 segundos; se o navegador bloquear a área de transferência, a tela explica o problema e mostra o texto para copiar à mão.

O texto é montado no servidor, por uma função Python pura (`backend/app/summary.py`, endpoint `POST /api/export/summary`, que recebe o mesmo corpo do teste de estresse mais o id do projeto), então é idêntico em projetos prontos e em projetos por briefing, e é testado sem navegador. Sem IA: os números vêm dos mesmos medidores da tela.

---

## Como a IA é usada

| Onde | O que a IA faz | O que ela **não** faz |
|---|---|---|
| Briefing | Propõe papéis, níveis exigidos, horas, papel crítico e nome do projeto | Não escolhe pessoas |
| Entrevista de perfil | Faz perguntas de acompanhamento e propõe um rascunho com evidências | Não define o nível final: a pessoa confirma |
| Checagem de coerência | Ajuda a redigir o aviso | Não decide se o aviso aparece (regra em Python) |
| Pergunta aberta do formulário | Sugere habilidades que a pessoa não marcou | Não define nível |

Toda saída da IA é validada (habilidades existentes, formato, limites). Se for inválida, o sistema usa o modo simulado ou o formulário.

| | **IA real (Groq)** | **Simulado (padrão sem chave)** |
|---|---|---|
| Quando ativa | Há `GROQ_API_KEY` e o modelo respondeu em até 15 s | Sem chave, ou com erro, timeout ou resposta inválida |
| Briefing | Interpreta texto livre e variado | Regras por palavras-chave |
| Perfil do membro | Entrevista adaptativa com rascunho | Formulário guiado |
| Squads, medidores, mentoria, trocas, recomendação, teste de estresse | Idênticos | Idênticos (não dependem da IA) |

O uso de IA **no desenvolvimento** (Claude, onde errou e como foi corrigido) está em [AI_LOG.md](AI_LOG.md).

---

## Como funciona por dentro

1. Cada tipo de squad tem uma "nota" própria que pesa entrega, crescimento e risco de um jeito diferente.
2. A busca parte de vários squads iniciais e vai trocando pessoas enquanto a nota melhora (**subida de encosta**, ou hill climbing), respeitando as regras duras de cada tipo (quantidade de novatos, horas, mentor obrigatório).
3. Os três squads precisam ser diferentes; para Evolutivo e Balanceado o algoritmo tenta as duas ordens de construção e fica com a de maior nota total.
4. O resultado é **determinístico**: mesma entrada, mesmos squads.
5. A recomendação, o teste de estresse e a checagem de coerência também são funções puras em Python, testadas sem IA.

---

## Tecnologia

- **Back-end:** Python 3.12, FastAPI, Pydantic.
- **Front-end:** React 18, TypeScript, Vite. Gráficos em SVG escritos à mão, sem biblioteca de gráficos.
- **IA:** Groq (modelo `openai/gpt-oss-120b`) por HTTP, com reserva automática para o modo simulado.
- **Entrega:** um único serviço no Render (plano gratuito). O FastAPI serve a API e o site construído (`frontend/dist`) no mesmo endereço. Um monitor externo mantém o site acordado.
- **Dados:** 24 membros e 6 projetos sintéticos (nenhum dado real do CITi).

---

## Rodar no seu computador

**Site completo** (o front-end já vem construído em `frontend/dist`):

```
cd backend
pip install -r requirements.txt
python -m uvicorn app.api:app --port 8000
```

Abra http://127.0.0.1:8000. Documentação interativa da API: http://127.0.0.1:8000/docs.

**Alterar o front-end:**

```
cd frontend
npm install
npm run build
```

**IA real (opcional):** crie `backend/.env` (arquivo ignorado pelo Git) com a linha `GROQ_API_KEY=sua_chave`. Sem isso, o site funciona em modo simulado.

**Demonstração no terminal** (a partir da pasta principal, não de dentro de `backend`): `python scripts/demo_cli.py pagamentos`.

---

## Testes

**186 testes automatizados**, todos passando, que rodam sem internet e sem chave de IA:

```
cd backend
pip install -r requirements.txt
python -m pytest -q
```

| Grupo | O que garante |
|---|---|
| Regras de alocação | medidores entre 0 e 100; 3 squads sempre diferentes; regras de novatos por tipo; escada Seguro > Balanceado > Evolutivo; regras de mentoria; projeto armadilha dispara o risco; falta de gente vira lacuna, não erro; trocas coerentes; resultado determinístico |
| API | rotas principais, erros 404 e 422 claros, site servido pelo mesmo servidor |
| IA e projetos novos | briefing simulado e real validados; resposta ruim da IA cai no simulado; nível só das frases-âncora; entrevista com limites e proteção contra texto malicioso; checagem de coerência; projeto novo monta 3 squads e aceita trocas |
| Recomendação | recomendação esperada nos 6 projetos para cada prioridade; números citados corretos; empate; trava de risco |
| Teste de estresse | pessoa única de habilidade crítica aparece como mais frágil; cobre todos os membros; funciona em projeto por briefing |
| Importar planilha | arquivo válido; cada tipo de erro (nível, nome repetido ou vazio, habilidade, poucos membros, limite de linhas); projetos prontos não mudam |
| Exportar resultado | resumo com todos os papéis e pessoas; números iguais aos medidores; marca de falta de horas; horas livres e exigidas; mentorias; ponto mais frágil só com o teste de estresse; vaga em aberto; estado atual depois de uma troca; projeto pronto e projeto por briefing com planilha; pedido inválido devolve 422 |
| Disponibilidade de horas | perfil com e sem os campos novos; CSV com e sem as colunas novas e cada erro de horas (negativo, texto, acima do limite, decimal em semanas); horas informadas entram no cálculo; sobrecarga quando faltam horas; ajuste do gerente; troca, aplicar troca e teste de estresse com as mesmas horas; 2 semanas com 1 fora = 50%; os 6 projetos prontos idênticos aos de antes |

Além dos testes automáticos, o site foi percorrido de ponta a ponta no navegador a cada mudança visual.

---

## Publicação

O site é publicado no **Render** (plano gratuito), com atualização automática a cada envio para a ramificação `main`.

- Build: `pip install -r backend/requirements.txt`
- Start: `cd backend && python -m uvicorn app.api:app --host 0.0.0.0 --port $PORT`
- Verificação de saúde: `/api/health` (aceita GET e HEAD)
- A chave da IA fica só em variável de ambiente no servidor (`GROQ_API_KEY`), nunca no repositório.
- Um monitor externo consulta `/api/health` a cada 5 minutos para o site não "dormir".

---

## Estrutura do repositório

```
backend/
  app/
    config.py          regras e pesos ajustáveis
    models.py          dados do domínio
    scoring.py         medidores e mentoria
    allocator.py       montagem dos 3 squads
    whatif.py          trocas e remoções
    recommend.py       recomendação por prioridade
    stress.py          teste de estresse
    summary.py         resumo do squad para colar no chat
    members_csv.py     leitura e validação da planilha (inclui as horas)
    data.py            membros e projetos de exemplo
    api.py             endpoints FastAPI
    ai/                briefing, entrevista, perfil e adaptador do Groq
  tests/               testes automatizados
    dados/             CSVs de teste e a cópia do resultado dos 6 projetos prontos
frontend/
  src/                 telas e componentes React
  dist/                site construído, servido pela API
scripts/               demonstração no terminal (demo_cli.py)
assets/                logo
AI_LOG.md              diário de uso de IA no desenvolvimento
```

---

## Limites conhecidos

**Limites**
- Os 24 membros e 6 projetos de exemplo são fictícios.
- A planilha importada vale só para projetos criados por briefing.
- A planilha e o perfil agora trazem as horas livres, mas elas são **declaradas** pela pessoa (ou ajustadas pelo gerente) e o sistema **não verifica** se são reais. Quem não informa entra com 8 h por semana.
- O perfil do membro fica só no navegador (localStorage).
- "Balanceado com exatamente 1 novato", "Evolutivo com pelo menos 2" e o peso 1,5 dos papéis críticos são **escolhas de produto**, ajustáveis em `config.py`.
- No plano gratuito, o primeiro acesso após muito tempo parado pode levar cerca de 1 minuto; o monitor reduz isso.
- O visual usa a fonte Inter Tight como substituta, e a logo é própria do projeto.
