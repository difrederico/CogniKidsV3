# Roadmap Histórico e Contexto de Projeto — CogniKids

> Arquivo de referência detalhada. Extraído do `CLAUDE.md` raiz na
> refatoração de eficiência de tokens. Consultar sob demanda para histórico de
> sprint, métricas de experimento passado, ou contexto de equipe/apresentação.

---

## Equipe e contexto

O CogniKids é uma plataforma educacional e terapêutica para crianças
neurodivergentes (TEA, TDAH, Dislexia) que conecta Professor, Pais e Aluno
em torno de dados reais de comportamento e aprendizagem.

**Equipe:**
- Frederico Lemes Rosa — responsável técnico (AI Analyst, NIAA/SENAI FATESG)
- Maria Clara Ribeiro Di Bragança — apresentará o projeto do 3º período (nov/dez 2026);
  está aprendendo Mineração de Dados agora — **todo notebook de mineração deste
  projeto segue CRISP-DM explicitamente** (mesmas 6 fases do notebook core em
  `docs/data-science/Apresentacao_CRISP-DM.md`), com markdown que define cada
  termo técnico (correlação, acurácia, TF-IDF, overfitting, etc.) antes de
  usá-lo. **Tom formal/acadêmico, não tutorial de iniciante** — os notebooks são
  também material que passa por avaliação de banca/professores: terceira
  pessoa/impessoal, sem coloquialismo ("chute", "cego", etc.), decisões técnicas
  justificadas por critério técnico (reprodutibilidade, auditabilidade,
  explicabilidade), nunca por "preferência do time". Ver
  `cognikids-adapt/notebooks/nucleo1_text_mining.ipynb` como referência de padrão.

**Datas:** Criado em Agosto de 2026. Apresentação prevista para
Novembro/Dezembro de 2026. Repositório: CogniKids (monorepo) —
`cognikids-backend/` (core, em manutenção ativa) + `cognikids-adapt/`
(satélite), dois microserviços independentes.

---

## Plano original do satélite (histórico de planejamento)

Registro do planejamento original do Motor de Adaptação Curricular, como
concebido antes da implementação (útil para entender a intenção por trás da
arquitetura atual — o estado real de cada etapa está no roadmap de sprints
abaixo, não aqui):

```
Professor insere atividade (texto livre ou banco)
→ Gateway FastAPI :8001
→ RabbitMQ
→ Worker de análise: Text Mining (CommonLit + Bloom's Taxonomy)
→ Worker de perfil: lê tokens do core (read-only)
→ Worker de adaptação: LLM gera versão adaptada por criança
→ Professor revisa e aprova
→ Atividade chega no app do aluno no formato ideal
→ Logs de interação → realimentam Data Mining
```

Na concepção original, `cognikids-adapt/` ainda não existia — só o core
(`cognikids-backend/`) estava presente no repositório. Hoje o satélite está
implementado e commitado (ver Sprints 0-3 abaixo); o estado atual do fluxo
(gateway → filas → workers, com o que é real vs. stub) está descrito no
`CLAUDE.md` raiz, seção "Stack e Fluxo Ativo do Satélite".

---

## Roadmap de Sprints

### Sprint 0 — Higiene e estrutura (Ago · sem 1) ✅ CONCLUÍDO
- [x] Criar estrutura de pastas (`cognikids-adapt/{gateway,workers,pipeline,graph,federated,scripts}`)
- [x] docker-compose.yml (gateway + rabbitmq + mongodb satélite) — testado de ponta a ponta, `gateway` responde em `:8001/health`
- [x] .env.example com todas as variáveis documentadas (raiz do repo)
- [x] Script de health check: `cognikids-adapt/scripts/health_check.py` — verifica GET `/api/status` do core
- [x] Teste de contrato: `cognikids-adapt/gateway/tests/test_telemetry_contract.py` — 8 testes, válido aceito e 5 variações inválidas rejeitadas
- [x] Mover API key hardcoded do core para variável de ambiente (ver nota histórica na ADR-010, `docs/architecture/ADRS.md`)

### Sprint 1 — Gateway + Telemetria (Ago–Set) ✅ CONCLUÍDO
- [x] FastAPI gateway: `/v1/curriculum/adapt` + `/v1/telemetry/events` — arquitetura
      em camadas (`api/`, `services/`, `schemas/`, `clients/`, `db/`), testado de
      ponta a ponta via Docker Compose real (não só localmente)
- [x] RabbitMQ: exchange `cognikids` + 4 filas (`analysis`, `profile`, `adaptation`,
      `telemetry` — uma a mais que o planejado, para separar ingestão de telemetria
      do pipeline de adaptação)
- [x] Worker de ingestão (`workers/worker_ingestion.py`): consome fila `telemetry` →
      persiste em `telemetry_events` no MongoDB satélite — confirmado via consulta
      direta no Mongo após publicar evento pelo gateway
- [x] Emulador de carga (`scripts/load_emulator.py`): 100 sessões sequenciais vs.
      100 paralelas, testado de verdade contra o gateway em Docker
- [x] Relatório de stress test (`scripts/relatorio_stress_test.md`): throughput
      9,9x maior em paralelo (159 req/s vs. 16 req/s), mas latência individual
      piora sob carga (60ms → 490ms médio, 1 worker Uvicorn) — **não testado
      ainda com o core rodando simultaneamente**, pendência registrada no relatório

### Sprint 2 — Motor de Adaptação (Set–Out)
- [x] Text Mining: complexidade (CommonLit) + Bloom's Taxonomy + Simpson's Taxonomy (psicomotor) —
      `workers/text_mining_pt.py` (funções portadas do Núcleo 1) +
      `workers/worker_analysis.py` (consome fila `analysis`, publica em `profile`).
      Regressão coberta por `workers/tests/test_text_mining_pt.py`, validado contra os
      mesmos conjuntos de teste rotulados do notebook: **46/46 Bloom's, 22/22 Simpson's,
      sem perda de acurácia na porta**
- [x] Worker de perfil: GET read-only no core + parse dos tokens — `workers/core_client.py`
      (JWT de serviço assinado com `CORE_JWT_SECRET`, GET `/api/accessibility/{aluno_id}`) +
      `workers/worker_profile.py` (consome fila `profile`, publica em `adaptation`).
      Usuário de serviço `tipo='admin'` criado no core via `scripts/criar_admin.py`
      (era `POST /api/register`; a rota pública deixou de aceitar `admin` — ADR-010)
      (`CORE_SERVICE_USER_ID` no `.env` — e-mail `satelite-service@cognikids.internal`,
      só existe para autenticação de máquina, nunca faz login de verdade). Testado com
      token real: `GET /api/accessibility/{aluno_id}` responde `200 OK` (antes era `401`
      sem o usuário). Degradação graciosa (segue sem tokens) também testada e mantida
      como rede de segurança caso o core fique fora do ar
- [x] Grafo de Conhecimento (cold start) em produção — `workers/knowledge_graph.py`
      (funções portadas e validadas contra o notebook Núcleo 2: cold start a partir
      dos tokens de acessibilidade + `atualizar_aresta_grafo()` reproduzindo o mesmo
      resultado do notebook, 0.25 → 0.555 após 3 acertos). Integrado ao
      `worker_profile.py`: persiste o grafo por aluno na coleção `student_graphs`
      do MongoDB satélite, reaproveita o grafo existente em jobs seguintes (não
      recria cold start), publica `knowledge_graph_summary` na fila `adaptation`.
      Testado de ponta a ponta via Docker Compose real (gateway → analysis →
      profile, com persistência e reaproveitamento confirmados no Mongo).
      Regressão coberta por `workers/tests/test_knowledge_graph.py` (5 testes)
- [x] Refinamento do grafo por `TelemetryEvent` de uso real — contrato fechado:
      `concept`/`correct` opcionais adicionados ao `TelemetryEvent`.
      `worker_ingestion.py` agora chama `atualizar_aresta_grafo()` quando o evento
      é `step_completed` avaliável, refinando a aresta aluno-conceito na mesma
      coleção `student_graphs` que `worker_profile.py` lê. Testado de ponta a
      ponta via Docker Compose: 3 eventos reais de acerto levaram o peso de um
      conceito de 0 (cold start) a 0.875, e um job de adaptação seguinte já
      carregou esse valor refinado no `knowledge_graph_summary`. Regressão
      coberta por `workers/tests/test_worker_ingestion_grafo.py` (5 testes, Mongo falso)
- [ ] Worker de adaptação: prompt engineering + LLM + resposta estruturada (Gemma 4 12B
      local via Ollama + fallback Gemini free tier — ADR-002 já decidida; fica para quando
      entrarmos na parte do LLM)
- [ ] Flutter: skeleton + login + tela Professor (inserir atividade)
- [ ] Flutter: tela Aluno (atividade adaptada passo a passo + áudio)

### Sprint 3 — Graph Mining + FL (Out–Nov)
- [x] NetworkX: protótipo do grafo validado em notebook (`nucleo2_grafo_conhecimento.ipynb`)
- [x] NetworkX: cold start do grafo aluno-conceito portado para `worker_profile.py` de
      verdade, persistido no MongoDB satélite (ver Sprint 2) — adiantado do Sprint 3
      original porque é pré-requisito do worker de adaptação
- [x] Contrato de acerto/conceito no `TelemetryEvent` + refinamento contínuo do grafo
      via `worker_ingestion.py` — adiantado do Sprint 3 original (ver Sprint 2)
- [ ] NetworkX: grafo de trilhas em produção (conceitos → recomendação)
- [x] Rede de Cuidado: centralidade + alertas de nós isolados — `workers/rede_cuidado.py`.
      Sem notebook de origem (técnica nova neste projeto). Grafo
      aluno-aluno: aresta quando o padrão de domínio sobre os mesmos conceitos é
      parecido (1 − distância média absoluta sobre conceitos em comum, não correlação
      de Pearson — a base é pequena/esparsa no início do projeto para uma correlação
      ser confiável, diferente do que o Núcleo 2 tinha com o ASSISTments). Centralidade
      de grau/intermediação identifica padrões de dificuldade comuns na turma; nó
      isolado = aluno sem par parecido, candidato a atenção individual (não a
      dificuldade em si — um aluno pode estar isolado por ir bem sozinho em algo raro,
      como no teste abaixo). Testado de ponta a ponta com cenário real via telemetria
      (`scripts/relatorio_rede_cuidado.py`): 2 alunos fortes nos mesmos conceitos
      conectados (similaridade 1.0), 2 alunos fracos nos mesmos conceitos conectados
      entre si (similaridade 1.0, grupo diferente do primeiro), 2 alunos sem par
      corretamente isolados. Regressão coberta por
      `workers/tests/test_rede_cuidado.py` (6 testes, cenário verificado à mão)
- [x] Flower: FedAvg com N escolas simuladas — `cognikids-adapt/federated/`.
      Experimento centralizado vs. federado real: `SGDClassifier` (BPM/GSR/movimento
      → risco de crise) em 4 escolas sintéticas não-IID (10,8% a 39,2% de taxa de
      crise entre escolas — de propósito, pra tornar a comparação federado vs.
      centralizado interessante). Agregação usa `flwr.server.strategy.aggregate.aggregate()`
      de verdade (a mesma função que a estratégia FedAvg do Flower usa por baixo dos
      panos) — rodadas conduzidas manualmente em vez do simulador baseado em Ray do
      Flower (suporte instável no Windows), mas com os componentes reais do
      framework (`NumPyClient`, `aggregate()`), não uma reimplementação própria.
      **Resultado quantificado (satisfaz o critério de aceite abaixo)**:
      federado empatou com centralizado, 0,747 de acurácia nos dois — sem perda ao
      trocar acesso centralizado ao dado por treino distribuído + agregação de
      parâmetros. Relatório completo com metodologia e limitações em
      `federated/relatorio_fl.md`. Regressão coberta por `federated/tests/`
      (8 testes: geração de dados não-IID + parâmetros do modelo)
- [ ] Flutter: tela Pais (histórico + comparativo original/adaptado)

### Sprint 4 — XAI + Pitch (Nov–Dez)
- [x] SHAP cards em linguagem acessível (pais) e técnica (professor) — ver abaixo
- [x] PySpark ETL completo — **sobre ASSISTments 2009, não DSB2019** (Kaggle
      retirou os dados dessa competição e o substituto exige aceitar regras no
      navegador — mesmo obstáculo documentado em `docs/architecture/DATASETS_ETL.md`;
      substituição documentada aqui, não silenciosa). `cognikids-adapt/notebooks/nucleo3_risco_frustracao.ipynb`,
      CRISP-DM completo: 274.331 interações explodidas via `arrays_zip`/`explode`.
      **Engenharia de features em quatro rodadas, cada uma validada por SHAP
      antes de prosseguir** — decisão de aprofundar motivada por duas perguntas
      diretas do time em sequência ("chegamos no melhor cenário possível para
      este dataset?", depois "tem mais engenharia de features que podemos
      usar?"), não planejada desde o início: (1) taxa de acerto **acumulada**
      e **em janela recente** (últimas 5 tentativas); (2) **sequência de erros
      consecutivos** (técnica de agrupamento por *run*, validada manualmente
      linha a linha, inclusive o caso extremo de um aluno cujas primeiras
      interações já são erro), **taxa de acerto por habilidade específica**
      (fallback para a acumulada quando o aluno ainda não tentou aquela
      habilidade — 10,9% dos casos), **tendência** (recente menos acumulada)
      e **tipo de resposta esperado** (`answer_type`, 5 categorias, até então
      ignorado); (3) **volatilidade recente** (desvio padrão do acerto na
      janela), **contagem de tentativas anteriores na mesma habilidade**
      (sinal de confiabilidade da taxa por habilidade), **posição na sessão**
      (resgatada de um esquecimento — já estava disponível desde a primeira
      rodada, prevista até no dicionário de tradução para os cards, mas nunca
      chegou a entrar na lista de features do modelo) e **dificuldade média
      da habilidade entre todos os alunos**, esta última exigindo cuidado
      metodológico extra: por depender da própria variável-alvo, só pode ser
      calculada com estatísticas do conjunto de **treino**, nunca do teste
      (a mesma lógica de um `fit`/`transform` de codificador do scikit-learn,
      feita manualmente), com valor de reserva para habilidades do teste sem
      correspondência no treino (não ocorreu na prática, mas o código está
      preparado). Todas as features de janela sem vazamento de dado, garantido
      pela própria definição da janela, não por checagem manual
- [x] XGBoost treinado + validação estratificada e **agrupada por aluno**
      (`StratifiedGroupKFold` — nenhum `user_id` aparece ao mesmo tempo em
      treino e teste, correção de uma falha metodológica real encontrada
      depois da primeira rodada: o split original era só por linha/interação,
      o que permitia o modelo "reconhecer" alunos já vistos no treino em vez
      de generalizar) — comparado contra linha de base (classe majoritária)
      por exigência metodológica (mesmo critério da ADR-006/comparação de
      classificadores do Núcleo 1). **Resultado real, sem maquiagem, progressão
      medida nas quatro rodadas**: acurácia em validação cruzada de 5 dobras
      0,699 → 0,713 → 0,723 → **0,725** (rodada final) contra uma linha de
      base de ~0,66 — cada rodada produziu ganho real, mas com retorno
      visivelmente decrescente (1,4 → 1,0 → 0,2 pontos percentuais entre
      rodadas), o próprio padrão que motivou parar de buscar novas features
      nesta versão. Também comparado contra Regressão Logística e Random
      Forest em cada rodada: na rodada intermediária os três ficaram muito
      próximos (Regressão Logística chegou a vencer em recall), mas a partir
      da terceira rodada o XGBoost volta a se destacar, com a maior margem na
      rodada final (recall 0,624, precisão 0,528, AUC-ROC 0,737, contra 0,596
      / 0,530 / 0,729 do Random Forest e 0,577 / 0,521 / 0,716 da Regressão
      Logística) — leitura registrada no notebook: quanto mais features
      envolvem interações (sequência de erros combinada com histórico,
      contagem de tentativas combinada com taxa por habilidade), maior a
      vantagem de um modelo de árvores sobre um modelo linear, que não capta
      essas interações sem que sejam construídas manualmente. SHAP confirma a
      validade de quase toda feature nova, com uma exceção honesta: na rodada
      final, `taxa_acerto_na_habilidade` é a mais importante (0,34), seguida
      por `sequencia_erros_anterior` (0,20) e `n_tentativas_habilidade_anteriores`
      (0,13, confirmando que a confiabilidade da estimativa por habilidade é,
      ela mesma, sinal útil); `posicao` e `dificuldade_habilidade` têm
      contribuição moderada mas real (0,04–0,05); `volatilidade_recente` foi a
      única aposta que não se confirmou (importância 0,004, quase a mais baixa
      do modelo) — mantida mesmo assim (não prejudica o XGBoost, que
      simplesmente ignora features fracas), mas registrada como hipótese que
      não rendeu o ganho esperado, não escondida por ter dado errado.
      **Correção de recall (decisão explícita do time, não trabalho futuro
      adiado)**: o modelo padrão (limiar 0,5, sem peso de classe) tinha
      recall de 0,25 na classe "erro" na primeira versão do notebook, subindo
      para 0,36 na rodada final de features — a maioria dos alunos em
      risco ainda passava sem sinalização, o que não atendia ao objetivo de
      negócio (deixar passar um aluno em risco custa mais do que um alarme
      falso, porque a janela de intervenção se fecha). Corrigido em duas
      etapas, com número real medido em cada rodada: (1) `scale_pos_weight`
      no XGBoost eleva o recall para 0,63 no mesmo limiar 0,5 (rodada final;
      0,58 → 0,58 → 0,60 nas rodadas anteriores), à custa de acurácia geral
      (0,73→0,69) e precisão (0,68→0,53); (2) ajuste do limiar de decisão via
      `precision_recall_curve`, buscando o menor limiar que atinge recall ≥
      0,80, resultou em limiar 0,388 → recall 0,80, precisão 0,45 (melhor
      resultado das quatro rodadas nesse ponto de operação — 0,41 → 0,42 →
      0,44 antes), acurácia 0,60. A queda de acurácia é esperada e aceita
      deliberadamente — não é regressão, é a troca assimétrica que o
      objetivo de negócio exige; cada rodada de engenharia de features
      tornou essa troca menos custosa. SHAP, cards explicáveis e a síntese
      CRISP-DM foram atualizados a cada rodada para explicar o modelo vigente
      (nunca um modelo descartado). PDF final com 26 páginas (13 na primeira
      versão). **Engenharia de features encerrada deliberadamente após a
      quarta rodada** — decisão explícita do time diante do padrão de retorno
      decrescente (1,4 → 1,0 → 0,2 pontos percentuais de acurácia entre
      rodadas), registrada no próprio notebook como decisão, não como
      abandono. Busca de hiperparâmetros do XGBoost e busca do tamanho ótimo
      da janela recente ficam como os itens de maior potencial ainda
      pendentes — o primeiro ganhou prioridade depois da rodada 3, quando o
      XGBoost passou a se destacar dos outros algoritmos (sinal de que o
      modelo já explora interações relevantes entre features). Teto
      estrutural também registrado: nenhuma engenharia de feature sobre este
      dataset recupera um sinal de latência/tempo entre tentativas — o
      ASSISTments não tem timestamp, mesma limitação já documentada para o
      ASSISTments/EdNet em `docs/architecture/DATASETS_ETL.md`; esse sinal só
      existirá com uso real do satélite via `TelemetryEvent`
- [ ] Business Model Canvas + pitch deck
- [ ] Ensaio da demo ao vivo com banca simulada

Nota de infraestrutura sobre PySpark/JVM/Windows: ver `docs/architecture/DATASETS_ETL.md`.

---

## Disciplinas do 3º Período → Artefatos

| Disciplina | Como aparece no projeto | Artefato avaliável |
|---|---|---|
| Paralelismo | FastAPI async + RabbitMQ + stress test | Relatório latência: sequencial vs. paralelo |
| Data Mining | PySpark ETL ASSISTments 2009 + XGBoost + SHAP | Notebook CRISP-DM documentado |
| Computação Distribuída | Arquitetura satélite + Flower FL | Experimento FL centralizado vs. federado |
| Graph Mining | NetworkX trilhas + Rede de Cuidado | Grafos visualizáveis + recomendação no app |
| Ética em IA / XAI | SHAP cards + LGPD + Privacy by Design | Cards explicáveis na interface |
| Empreendedorismo | SaaS B2B2C + pitch + canvas | Pitch deck + demo ao vivo |

---

## Critérios de aceite — a demo está pronta quando

- [ ] Professor insere atividade → 3 versões geradas em < 10 segundos
- [ ] Aluno abre app e encontra atividade no formato correto para seu perfil
- [ ] Pais visualizam histórico + explicação da adaptação em linguagem simples
- [ ] Stress test: 100 sessões paralelas sem degradar o core
- [ ] Grafo gera recomendação visível no app
- [ ] Card SHAP explicável aparece na interface do professor
- [x] Experimento FL: centralizado vs. federado com resultado quantificado —
      ver `cognikids-adapt/federated/relatorio_fl.md` (0,747 vs. 0,747, empate)
