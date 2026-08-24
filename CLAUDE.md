# CogniKids V2.x — Adaptação Curricular com IA
## CLAUDE.md — Briefing permanente do projeto

> **Leia este arquivo inteiro antes de qualquer ação.**
> Ele descreve o que já existe, o que será construído neste repositório,
> e as regras que nunca podem ser violadas.

---

## 1. Contexto — o que já existe

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

---

## 2. O que o sistema core já tem

O core **mora neste mesmo repositório**, na pasta `cognikids-backend/`, como
um serviço próprio (Flask + MongoDB, porta padrão do serviço core). Ele
continua em manutenção ativa — correções críticas, autorização e acessibilidade
seguem evoluindo diretamente nele — mas mantém seu papel de **serviço
independente**: roda no seu próprio processo/container, com seu próprio banco,
e nunca deve depender do satélite para funcionar.

```
cognikids-backend/  (Flask + MongoDB — SERVIÇO CORE, dentro deste monorepo)
├── 18 controllers MVC
│   auth · student · teacher · parent · iot · alert · schedule
│   forum · gallery · consent · accessibility · break · grade · qa...
├── Models/
│   ├── accessibility_profile_model.py  ← PEÇA CENTRAL
│   │   tokens comportamentais por criança (sem diagnóstico médico)
│   │   ex: audio_disponivel, instrucao_uma_por_vez, fonte_ampliada...
│   └── consent_model.py  ← consentimento LGPD com revogação imediata
├── mqtt_to_redis_bridge.py  ← pulseira M5Stack → MQTT → Redis
├── scripts/utils/train_model.py  ← Random Forest (BPM+GSR → risco de crise)
└── cognikids-front-end/  (Streamlit — dívida técnica: duplicado)
```

**O que o core faz hoje:**
- Recebe dados biométricos da pulseira (BPM + GSR) via MQTT → Redis
- Classifica risco de crise com Random Forest (dados sintéticos)
- Gerencia perfis de acessibilidade configurados pelos pais
- Controla notas, desafios, galeria, fórum, agenda, Q&A
- Implementa consentimento LGPD com revogação imediata
- Emite alertas em tempo real para a professora

**O que o core NÃO faz (e este projeto resolve):**
O perfil de acessibilidade existe mas não é usado para adaptar conteúdo
pedagógico real. O professor não tem como enviar uma atividade e receber
versões adaptadas automaticamente para cada criança. Este projeto fecha
esse ciclo.

---

## 3. O que vamos construir agora (novo serviço satélite)

Dentro deste mesmo repositório, vamos criar um **novo serviço** — o satélite
(`cognikids-adapt/`) — completamente novo, desenvolvido do zero neste
semestre, rodando como microserviço independente ao lado do core
(processo/container próprio, banco próprio, sem tocar no código do core).

**O módulo central é o Motor de Adaptação Curricular:**

```
Professor insere atividade (texto livre ou banco)
→ Gateway FastAPI :8001  [A CRIAR]
→ RabbitMQ               [A CRIAR]
→ Worker de análise: Text Mining (CommonLit + Bloom's Taxonomy)  [A CRIAR]
→ Worker de perfil: lê tokens do core (read-only)  [A CRIAR]
→ Worker de adaptação: LLM gera versão adaptada por criança  [A CRIAR]
→ Professor revisa e aprova
→ Atividade chega no app do aluno no formato ideal  [A CRIAR]
→ Logs de interação → realimentam Data Mining  [A CRIAR]
```

**Tudo em `cognikids-adapt/` será criado do zero durante o semestre.**
Hoje essa pasta ainda não existe — só o core (`cognikids-backend/`) está
presente no repositório.

---

## 4. Arquitetura: monorepo, dois microserviços

Core e satélite vivem no **mesmo repositório git**, mas continuam sendo
**dois serviços independentes em runtime** — processos separados, containers
separados, bancos separados. Monorepo é só sobre onde o código-fonte mora;
não muda a separação de responsabilidades nem o desacoplamento em tempo de
execução.

```
CogniKids/                      ← este repositório (monorepo)
├── cognikids-backend/          ← serviço CORE (Flask, existente, em manutenção ativa)
├── cognikids-front-end/        ← front-end core (Streamlit)
├── cognikids-pulseira-m5stack/ ← firmware da pulseira
├── cognikids-adapt/             ← serviço NOVO [A CRIAR]
│   ├── gateway/                 ← FastAPI :8001
│   ├── workers/                 ← Workers RabbitMQ
│   │   ├── worker_analysis.py      ← Text Mining + Bloom's Taxonomy
│   │   ├── worker_profile.py       ← lê perfil do core (read-only)
│   │   └── worker_adaptation.py    ← chama LLM, gera versão adaptada
│   ├── pipeline/                 ← PySpark ETL + XGBoost + SHAP
│   ├── graph/                    ← NetworkX (grafo de conhecimento)
│   ├── federated/                 ← Flower (Federated Learning)
│   └── scripts/                   ← emulador de carga, testes de contrato
├── mobile/                     ← Flutter app (3 perfis) [A CRIAR]
├── docker-compose.yml          ← orquestra os dois serviços + infra (RabbitMQ, Mongo satélite)
├── .env.example
└── CLAUDE.md                   ← este arquivo
```

### Regras da fronteira — NUNCA violar
1. O satélite **nunca escreve** no banco MongoDB do core
2. O satélite **nunca importa** código Python do core (nada de `from cognikids_backend...`) — comunicação só via rede
3. O core **continua funcionando** mesmo que o satélite esteja offline (containers/processos independentes)
4. Integração apenas por: JWT compartilhado + GET read-only no core, chamado via HTTP
5. Estar no mesmo repositório não é desculpa para acoplar — se o satélite precisa de algo do core, é uma chamada HTTP, nunca um import ou um caminho de arquivo compartilhado

---

## 5. Princípio pedagógico central — NUNCA violar

**O conteúdo pedagógico NUNCA muda.**
Apenas formato e linguagem são adaptados.
O professor revisa e aprova cada versão antes de enviar para o aluno.

**Adaptação por perfil:**

| Aluno | Condição | O que muda na atividade |
|-------|----------|------------------------|
| Lucas (exemplo) | TEA grau 1 | Passo a passo numerado · áudio · exemplo cotidiano · fonte ampliada · fundo #F5F0E8 · ZERO animações |
| Sofia (exemplo) | TDAH | Chunks ≤3 linhas · checklist dopaminérgico · negrito estratégico · progresso visível |
| Pedro (exemplo) | Dislexia | Atkinson Hyperlegible · line-height 2.0 · letter-spacing 0.08em · fundo #FEFAE0 · texto à esquerda |

Os perfis reais vêm dos tokens configurados no core pelos pais.
Esses exemplos são apenas ilustrativos para guiar o desenvolvimento.

---

## 5.1 Arcabouço Multi-Dataset + Grafo de Conhecimento (fonte: Documento de Arquitetura V2)

A mineração e o Grafo de Conhecimento não usam dado médico real — são calibrados
com datasets públicos numa fase offline, e depois realimentados continuamente
pelo uso real do aluno (fase online). Duas fases, um único grafo:

**Fase 1 — Calibração offline (datasets públicos):**

| Dataset | Papel | Status | Local |
|---|---|---|---|
| **CommonLit (CLEAR Corpus)** | calibra o LLM para legibilidade/complexidade textual da versão adaptada | ✅ baixado — 4.726 excertos, `Excerpt` + 6 métricas de legibilidade (`Flesch-Kincaid-Grade-Level`, `BT Easiness`...) | `datasets/raw/commonlit_clear_corpus/CLEAR.csv` |
| **Educational Bloom's Taxonomy** | garante que resumir/adaptar não remova o conceito pedagógico central | ✅ baixado — 8.767 questões rotuladas `BT1`–`BT6` | `datasets/raw/blooms_taxonomy/blooms_taxonomy_dataset.csv` |
| **ASSISTments 2009** | logs reais de tutores inteligentes (tentativas, habilidades, tipo de resposta) → arestas iniciais do Grafo de Conhecimento | ✅ baixado — 4.148 alunos, `skill_ids` + `attempt_counts` | `datasets/raw/assistments2009/assistments2009_train.parquet` |
| **EdNet (amostra, substitui DSB2019)** | padrões de navegação/atrito (sequência `enter`→`respond`→`submit` por aluno) → calibra detecção de frustração/fadiga | ✅ baixado — ~5.000 alunos, log de eventos com timestamp | `datasets/raw/ednet_sample/raw_data/` |

`datasets/raw/` está no `.gitignore` (dados públicos grandes, não versionar).
Comandos para reobter:

```bash
# CommonLit (CLEAR Corpus) — Kaggle, dataset não-competição
kaggle datasets download -d verracodeguacas/clear-corpus --unzip -p datasets/raw/commonlit_clear_corpus

# Bloom's Taxonomy — Kaggle, dataset não-competição
kaggle datasets download -d vijaydevane/blooms-taxonomy-dataset --unzip -p datasets/raw/blooms_taxonomy

# ASSISTments 2009 — Hugging Face, público, sem login
curl -sL "https://huggingface.co/datasets/Atomi/ASSISTments2009/resolve/main/data/train-00000-of-00001.parquet" \
  -o datasets/raw/assistments2009/assistments2009_train.parquet

# EdNet (amostra, substitui DSB2019 — Kaggle retirou os dados dessa competição
# em 2026, sem previsão de retorno) — Hugging Face, público, sem login
curl -sL "https://huggingface.co/datasets/Unggi/ednet5000_raw_data/resolve/main/ednet5000_raw_data.tar.gz" \
  -o datasets/raw/ednet_sample/ednet5000_raw_data.tar.gz
tar -xzf datasets/raw/ednet_sample/ednet5000_raw_data.tar.gz -C datasets/raw/ednet_sample

# Upgrade opcional de escala (mesma família do DSB2019, citado no Documento de
# Arquitetura V2): "Jo Wilder and the Capitol Case" — ainda existe no Kaggle,
# mas exige aceitar as regras da competição no navegador antes do download:
# https://www.kaggle.com/competitions/predict-student-performance-from-game-play/rules
kaggle competitions download -c predict-student-performance-from-game-play -p datasets/raw/jo_wilder_gameplay
```

> ⚠️ O Kaggle **retirou os dados** da competição `data-science-bowl-2019`
> (arquivos não listam mais na API, mesmo autenticado) — não é mais possível
> baixá-la. O EdNet a substitui no papel de "Análise de Variabilidade
> Comportamental em Interação" (seção 5.1).

**Fase 2 — Loop de feedback online (uso real, sem dado médico):**

```
Aluno interage com a atividade adaptada
  → TelemetryEvent (step_completed, hint_requested, abandoned, duration_ms)
  → IoT: BPM/GSR durante a atividade (pico de ansiedade?)
  ↓
Grafo de Conhecimento é atualizado
  (aresta fica "mais pesada"/difícil se o aluno travou ou teve pico de estresse)
  ↓
Próxima adaptação para aquele aluno já nasce ajustada
  (blocos menores, outro formato, outro nível de estímulo)
```

O grafo representa: nós = aluno + conceitos + formatos (visual/textual/áudio);
arestas = domínio ou dificuldade. A mineração no grafo busca o "caminho de
aprendizado de menor atrito" por criança — não um valor estático, recalculado
a cada nova sessão de uso.

**Definição concreta de nós e arestas (Grafo de Conhecimento por criança):**

- **Nós = conceitos cognitivos**, não atividades. Ex: `sequência_auditiva`,
  `categorização_visual`, `causa_efeito`, `reconhecimento_sonoro`. Cada nó
  também carrega o **formato de processamento** associado (visual, auditivo,
  passo a passo).
- **Arestas = domínio do aluno sobre aquele conceito/formato**, ponderadas por
  três sinais extraídos do `TelemetryEvent`: **taxa de acerto**, **latência**
  (tempo até responder/completar o passo) e **persistência** (tentativas antes
  de abandonar ou pedir dica).
- **Cold start**: no início, o grafo nasce com sinal grosseiro dos tokens de
  acessibilidade já configurados pelos pais no core (ex: `audio_disponivel`).
  Esse é o único uso direto dos tokens do core no grafo.
- **Peso da aresta (validado com dado real, `cognikids-adapt/notebooks/nucleo2_grafo_conhecimento.ipynb`)**:
  média simples de sinais normalizados (não modelo treinado — mesma filosofia
  determinística/explicável da ADR-006), ex. `(taxa_acerto + persistência_normalizada) / 2`.
  Cada sinal isolado é fraco (correlações entre -0.02 e -0.15 nos datasets de
  calibração), o que reforça a necessidade de combinar sinais em vez de usar um só.
- **Achado confirmado empiricamente**: o sinal de abandono/persistência fina
  **não existe de forma observável nem no ASSISTments nem no EdNet** (testado
  em 150 alunos reais do EdNet, taxa de abandono = 0% em todos) — não é só o
  core que não produz esse dado (frase abaixo), os datasets públicos de
  calibração também não o oferecem. Esse sinal só existirá com uso real do
  satélite via `TelemetryEvent` tipo `abandoned`/`hint_requested` — não dá pra
  calibrar essa parte na fase offline, só a fase online resolve isso.
- **Refinamento contínuo**: a cada atividade adaptada que a criança usa no
  satélite, o `TelemetryEvent` gerado atualiza o peso das arestas — o grafo
  fica mais preciso a cada sessão. O core hoje **não** produz esse dado fino
  (`challenge_model.py` só registra `completed_at`, sem acerto/latência/tentativas)
  — esse sinal é gerado inteiramente pelo satélite.
- **Uso na adaptação**: o motor de adaptação (Núcleo 3) consulta o grafo antes
  de chamar o LLM — é o grafo que decide **o quê** adaptar (ex: "está fraco em
  causa-efeito visual, forte em sequência auditiva"), o LLM só decide **como**
  expressar isso em texto/áudio/pictograma. Isso é o que torna a adaptação
  explicável (`xai_explanation` no contrato de API, seção 8).

---

## 5.2 Três Domínios da Aprendizagem + UDL 3.0 (fundamentação teórica ampliada)

Descoberta no protótipo do Núcleo 1: a Taxonomia de Bloom cobre só o domínio
**cognitivo** (pensar). Existem dois outros domínios clássicos da educação, e um
framework de design mais recente que amarra os três — juntos, dão ao projeto uma
base teórica mais forte do que só Bloom's isolado.

**Os três domínios clássicos da aprendizagem (Bloom, Simpson, Krathwohl):**

| Domínio | Taxonomia | Mede | Uso no CogniKids |
|---|---|---|---|
| Cognitivo | Bloom (1956/2001) | Processo de pensamento (memorizar → criar) | `worker_analysis.py` — classificador de verbo em PT-BR (ADR-006) |
| Psicomotor | Simpson (1972) | Habilidade física/motora (percepção → criação de movimento) | `worker_analysis.py` — mesma técnica de regra por verbo, nova dimensão de saída |
| Afetivo | Krathwohl (1964) | Atitude/emoção (receber → internalizar um valor) | **Não vem do texto** — é o que a pulseira IoT do core já mede (BPM/GSR → ansiedade). Ponte conceitual para o Núcleo 2 (Grafo de Conhecimento), não um classificador de texto novo |

A Taxonomia de Simpson tem 7 níveis (percepção, prontidão, resposta guiada,
mecanismo, resposta complexa, adaptação, criação) e identifica se uma atividade
exige execução motora (ex: "monte", "manuseie") — relevante porque parte do
público do CogniKids tem dificuldades de coordenação motora associadas (comum
em TEA/TDAH). Sem dataset público em nenhum idioma para nenhuma das duas
taxonomias (Simpson e Krathwohl) — mesma situação que motivou a abordagem por
regra em Bloom's PT-BR.

**UDL 3.0 — Universal Design for Learning (CAST, jul/2024):** não é uma
taxonomia de classificação de conteúdo, é o **framework de design que justifica
a arquitetura do motor de adaptação**. Baseado em neurociência (três redes
cerebrais), define 3 princípios com 3 guidelines cada:

| Princípio (rede cerebral) | Guidelines | Onde aparece no CogniKids |
|---|---|---|
| **Engajamento** (rede afetiva) | Acolher interesses/identidades · Sustentar esforço · Capacidade emocional | Professor no loop de aprovação · progresso visível (Sofia) |
| **Representação** (rede de reconhecimento) | Percepção · Linguagem e símbolos · Construção de conhecimento | Os 3 formatos de saída (texto/áudio/pictograma) — é a definição central do princípio |
| **Ação e Expressão** (rede estratégica) | Interação · Expressão/comunicação · Desenvolvimento de estratégia | Passo a passo numerado (Lucas) · checklist dopaminérgico (Sofia) |

UDL 3.0 é citado como a fundamentação teórica do **princípio pedagógico central**
(seção 5: adaptar formato, nunca conteúdo) e da arquitetura de 3 formatos —
não como algo a implementar em código, e sim como referência acadêmica que
justifica por que o sistema é desenhado assim.

---

## 6. Stack Tecnológica (a implementar)

### Backend Satélite
- **Gateway:** FastAPI :8001 + Pydantic v2 + async/await
- **Mensageria:** RabbitMQ (exchange: cognikids, filas: analysis, profile, adaptation, telemetry)
- **Banco:** MongoDB TimeSeries :27018 (separado do core :27017)
- **LLM:** Gemma 4 12B (Unified) local via Ollama, custo zero (fallback: Gemini
  API camada gratuita). Ver ADR-002.
- **Auth:** JWT HS256 — mesmo SECRET_KEY do core (via variável de ambiente)

### Data & ML
- **Datasets:** CommonLit Readability Prize · Educational Bloom's Taxonomy ·
  ASSISTments / EdNet · DSB2019 (PBS KIDS) / Jo Wilder PSP Raw — ver seção 5.1
  para o papel de cada um
- **Taxonomias sem dataset (classificação por regra, ver seção 5.2):**
  Simpson's Taxonomy (domínio psicomotor) · Krathwohl's Taxonomy (domínio
  afetivo, ponte com IoT) · UDL 3.0 (framework de design, não classificador)
- **ETL:** PySpark 3.5 — sobre os datasets acima (público, sem dado médico real)
- **Modelo:** XGBoost + SHAP (previsão de risco de frustração/fadiga, calibrado com DSB2019)
- **Grafos:** NetworkX (Grafo de Conhecimento: aluno + conceitos + formatos,
  arestas calibradas com ASSISTments/EdNet e realimentadas pelo uso real — seção 5.1)
- **FL:** Flower (FedAvg — privacidade das crianças)

### Mobile
- **Framework:** Flutter 3.x + Riverpod
- **3 perfis:** Professor · Pais · Aluno (temas visuais distintos por neurologia)
- **Offline:** adaptação de dificuldade client-side sem conexão

---

## 7. Esquema canônico — TelemetryEvent (a implementar)

```python
class TelemetryEvent(BaseModel):
    event_id: str          # UUID v4
    student_id: str        # ID do aluno no core
    activity_id: str       # ID da atividade adaptada
    session_id: str        # UUID da sessão
    event_type: str        # step_completed | audio_played | abandoned | hint_requested
    step_number: int | None
    concept: str | None    # conceito cognitivo do passo (só quando avaliável — ver abaixo)
    correct: bool | None   # acerto/erro do passo (só quando avaliável — ver abaixo)
    duration_ms: int       # tempo no passo atual
    timestamp: datetime    # UTC
    metadata: dict         # dados extras sem schema fixo
```

`concept`/`correct` só fazem sentido em `event_type="step_completed"` sobre um
passo avaliável (nem todo passo tem resposta certa/errada — ex: um passo de
leitura pura não tem). Quando os dois vêm preenchidos, `worker_ingestion.py`
chama `atualizar_aresta_grafo()` (`workers/knowledge_graph.py`) e refina a
aresta aluno-conceito no Grafo de Conhecimento — é assim que o loop da seção
5.1 se fecha (**✅ implementado e testado**, ver ADR relacionada no roadmap).

---

## 8. Contratos de API (a implementar)

### POST /v1/curriculum/adapt
```json
Request:
{
  "teacher_id": "string",
  "title": "string",
  "subject": "string",
  "original_content": "string",
  "student_ids": ["string"]
}

Response 202:
{
  "job_id": "uuid",
  "status": "queued",
  "estimated_seconds": 15
}
```

### GET /v1/curriculum/jobs/{job_id}
```json
Response:
{
  "job_id": "uuid",
  "status": "completed | processing | failed",
  "adaptations": [
    {
      "student_id": "string",
      "adapted_content": "string",
      "format_applied": ["passo_a_passo", "audio", "exemplo_cotidiano"],
      "xai_explanation": "string",
      "profile_tokens_used": {}
    }
  ]
}
```

### POST /v1/telemetry/events
```json
Body: TelemetryEvent
Response 201: { "event_id": "uuid", "ingested": true }
```

---

## 9. Variáveis de Ambiente (.env.example)

```bash
# Core (apenas leitura, só via HTTP — nunca Mongo direto)
CORE_BASE_URL=http://localhost:5001
CORE_JWT_SECRET=<mesmo secret do Flask core>
# ObjectId de um usuário tipo='admin' real na base do core — usado pelo
# worker_profile.py para montar o JWT de serviço (pode_ver_aluno libera
# qualquer aluno para admin). Sem isso, GET /api/accessibility falha.
# Criar com `python scripts/criar_admin.py` — POST /api/register é rota
# pública e recusa tipo='admin' desde a ADR-010.
CORE_SERVICE_USER_ID=<ObjectId de um usuário admin no core>

# Satélite (novo)
SATELLITE_MONGO_URI=mongodb://localhost:27018/cognikids_adapt
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
RABBITMQ_EXCHANGE=cognikids

# LLM (híbrido, custo zero — ver ADR-002)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma4:12b
GEMINI_API_KEY=<sua chave Gemini — fallback gratuito, obtida no Google AI Studio>

# Gateway
GATEWAY_PORT=8001
GATEWAY_HOST=0.0.0.0
```

> ⚠️ O serviço core tinha `TEMP_API_KEY_123` hardcoded no código.
> Sprint 0 corrige isso. Nunca repetir esse padrão em nenhum dos dois serviços.

---

## 9.1 LGPD — Encarregado de Dados e Retenção

Levantamento de conformidade feito nesta sessão (auditoria de dois revisores
independentes, um por serviço) encontrou o sistema sem Encarregado
designado e sem política de retenção documentada em nenhum lugar — o que
segue corrige as duas lacunas mais baratas de fechar. As lacunas mais caras
(criptografia em repouso, log de acesso completo, TTL/auth no RabbitMQ e no
Mongo do satélite) continuam registradas como trabalho futuro, não
escondidas.

**Encarregado de dados (Art. 41 da LGPD):** Frederico Lemes Rosa, responsável
técnico do projeto, é o ponto de contato para qualquer solicitação de
titular de dados (pai/responsável, em nome da criança) sobre os dados
tratados pelo CogniKids — acesso, correção, portabilidade ou eliminação.
Contato: `frederico.lemesrosa@gmail.com`. Esta designação vale para a fase
atual (protótipo acadêmico); antes de qualquer uso com dado real de criança
fora de ambiente de demonstração, a designação e o processo de atendimento
ao titular precisam ser formalizados com um Encarregado dedicado, não
acumulado com a função técnica.

**Política de retenção (estado atual, honesto):** `curriculum_jobs` e
`telemetry_events` do satélite têm TTL de 180 dias (ADR-009). `registros_iot`
e `alerts` do core são eliminados no momento da revogação de consentimento,
não por tempo (ADR-008). Ainda sem expiração: `student_graphs` do satélite
(deliberado — é estado atual do aluno, não log, ver ADR-009) e o perfil de
acessibilidade do core (fica até a exclusão de conta). Nenhuma coleção
sensível deveria reter dado indefinidamente sem justificativa — o que ainda
não tem justificativa nem correção é registrado aqui, não escondido.

---

## 10. Roadmap de Sprints

### Sprint 0 — Higiene e estrutura (Ago · sem 1) ✅ CONCLUÍDO
- [x] Criar estrutura de pastas conforme seção 4 (`cognikids-adapt/{gateway,workers,pipeline,graph,federated,scripts}`)
- [x] docker-compose.yml (gateway + rabbitmq + mongodb satélite) — testado de ponta a ponta, `gateway` responde em `:8001/health`
- [x] .env.example com todas as variáveis documentadas (raiz do repo)
- [x] Script de health check: `cognikids-adapt/scripts/health_check.py` — verifica GET `/api/status` do core
- [x] Teste de contrato: `cognikids-adapt/gateway/tests/test_telemetry_contract.py` — 8 testes, válido aceito e 5 variações inválidas rejeitadas
- [x] Mover API key hardcoded do core para variável de ambiente — já feito em commit anterior desta branch (nenhuma chave hardcoded encontrada, só placeholders em `.env.example`)

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
- [x] Text Mining: complexidade (CommonLit) + Bloom's Taxonomy + Simpson's Taxonomy (psicomotor,
      ver seção 5.2) — `workers/text_mining_pt.py` (funções portadas do Núcleo 1) +
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
      `concept`/`correct` opcionais adicionados ao `TelemetryEvent` (ver seção 7).
      `worker_ingestion.py` agora chama `atualizar_aresta_grafo()` quando o evento
      é `step_completed` avaliável, refinando a aresta aluno-conceito na mesma
      coleção `student_graphs` que `worker_profile.py` lê. Testado de ponta a
      ponta via Docker Compose: 3 eventos reais de acerto levaram o peso de um
      conceito de 0 (cold start) a 0.875, e um job de adaptação seguinte já
      carregou esse valor refinado no `knowledge_graph_summary` — loop da seção
      5.1 fechado e confirmado. Regressão coberta por
      `workers/tests/test_worker_ingestion_grafo.py` (5 testes, Mongo falso)
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
      Sem notebook de origem (técnica nova neste projeto — ver decisão abaixo). Grafo
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
      **Resultado quantificado (satisfaz o critério de aceite da seção 14)**:
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
      navegador — mesmo obstáculo já registrado na seção 5.1; substituição
      documentada aqui, não silenciosa). `cognikids-adapt/notebooks/nucleo3_risco_frustracao.ipynb`,
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
      estrutural also registrado: nenhuma engenharia de feature sobre este
      dataset recupera um sinal de latência/tempo entre tentativas — o
      ASSISTments não tem timestamp, mesma limitação já documentada para o
      ASSISTments/EdNet na seção 5.1; esse sinal só existirá com uso real do
      satélite via `TelemetryEvent`
- [ ] Business Model Canvas + pitch deck
- [ ] Ensaio da demo ao vivo com banca simulada

> **Nota de infraestrutura**: PySpark exige Java (JVM) — não é uma biblioteca
> Python pura, é uma API que se comunica com o motor Spark (Scala/JVM) via
> Py4J. Sem JDK instalado, `import pyspark` funciona mas qualquer operação real
> falha. JDK 17 (Microsoft Build of OpenJDK) instalado nesta máquina para
> viabilizar isso. No Windows, também é necessário setar `PYSPARK_PYTHON`
> explicitamente para o caminho completo do `python.exe` — sem isso, o
> processo worker que o Spark abre é interceptado pelo stub da Microsoft
> Store e a conexão do worker com o driver expira (erro real encontrado e
> corrigido nesta sessão, não hipotético).

---

## 11. Disciplinas do 3º Período → Artefatos

| Disciplina | Como aparece no projeto | Artefato avaliável |
|---|---|---|
| Paralelismo | FastAPI async + RabbitMQ + stress test | Relatório latência: sequencial vs. paralelo |
| Data Mining | PySpark ETL DSB2019 + XGBoost + SHAP | Notebook CRISP-DM documentado |
| Computação Distribuída | Arquitetura satélite + Flower FL | Experimento FL centralizado vs. federado |
| Graph Mining | NetworkX trilhas + Rede de Cuidado | Grafos visualizáveis + recomendação no app |
| Ética em IA / XAI | SHAP cards + LGPD + Privacy by Design | Cards explicáveis na interface |
| Empreendedorismo | SaaS B2B2C + pitch + canvas | Pitch deck + demo ao vivo |

---

## 12. Decisões Arquiteturais (ADRs)

### ADR-001: Monorepo com dois microserviços
**Decisão:** Código novo do satélite (`cognikids-adapt/`) vive no mesmo
repositório git do core (`cognikids-backend/`), mas roda como serviço
independente em runtime — processo, container e banco próprios. Comunicação
só via HTTP (JWT + GET read-only), nunca por import de código.
**Motivo:** Simplifica o desenvolvimento em equipe pequena e a apresentação
(um só checkout), sem abrir mão do isolamento que protege o sistema core
já validado de risco de regressão.

### ADR-006: Text Mining em PT-BR sobre datasets em inglês — ✅ DECIDIDO
**Achado (protótipo Núcleo 1, `cognikids-adapt/notebooks/nucleo1_text_mining.ipynb`):**
CommonLit e Bloom's Taxonomy são datasets em inglês; testado com texto em
português, o classificador Bloom's (TF-IDF + LogReg treinado só em inglês) não
generalizou. Flesch-Kincaid também não é confiável direto em português.
**Decisão: sem depender de LLM** (preferência explícita do time — evitar
dependência de LLM sempre que der pra resolver de forma determinística).
Implementado e validado com dado real no notebook:
1. **Complexidade** — Índice Flesch adaptado para português (Martins et al. 1996,
   USP São Carlos): `248.835 - 1.015*(palavras/frases) - 84.6*(sílabas/palavras)`,
   contagem de sílabas via `pyphen` (lang `pt_BR`). Sem dataset, sem API.
2. **Intenção pedagógica** — classificador por regra usando a tabela de verbos
   da Taxonomia de Bloom em português (padrão pedagógico brasileiro, alinhado à
   BNCC), casando infinitivo + formas de imperativo/comando (`explique`,
   `compare`, `crie`...). Determinístico, sem treino, auditável (bom para XAI).
   Default conservador (BT1/memorização) quando nenhum verbo de comando é
   reconhecido no texto.

O classificador em inglês (TF-IDF + LogReg, ~73% acurácia) fica só como
referência de que o sinal existe no dataset — **não vai para produção**.
`worker_analysis.py` (Sprint 2) implementa as duas funções PT-BR validadas no
notebook: `avaliar_complexidade_pt()` e `classificar_bloom_pt()`.

**Validação quantitativa (não só qualitativa)**: montado um conjunto de teste
rotulado à parte (`dados_avaliacao/teste_bloom_pt.json` e `teste_simpson_pt.json`,
46 e 22 casos, múltiplas disciplinas, com verbos deliberadamente fora da tabela
original). Acurácia inicial: **60,9% (Bloom's) e 77,3% (Simpson's)** — bem abaixo
do que os poucos exemplos escolhidos a dedo sugeriam. Todo erro veio de cobertura
de vocabulário (verbo válido, fora da tabela). Corrigido expandindo as tabelas
+ regra de desempate (nível mais alto entre verbos empatados) → **100% nos dois**
após reavaliação no mesmo conjunto. Lição registrada: validação com poucos
exemplos próprios superestima desempenho; a tabela de verbos deve crescer
incrementalmente com uso real, não é um artefato fechado.

> ⚠️ **Correção obrigatória de leitura desse 100% (auditoria do conselho,
> ADR-011).** Esse número é **in-sample**: a tabela foi expandida com os erros
> do próprio conjunto de teste e reavaliada no mesmo conjunto. O número honesto
> de generalização é o **primeiro**: **60,9% (Bloom) e 77,3% (Simpson)** — as
> únicas medidas feitas sobre vocabulário não visto. Medido depois, sobre
> enunciados brasileiros típicos do fundamental I: **8 de 9 caem no default
> BT1** (falham `faça`, `dê`, `escreva`, `circule`, `complete`, `marque`,
> `ligue`, e enunciado nominalizado sem verbo). Ao citar em banca ou artigo,
> reportar os dois números e rotular o 100% como in-sample. E o `(default)`
> precisa virar estado bloqueante, não um BT1 silencioso: subclassificar é a
> direção **insegura**, porque autoriza uma adaptação que reduz a atividade a
> memorização e um invariante ingênuo aprovaria comparando BT1 com BT1.

### ADR-007: Ampliação teórica — Simpson, Krathwohl e UDL 3.0 — ✅ DECIDIDO
**Decisão:** além de Bloom's (domínio cognitivo), o projeto passa a usar:
  - **Simpson's Taxonomy (1972, domínio psicomotor)** — implementada em código,
    mesma técnica de classificador por regra de verbo em PT-BR do Bloom's
    (sem dataset, ver ADR-006). Detecta se a atividade exige execução motora.
  - **Krathwohl's Taxonomy (1964, domínio afetivo)** — **não implementada como
    classificador de texto**; documentada como ponte conceitual com a telemetria
    IoT do core (BPM/GSR já mede estado afetivo/ansiedade). Integração real
    acontece no Núcleo 2 (Grafo de Conhecimento), não no Núcleo 1.
  - **UDL 3.0 — Universal Design for Learning (CAST, jul/2024)** — não é
    classificador, é o framework de design citado para justificar teoricamente
    a arquitetura de 3 formatos de saída (seção 5) e o princípio "adaptar
    formato, nunca conteúdo".
**Motivo:** Bloom's isolado só cobre 1 de 3 domínios clássicos da aprendizagem;
completar o quadro (seção 5.2) fortalece a fundamentação acadêmica do projeto e
identifica, via Simpson's, um sinal (demanda motora) hoje ignorado — relevante
porque parte do público do CogniKids tem dificuldade de coordenação motora
associada ao TEA/TDAH.

### ADR-008: Revogação de consentimento com efeito real sobre o dado — ✅ DECIDIDO
**Contexto:** auditoria de conformidade (dois revisores independentes, um por
serviço, seção 9.1) encontrou que revogar consentimento só mudava uma flag no
documento de consentimento — nenhum dado já coletado era eliminado ou
anonimizado, apesar de `consent_model.py` já alegar em comentário que "a
revogação é tão fácil quanto conceder... e o efeito é imediato". O efeito
imediato real era só sobre visibilidade (o professor deixava de ver o aluno),
não sobre o dado em si.
**Decisão:** `Consent.registrar()` agora elimina (`delete_many`, não só
anonimiza) o histórico bruto de `registros_iot` e `alerts` de um aluno no
momento em que `coleta_biometrica` transiciona de concedido para revogado —
não há finalidade legítima remanescente para reter dado biométrico bruto de
uma criança (art. 11 da LGPD) uma vez que a coleta deixou de ser autorizada.
`compartilhar_escola` fica deliberadamente de fora dessa eliminação: revogar
o compartilhamento com a escola não significa que o dado perdeu finalidade
(o app e o responsável continuam usando), só que o professor deixa de
enxergá-lo — isso já era coberto por `alunos_visiveis`/`filtrar_por_consentimento`.
**Escopo desta correção, dito com honestidade:** cobre só o **core**. O
satélite (`telemetry_events`, `student_graphs`, `curriculum_jobs`) é um banco
separado, sem mecanismo de revogação em cascata entre os dois serviços —
continua sendo uma lacuna real, registrada aqui, não escondida. Fechar isso
exigiria o satélite assinar/consultar eventos de revogação do core, hoje
inexistente.
**Validado com teste real:** revogar consentimento com um registro biométrico
já existente elimina o registro (`registros_iot`/`alerts` count vai a zero);
revogar só `compartilhar_escola` isoladamente não elimina nada, confirmando
que a distinção acima é aplicada corretamente, não só descrita.

### ADR-009: Consentimento e retenção no satélite — ✅ PARCIALMENTE FECHADO
**Contexto:** a auditoria de LGPD do satélite (dois revisores, seção 9.1)
encontrou dois problemas ativos: (1) o gateway aceitava e gravava telemetria
de qualquer aluno autenticado, sem checar se o responsável autorizou o uso
do app — autenticação (é o próprio aluno) e consentimento (os pais
autorizaram) são coisas diferentes, e só a primeira era checada; (2) nenhuma
coleção sensível do satélite (`curriculum_jobs`, `telemetry_events`,
`student_graphs`) tinha expiração — tudo persistia indefinidamente.
**Decisão — consentimento:** `POST /v1/telemetry/events` agora consulta
`GET /api/consent/{aluno_id}` no core (mesmo padrão de JWT de serviço já
usado por `workers/core_client.py`, replicado em `gateway/app/clients/core_client.py`
porque o worker de telemetria vive no gateway, não numa fila) antes de
aceitar o evento — rejeita com 403 se `uso_app` não estiver concedido, e com
503 se o core estiver inacessível (o lado seguro do erro, numa ingestão de
dado novo, é recusar, não aceitar por padrão). Validado com teste real via
Docker: 403 sem consentimento → 201 após conceder → 403 de novo após
revogar, com o core e o satélite rodando de verdade, não simulado.
**Decisão — retenção:** `curriculum_jobs` e `telemetry_events` ganharam
índice TTL (`expireAfterSeconds`, 180 dias — mesma ordem de grandeza de um
ano letivo), confirmado criado de verdade no Mongo (`getIndexes()`, não só
no código). `student_graphs` foi deixado de fora de propósito: é o estado
atual e cumulativo do domínio de conceitos do aluno, não um log — aplicar
TTL ali apagaria o grafo de um aluno ativo, o oposto do que a coleção existe
para fazer. A política de retenção certa para esse caso é vinculada a
exclusão de conta/revogação, não a tempo, e continua em aberto.
**Escopo desta correção, dito com honestidade:** o que ficou de fora,
registrado como trabalho futuro, não escondido: autenticação/autorização do
próprio broker RabbitMQ (hoje `guest:guest` por padrão, não verificado se
isso foi trocado em produção) e do MongoDB satélite (não verificado se roda
com auth habilitada) continuam fora do escopo desta correção — são
mudanças de infraestrutura, não de código de aplicação, e o risco relativo é
menor nesta fase (protótipo acadêmico, rede local) do que os dois problemas
já fechados aqui.

### ADR-010: Correções críticas de segurança — ✅ PARCIALMENTE FECHADO
**Contexto:** o time declarou intenção de colocar o sistema em produção com
professor, pais e alunos reais. Isso anulou a premissa que sustentava a
ADR-009 ("o risco relativo é menor nesta fase — protótipo acadêmico, rede
local"), e uma auditoria adversarial do conselho encontrou falhas que a
premissa anterior tolerava e a nova não. Todas confirmadas lendo o código,
não inferidas.

**Corrigido nesta rodada, com teste que tenta o ataque:**
1. **Escalonamento de privilégio pelo cadastro público.** `POST /api/register`
   não exige token e lia `tipo` do corpo, com `admin` em `TIPOS_PERMITIDOS` —
   qualquer pessoa com acesso de rede criava para si um perfil que, em
   `authz.py`, ignora consentimento (`pode_ver_aluno` retorna `True`
   incondicionalmente; `alunos_visiveis` devolve todos os alunos sem
   `filtrar_por_consentimento`). Efeito: leitura de biometria, alertas,
   sentimentos, notas e perfil funcional de **todas** as crianças. Corrigido
   com `TIPOS_AUTOREGISTRAVEIS` (`Utils/roles.py`); admin agora só nasce por
   `scripts/criar_admin.py`, que exige acesso ao servidor. O `.env.example`
   documentava o `curl` que explorava isso — substituído pelo script.
2. **IDOR no job de adaptação.** `GET /v1/curriculum/jobs/{job_id}` exigia só
   um JWT válido de qualquer perfil, sem checagem de propriedade. Corrigido
   com `pode_ver_job()` (professor dono ou aluno citado), devolvendo **404 e
   não 403** — quem não é dono não deve nem confirmar que o job existe.
3. **`POST /v1/curriculum/adapt` não validava `student_ids`.** Conferia o
   `teacher_id` e aceitava qualquer aluno; o `worker_profile` então buscava os
   tokens com a conta de serviço (admin), que ignora consentimento — furando
   exatamente a garantia que a ADR-008 celebra. Corrigido consultando
   `GET /api/teachers/{id}/students` **com o token do próprio professor**
   (nunca com autoridade elevada), rota que já aplica `alunos_visiveis`.
4. **Infraestrutura publicada na rede.** RabbitMQ com `guest:guest` e console
   de administração em `0.0.0.0:15672`, Mongo do satélite em `0.0.0.0:27018`
   sem auth. Portas religadas ao loopback e credenciais do broker movidas para
   o `.env`.

**Regressão coberta por** `cognikids-backend/tests/test_seguranca_producao.py`
(5 testes) e `cognikids-adapt/gateway/tests/test_curriculum_autorizacao.py` +
`test_curriculum_rotas_seguranca.py` (12 testes). São testes que **encenam o
ataque** e quebram o build se ele voltar a funcionar — diferente do resto da
suíte, que verifica se a funcionalidade funciona.

**O que fica aberto, dito com honestidade (não é lista genérica — foi
verificado no código):**
- **Auth no Mongo do satélite não foi habilitada.** `MONGO_INITDB_ROOT_USERNAME`
  só tem efeito em volume vazio; com `mongo-adapt-data` já populado ela é
  ignorada em silêncio e o banco seguiria sem auth *parecendo* protegido.
  Exige `db.createUser()` manual ou recriar o volume. Hoje a proteção real é
  o loopback.
- **Modelo de risco de crise sem validação real.** `scripts/utils/train_model.py`
  gera dado sintético com ruído de 25% e **8% dos rótulos invertidos de
  propósito**, com faixas de `ATIVO` e `TENSO` quase idênticas ("para baixar
  acurácia") e alvo declarado de `~75-82%`. É honesto como artefato de demo e
  indefensável como classificador de segurança: `LIMIAR_BPM_ALTO = 130` marca
  severidade máxima, e 130 bpm é uma criança de 7 anos no recreio. **Nenhum
  uso com criança real enquanto isso não for refeito.**
- Sem TLS (o core roda no servidor de desenvolvimento do Werkzeug), sem
  criptografia em repouso, sem log de acesso de leitura, sem recuperação de
  senha, sem endpoint de portabilidade ou exclusão de conta, sem rate limit,
  sem verificação de e-mail, sem revogação em cascata core→satélite.
- `link-child` exige `@responsavel_required`, mas como o cadastro é público
  qualquer um vira responsável e vincula uma criança pelo e-mail. A correção
  do item 1 fecha a escalada para admin, **não** esta: falta confirmação por
  terceiro (escola) no vínculo.

### ADR-011: Correções do conselho de especialistas — ✅ APLICADAS (rodada 1)
**Contexto:** um conselho de 9 autoridades independentes (terapia ocupacional/TEA,
psicopedagogia TDAH+dislexia, fonoaudiologia/CAA, professora de sala inclusiva,
mãe de criança autista, DPO/LGPD, educação inclusiva e marco legal, evidência e
segurança clínica, identidade visual) auditou o sistema com um Fact Pack comum,
isoladas umas das outras. Encontraram oito defeitos que a auditoria anterior não
tinha visto. **Todos foram verificados rodando o código, não inferidos.**

**Corrigido nesta rodada:**

1. **Campo de diagnóstico no Kit de Apoio.** `support_kits.neurodivergencia`
   guardava dado sensível de saúde de menor em texto livre — contra a ADR-003 e
   o cabeçalho de `accessibility.py`. Agravante encontrado pela TO: `pode_ver_aluno`
   libera o próprio usuário, então **a criança conseguia ler o próprio laudo**.
   Nenhuma lógica de negócio consumia o campo. Removido do modelo, do
   serializador e da gravação. Encontrado por **cinco autoridades independentes**.
2. **`dimensoes_atendidas()` produzia registro falso de adequação.** Computava
   sobre os tokens *declarados* na opção, não sobre o efeito. Medido: 4 de 4
   casos testados afirmavam uma dimensão com delta de tokens vazio. Como a escola
   usa esse campo como evidência de adaptação razoável (LBI art. 3º, III), que se
   afere pelo efeito concreto, isso era registro falso. Agora computa sobre o
   delta real, e a API expõe `respostas_sem_efeito[]` para a UI poder mostrar ao
   responsável o que ele declarou e não foi aplicado.
3. **Verbos acentuados nunca casavam.** `text_mining_pt.py` gravava `reconheca` e
   `esclareca` sem cedilha; o texto real vem acentuado e o regex jamais casava —
   verbos presentes na tabela caindo no default em silêncio. Corrigido
   normalizando acentuação nos dois lados (`_sem_acento`), o que fecha a classe
   inteira do problema em vez de remendar verbo a verbo. Verificado:
   "Reconheça…" passou de default para `BT1_lembrar`, "Esclareça…" para
   `BT2_entender`. Os 46/46 e 22/22 dos conjuntos rotulados continuam passando.
4. **`textos_longos: sim` apagava a letra de quem lê com esforço.** Combinado com
   `leitura: com_ajuda`, resolvia para `texto: so_figura` — a criança perdia
   prática de leitura por ter respondido com honestidade sobre fadiga. Cansaço com
   texto longo se trata **fatiando** (`passo_unico`), não removendo a letra. Quem
   realmente não lê chega a `so_figura` pelas perguntas `leitura` e
   `comunicacao_verbal`, que é onde essa decisão pertence. Apontado
   independentemente por psicopedagogia e terapia ocupacional.
5. **`uso_pesquisa` prometia anonimização inexistente.** A descrição afirmava ao
   responsável "dados sem identificação", e **nada no código desidentifica nada**.
   Pior: a constante nunca era lida por código de produção — quem marcava sim e
   quem marcava não recebiam tratamento idêntico. Somado a isso, pesquisa com
   menores exige CEP/CONEP (Res. CNS 466/2012 e 510/2016), TCLE do responsável e
   **TALE — assentimento da própria criança**, nenhum dos quais existe. A
   finalidade agora é `disponivel: False`: fica **visível e desabilitada** (sumir
   esconderia do responsável que ela existiu e quebraria a leitura dos
   `consent_events` já gravados), e `registrar()` recusa concedê-la venha o pedido
   de onde vier.

**Regressão coberta por** `tests/test_correcoes_conselho.py` (9 testes) e
`tests/test_fluxos_perfis.py::test_kit_nao_aceita_nem_devolve_diagnostico`.
Suíte do core: **201 passando**. Workers: 20 passando.

**Achado que NÃO foi corrigido nesta rodada, e é grande:** o motor de
acessibilidade quase não funciona. Medido rodando `resolver_tokens()` sobre as 33
opções do catálogo: **20 não mudam token nenhum**; `busca_estimulo` e
`linguagem_literal` são **100% inertes** (nenhuma resposta produz efeito); e 8
valores de token são **inalcançáveis** pelo questionário do responsável
(`estimulo: vivo`, `densidade: completa`, `movimento: completo`,
`som: sob_demanda`, `alvo_toque: normal`, `navegacao: livre`, `linguagem: livre`,
`entrada: texto`). A causa é estrutural: `TOKENS_PADRAO` nasce quase no extremo
protetivo e `_mais_conservador` nunca afrouxa. A correção nº 2 torna isso
**visível** ao responsável, mas não resolve — resolver exige redesenhar o
catálogo, decisão pedagógica que não cabe numa correção pontual.

**Trabalho de backend que o conselho identificou e ainda não foi feito:**
registro de aprovação no schema `Adaptation` (o princípio "o professor revisa e
aprova cada versão" **não existe em código** — busca por `aprov|approv|revis` no
satélite retorna zero ocorrências funcionais) · reclassificação Bloom/Simpson
sobre o texto **adaptado**, com reprovação quando o nível cai, **junto com**
transformar o `(default)` em estado bloqueante · versionamento de
`accessibility_profiles` (hoje `$set` sem histórico — sem isso não há
acompanhamento, metade do que o AEE exige) · expansão da tabela de verbos, que
falha em 8 de 9 enunciados brasileiros reais · campo `habilidade_bncc` para
tornar "preserva a habilidade" verificável por igualdade de string.

### ADR-002: LLM via API — ✅ DECIDIDO (híbrido, custo zero)
**Decisão:** time é formado por estudantes sem orçamento para custo recorrente
de API — descartadas todas as opções pagas (Claude, AWS Bedrock). `worker_adaptation.py`
usa uma cadeia de dois provedores, ambos gratuitos:
  1. **Gemma 4 12B (Unified) local, via Ollama** — modelo primário. Roda numa
     máquina dedicada do time (GPU 12GB VRAM, 32GB RAM, i7 9ª geração), custo
     zero, sem dependência de internet para inferência. Cabe em ~6-7GB de VRAM
     em quantização 4-bit (padrão Ollama), com folga para contexto. Variante
     "Unified" é encoder-free (multimodal nativo texto/imagem/áudio) — relevante
     porque a arquitetura de 3 formatos de saída (seção 5) inclui pictograma;
     abre caminho para o próprio modelo lidar com conteúdo visual no futuro sem
     trocar de modelo.
  2. **Gemini API (camada gratuita)** — fallback, quando a máquina local estiver
     indisponível ou sobrecarregada. Camada free tier do Google é permanente
     (não é trial), sem cartão de crédito, com limite de requisições/minuto e
     tokens/dia suficiente para o volume de um projeto acadêmico (poucas
     adaptações por demonstração, não tráfego de produção).
**Reforço de LGPD sobre a ordem primário/fallback (não é só custo):** rodar
localmente não é só mais barato — é o que mantém o conteúdo da atividade e os
tokens de acessibilidade da criança (`profile_tokens_used`) dentro da rede da
escola, nunca saindo para um servidor de terceiro. O fallback em nuvem
(Gemini, EUA) é uma transferência internacional de dado de menor, que exigiria
base legal própria (LGPD art. 33) — hoje isso ainda não é um risco ativo
porque `worker_adaptation.py` não está implementado (confirmado por auditoria
de código, não só pela documentação), mas vira um requisito real no dia em
que o fallback for codificado: no mínimo, o fallback não deve ser acionado
quando o conteúdo carrega token de acessibilidade identificável, ou precisa
de consentimento específico para essa transferência — decisão de design
ainda em aberto, registrada aqui para não ser esquecida quando o worker for
implementado.
**Descartado:** Claude (Anthropic) e AWS Bedrock — nenhum dos dois oferece
camada gratuita sustentável para uso contínuo, incompatível com o orçamento do
time. Gemma 4 27B/31B também descartados nesta máquina — não cabem nos 12GB de
VRAM disponíveis sem quantização agressiva (perda de qualidade) ou offload para
CPU (latência inviável para demo ao vivo).
**Pendente:** validar a saída do Gemma 4 12B com um conjunto de teste rotulado
(mesma disciplina de validação quantitativa da ADR-006) antes de considerar a
qualidade da adaptação aceitável para produção — não assumir qualidade sem medir.
**Motivo:** custo zero é restrição inegociável do time (sem verba), não uma
preferência estilística — a mesma razão que já motivou evitar LLM na
classificação PT-BR (ADR-006) aqui se aplica à escolha do provedor.

### ADR-003: Sem diagnóstico médico
**Decisão:** Tokens de comportamento observável, nunca CID/DSM.
**Motivo:** LGPD dados sensíveis de menores + decisão ética deliberada.

### ADR-004: Federated Learning
**Decisão:** Flower FedAvg — dados ficam na escola, só pesos trafegam.
**Motivo:** LGPD + Privacy by Design + cobre Computação Distribuída.

### ADR-005: UI diferenciada por neurologia
**Decisão:** 3 temas visuais distintos no Flutter, baseados em estudos.
**Fontes:** Ben-Sasson 2009 (TEA) · Frontiers 2025 (TDAH) · BDA 2025 + Zorzi 2012 (Dislexia).

---

## 13. O que NÃO fazer

- ❌ Modificar `cognikids-backend/` a partir do trabalho do satélite (mudanças no core seguem seu próprio fluxo, à parte)
- ❌ Importar código Python do core dentro do satélite (ou vice-versa) — só HTTP
- ❌ Usar dados reais de crianças — usar DSB2019 (público) nesta fase
- ❌ Hardcodar chaves, senhas ou tokens no código
- ❌ Usar neon, animações ou movimento na interface do aluno TEA
- ❌ Armazenar diagnóstico médico — apenas tokens comportamentais
- ❌ Justificar texto na interface do aluno com dislexia
- ❌ Escrever no banco MongoDB do core
- ❌ Adicionar funcionalidades fora do escopo sem avaliar impacto no prazo

---

## 14. Critérios de aceite — a demo está pronta quando

- [ ] Professor insere atividade → 3 versões geradas em < 10 segundos
- [ ] Aluno abre app e encontra atividade no formato correto para seu perfil
- [ ] Pais visualizam histórico + explicação da adaptação em linguagem simples
- [ ] Stress test: 100 sessões paralelas sem degradar o core
- [ ] Grafo gera recomendação visível no app
- [ ] Card SHAP explicável aparece na interface do professor
- [x] Experimento FL: centralizado vs. federado com resultado quantificado —
      ver `cognikids-adapt/federated/relatorio_fl.md` (0,747 vs. 0,747, empate)

---

*Criado: Agosto de 2026*
*Apresentação prevista: Novembro / Dezembro de 2026*
*Repositório: CogniKids (monorepo) — `cognikids-backend/` (core, em manutenção ativa) + `cognikids-adapt/` (novo, a construir), dois microserviços independentes*
