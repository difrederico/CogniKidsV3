# Decisões Arquiteturais (ADRs) — CogniKids

> Arquivo de referência detalhada. Extraído do `CLAUDE.md` raiz na refatoração
> de eficiência de tokens (as regras ativas resumidas ficam na raiz; aqui está
> a justificativa completa, achados de auditoria e histórico de correções).
> Reordenado numericamente (ADR-001 → ADR-011) para navegação; nenhum
> conteúdo foi removido em relação à versão anterior do `CLAUDE.md`.

---

## ADR-001: Monorepo com dois microserviços

**Decisão:** Código novo do satélite (`cognikids-adapt/`) vive no mesmo
repositório git do core (`cognikids-backend/`), mas roda como serviço
independente em runtime — processo, container e banco próprios. Comunicação
só via HTTP (JWT + GET read-only), nunca por import de código.

**Motivo:** Simplifica o desenvolvimento em equipe pequena e a apresentação
(um só checkout), sem abrir mão do isolamento que protege o sistema core
já validado de risco de regressão.

### Contexto — o core (`cognikids-backend/`)

O core mora neste mesmo repositório como serviço próprio (Flask + MongoDB).
Está em manutenção ativa — correções críticas, autorização e acessibilidade
seguem evoluindo diretamente nele — mas mantém seu papel de **serviço
independente**: roda no seu próprio processo/container, com seu próprio
banco, e nunca deve depender do satélite para funcionar.

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

**O que o core NÃO faz (e o satélite resolve):** o perfil de acessibilidade
existe mas não é usado para adaptar conteúdo pedagógico real. O professor não
tem como enviar uma atividade e receber versões adaptadas automaticamente
para cada criança.

### Estrutura completa do monorepo

```
CogniKids/                      ← este repositório (monorepo)
├── cognikids-backend/          ← serviço CORE (Flask, existente, em manutenção ativa)
├── cognikids-front-end/        ← front-end core (Streamlit)
├── cognikids-pulseira-m5stack/ ← firmware da pulseira
├── cognikids-adapt/            ← serviço satélite
│   ├── gateway/                 ← FastAPI :8001
│   ├── workers/                 ← Workers RabbitMQ
│   │   ├── worker_analysis.py      ← Text Mining + Bloom's Taxonomy
│   │   ├── worker_profile.py       ← lê perfil do core (read-only)
│   │   └── worker_adaptation.py    ← chama LLM, gera versão adaptada (STUB)
│   ├── pipeline/                 ← PySpark ETL + XGBoost + SHAP
│   ├── graph/                    ← NetworkX (grafo de conhecimento)
│   ├── federated/                 ← Flower (Federated Learning)
│   └── scripts/                   ← emulador de carga, testes de contrato
├── mobile/                     ← Flutter app (3 perfis)
├── docker-compose.yml          ← orquestra os dois serviços + infra (RabbitMQ, Mongo satélite)
├── .env.example
└── CLAUDE.md                   ← briefing enxuto (este arquivo é a referência detalhada)
```

### Regras da fronteira — NUNCA violar
1. O satélite **nunca escreve** no banco MongoDB do core
2. O satélite **nunca importa** código Python do core (nada de `from cognikids_backend...`) — comunicação só via rede
3. O core **continua funcionando** mesmo que o satélite esteja offline (containers/processos independentes)
4. Integração apenas por: JWT compartilhado + GET read-only no core, chamado via HTTP
5. Estar no mesmo repositório não é desculpa para acoplar — se o satélite precisa de algo do core, é uma chamada HTTP, nunca um import ou um caminho de arquivo compartilhado

---

## ADR-002: LLM via API — ✅ DECIDIDO (híbrido, custo zero)

**Decisão:** time é formado por estudantes sem orçamento para custo recorrente
de API — descartadas todas as opções pagas (Claude, AWS Bedrock). `worker_adaptation.py`
usa uma cadeia de dois provedores, ambos gratuitos:

1. **Gemma 4 12B (Unified) local, via Ollama** — modelo primário. Roda numa
   máquina dedicada do time (GPU 12GB VRAM, 32GB RAM, i7 9ª geração), custo
   zero, sem dependência de internet para inferência. Cabe em ~6-7GB de VRAM
   em quantização 4-bit (padrão Ollama), com folga para contexto. Variante
   "Unified" é encoder-free (multimodal nativo texto/imagem/áudio) — relevante
   porque a arquitetura de 3 formatos de saída (texto/áudio/pictograma) inclui
   pictograma; abre caminho para o próprio modelo lidar com conteúdo visual no
   futuro sem trocar de modelo.
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

---

## ADR-003: Sem diagnóstico médico

**Decisão:** Tokens de comportamento observável, nunca CID/DSM.
**Motivo:** LGPD dados sensíveis de menores + decisão ética deliberada.

---

## ADR-004: Federated Learning

**Decisão:** Flower FedAvg — dados ficam na escola, só pesos trafegam.
**Motivo:** LGPD + Privacy by Design + cobre Computação Distribuída.

---

## ADR-005: UI diferenciada por neurologia

**Decisão:** 3 temas visuais distintos no Flutter, baseados em estudos.
**Fontes:** Ben-Sasson 2009 (TEA) · Frontiers 2025 (TDAH) · BDA 2025 + Zorzi 2012 (Dislexia).

### Adaptação por perfil (exemplos ilustrativos)

| Aluno | Condição | O que muda na atividade |
|-------|----------|------------------------|
| Lucas (exemplo) | TEA grau 1 | Passo a passo numerado · áudio · exemplo cotidiano · fonte ampliada · fundo #F5F0E8 · ZERO animações |
| Sofia (exemplo) | TDAH | Chunks ≤3 linhas · checklist dopaminérgico · negrito estratégico · progresso visível |
| Pedro (exemplo) | Dislexia | Atkinson Hyperlegible · line-height 2.0 · letter-spacing 0.08em · fundo #FEFAE0 · texto à esquerda |

Os perfis reais vêm dos tokens configurados no core pelos pais. Esses exemplos
são apenas ilustrativos para guiar o desenvolvimento.

---

## ADR-006: Text Mining em PT-BR sobre datasets em inglês — ✅ DECIDIDO

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
>
> **Busca de dataset brasileiro para expandir a tabela (verificado, não
> especulado):** ENEM tem datasets públicos reais (Kaggle, GitHub, ~4.000
> questões classificadas), mas sofre do mesmo problema de gênero do dataset em
> inglês — é prova de vestibular, não comando de caderno de fundamental I. A
> **Matriz de Referência do SAEB** (`download.inep.gov.br`, busca "Matriz de
> Referência SAEB Língua Portuguesa/Matemática" por ano escolar) é a melhor
> âncora oficial: descritores verbo+habilidade específicos do 5º ano (ex.: D1
> "Localizar informações explícitas", D3 "Inferir o sentido de uma palavra").
> Não é um dataset pronto de comandos operacionais ("circule", "ligue") — é
> vocabulário de **habilidade cognitiva**, útil para justificar/citar o nível
> de cada verbo novo, não para preencher a tabela automaticamente. Simulados
> de professores para SAEB 5º ano (PEBSP, Tudo Sala de Aula, Atividade
> Pedagógica) têm o registro operacional que falta, mas são PDFs soltos sem
> padronização e com licença incerta para redistribuição — servem para
> **extrair e validar vocabulário**, não para copiar texto ao repositório. Não
> existe, publicamente, um dataset já estruturado e rotulado de "comando de
> atividade escolar brasileira classificado por nível de Bloom" — a expansão
> da tabela continua exigindo julgamento pedagógico profissional.

---

## ADR-007: Ampliação teórica — Simpson, Krathwohl e UDL 3.0 — ✅ DECIDIDO

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
  a arquitetura de 3 formatos de saída e o princípio "adaptar formato, nunca
  conteúdo".

**Motivo:** Bloom's isolado só cobre 1 de 3 domínios clássicos da aprendizagem;
completar o quadro fortalece a fundamentação acadêmica do projeto e
identifica, via Simpson's, um sinal (demanda motora) hoje ignorado — relevante
porque parte do público do CogniKids tem dificuldade de coordenação motora
associada ao TEA/TDAH.

### Três Domínios da Aprendizagem + UDL 3.0 (fundamentação teórica ampliada)

Descoberta no protótipo do Núcleo 1: a Taxonomia de Bloom cobre só o domínio
**cognitivo** (pensar). Existem dois outros domínios clássicos da educação, e
um framework de design mais recente que amarra os três — juntos, dão ao
projeto uma base teórica mais forte do que só Bloom's isolado.

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

UDL 3.0 é citado como a fundamentação teórica do **princípio pedagógico
central** (adaptar formato, nunca conteúdo) e da arquitetura de 3 formatos —
não como algo a implementar em código, e sim como referência acadêmica que
justifica por que o sistema é desenhado assim.

---

## ADR-008: Revogação de consentimento com efeito real sobre o dado — ✅ DECIDIDO

**Contexto:** auditoria de conformidade (dois revisores independentes, um por
serviço) encontrou que revogar consentimento só mudava uma flag no
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

---

## ADR-009: Consentimento e retenção no satélite — ✅ PARCIALMENTE FECHADO

**Contexto:** a auditoria de LGPD do satélite (dois revisores) encontrou dois
problemas ativos: (1) o gateway aceitava e gravava telemetria de qualquer
aluno autenticado, sem checar se o responsável autorizou o uso do app —
autenticação (é o próprio aluno) e consentimento (os pais autorizaram) são
coisas diferentes, e só a primeira era checada; (2) nenhuma coleção sensível
do satélite (`curriculum_jobs`, `telemetry_events`, `student_graphs`) tinha
expiração — tudo persistia indefinidamente.

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
próprio broker RabbitMQ e do MongoDB satélite continuavam fora do escopo
desta correção específica — mudanças de infraestrutura, fechadas depois na
ADR-010.

### LGPD — Encarregado de Dados e Retenção (estado consolidado)

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
`telemetry_events` do satélite têm TTL de 180 dias (acima). `registros_iot`
e `alerts` do core são eliminados no momento da revogação de consentimento,
não por tempo (ADR-008). Ainda sem expiração: `student_graphs` do satélite
(deliberado — é estado atual do aluno, não log) e o perfil de acessibilidade
do core (fica até a exclusão de conta). Nenhuma coleção sensível deveria
reter dado indefinidamente sem justificativa — o que ainda não tem
justificativa nem correção é registrado aqui, não escondido.

---

## ADR-010: Correções críticas de segurança — ✅ PARCIALMENTE FECHADO

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
   o `.env` (`RABBITMQ_USER`/`RABBITMQ_PASS`).

**Regressão coberta por** `cognikids-backend/tests/test_seguranca_producao.py`
(5 testes) e `cognikids-adapt/gateway/tests/test_curriculum_autorizacao.py` +
`test_curriculum_rotas_seguranca.py` (12 testes). São testes que **encenam o
ataque** e quebram o build se ele voltar a funcionar — diferente do resto da
suíte, que verifica se a funcionalidade funciona. Validação adicional ao vivo
contra os serviços reais em Docker: `scripts/verificar_seguranca_ao_vivo.py`
(12 ataques encenados, todos bloqueados — inclui a checagem de porta pela
rede, que só faz sentido contra portas de fato publicadas).

**O que fica aberto, dito com honestidade (não é lista genérica — foi
verificado no código):**
- **Auth no Mongo do satélite ainda não foi habilitada de fato** —
  `MONGO_INITDB_ROOT_USERNAME` só tem efeito em volume vazio; com
  `mongo-adapt-data` já populado ela é ignorada em silêncio. Isso continua
  exigindo ação manual (`db.createUser()` ou recriar o volume — passo a
  passo agora documentado em `docker-compose.yml`, serviço `mongo-adapt`) —
  não dá para automatizar sem risco de apagar dado real do satélite sem
  pedir. **O que mudou nesta rodada:** a falta de auth deixou de ficar
  "parecendo protegida" em silêncio — `scripts/verificar_seguranca_ao_vivo.py`
  ganhou o Ataque 5, que conecta no Mongo satélite sem credenciais e
  **falha o build** se a conexão tiver sucesso (hoje falha de propósito,
  documentando o estado real, até alguém aplicar a correção manual).
- **Modelo de risco de crise sem validação real.** `scripts/utils/train_model.py`
  gera dado sintético com ruído de 25% e **8% dos rótulos invertidos de
  propósito**, com faixas de `ATIVO` e `TENSO` quase idênticas ("para baixar
  acurácia") e alvo declarado de `~75-82%`. É honesto como artefato de demo e
  indefensável como classificador de segurança: `LIMIAR_BPM_ALTO = 130` marca
  severidade máxima, e 130 bpm é uma criança de 7 anos no recreio. **Nenhum
  uso com criança real enquanto isso não for refeito.** Não inventamos um
  limiar novo aqui — decisão clínica que não cabe a este time — mas o aviso
  deixou de ser só comentário: `LIMIAR_BPM_ALTO`/`LIMIAR_GSR_ALTO` viraram
  configuráveis por ambiente (`alert_model.py`, espelhados em
  `alert_monitor.py`, mesmo padrão de `.env.example`), e todo alerta agora
  grava `modelo_validado` (`False` por padrão, só vira `True` quando alguém
  validar conscientemente e mudar `MODELO_RISCO_VALIDADO=true`). O campo
  aparece na própria tela do professor (`GET /api/teachers/crisis_alerts`),
  não só em log — quem lê o alerta vê que a severidade ainda não é
  clinicamente confiável. `test_limiares_sao_os_mesmos_dos_dois_lados` e
  `test_consumidor_mantem_a_mesma_flag_do_modelo_de_alertas`
  (`tests/test_pipeline_iot.py`) travam a duplicação entre os dois arquivos
  no mesmo valor, não só nos mesmos casos de teste.
- Sem TLS (o core roda no servidor de desenvolvimento do Werkzeug), sem
  criptografia em repouso, sem log de acesso de leitura, sem recuperação de
  senha, sem endpoint de portabilidade ou exclusão de conta, sem rate limit,
  sem verificação de e-mail.

**Feito depois (rodada 4): revogação em cascata core→satélite.** ADR-008 já
apagava `registros_iot`/`alerts` no core quando `coleta_biometrica` é
revogada, mas documentava a lacuna: o satélite deriva do mesmo dado
comportamental o grafo de conhecimento (`student_graphs`) e a telemetria
bruta (`telemetry_events`), sem nenhum mecanismo de cascata entre os dois
serviços. Esta é a **primeira chamada core→satélite** do projeto (até aqui
só satélite→core existia, via `core_client.py`).

- **Core**: `Utils/satellite_client.py` (novo) — `notificar_revogacao_biometrica`,
  chamada de `consent_model._eliminar_dado_biometrico`. Emite um JWT de
  serviço próprio (claim `{"servico": "core"}`, 5 min de vida, assinado com
  o mesmo `SECRET_KEY`/`CORE_JWT_SECRET` compartilhado) e chama
  `DELETE {SATELLITE_BASE_URL}/v1/students/{aluno_id}/behavioral-data`.
  **Best-effort por desenho, não por acidente**: qualquer falha (satélite
  fora do ar, timeout, DNS) vira aviso em log, nunca exceção — respeita a
  regra de fronteira do CLAUDE.md §2 ("o core continua funcionando mesmo
  que o satélite esteja offline"). `SATELLITE_BASE_URL` é opcional, com
  default `http://localhost:8001`.
- **Satélite**: nova rota `DELETE /v1/students/{aluno_id}/behavioral-data`
  (`api/v1/students.py`, novo), protegida por uma dependência nova,
  `servico_core_autenticado` (`core/security.py`) — **não** reaproveita
  `usuario_autenticado`: um JWT de professor/aluno/responsável válido é
  explicitamente rejeitado (403), só o claim `servico=core` passa. Serviço
  `student_data_service.purgar_dados_comportamentais` apaga
  `student_graphs` (filtro `aluno_id`) e `telemetry_events` (filtro
  `student_id` — formatos diferentes por desenho, não inconsistência).
  `curriculum_jobs` fica **fora** desta cascata de propósito: não é
  derivado especificamente de `coleta_biometrica`, é conteúdo pedagógico
  ligado a `compartilhar_escola`/`uso_app` — apagá-lo é decisão de produto
  separada, não coberta aqui.
- Coberto por 4 testes novos em `tests/test_students_rotas.py` no satélite
  (purga bem-sucedida, campo de filtro correto por coleção, JWT humano
  rejeitado, sem token rejeitado) e 2 no core em `test_consentimento.py`
  (`test_revogacao_notifica_o_satelite`,
  `test_revogacao_nao_falha_se_satelite_estiver_fora_do_ar` — esta última
  encena exatamente o cenário que a regra de fronteira exige suportar).
  Suíte completa: core 221 testes, satélite 49, todos passando.

**Feito depois (rodada 3): confirmação por terceiro no `link-child`.**
`POST /api/parents/link-child` não vincula mais direto — cria um pedido
pendente em `vinculos_pendentes` (`app/Models/vinculo_model.py`, novo) e só
popula `users.filhos_ids` quando um professor de uma turma do aluno confirma
em `PUT /api/teachers/link-requests/<id>/confirm` (novo, em
`teacher_controller.py`; simétrico `.../reject`). Fila do professor em
`GET /api/teachers/link-requests/pending`, filtrada por
`alunos_do_professor` — professor de outra turma não vê nem confirma pedido
alheio (404, não 403, mesma filosofia das outras correções de IDOR).
Responsável acompanha o próprio pedido em `GET /api/parents/link-requests`.
Idempotente por desenho, mesmo padrão de `curriculum_service.aprovar_adaptacao`
no satélite (filtro exige `status: pendente`; decidir duas vezes não
sobrescreve a primeira decisão). Coberto por 4 testes novos em
`test_fluxos_perfis.py::TestFluxoResponsavel` (pendência → confirmação,
recusa, idempotência do pedido, fila do professor) e 3 testes de ataque em
`test_seguranca_producao.py` (desconhecido não ganha acesso só vinculando,
professor sem a turma não confirma nem vê pedido alheio).

Achado lateral, corrigido na mesma rodada: `accessibility_profile_model.py`
e `vinculo_model.py` ordenavam histórico só por timestamp
(`sort('data_hora', -1)`) — duas gravações no mesmo milissegundo empatam, e
o Mongo não garante ordem estável em empate. Descoberto porque
`test_mudanca_registra_de_e_para` passava isolado e falhava na suíte
completa (contra Mongo real, onde o empate realmente acontece). Corrigido
com desempate por `_id` (monotônico por inserção) nos dois modelos.
**Mesmo padrão existe, não corrigido, em** `alert_model.py`,
`consent_model.py` e `break_request_model.py` — candidato a rodada futura,
fora do escopo desta correção.

Suíte completa do core: **214 testes, todos passando** (era 208 antes desta
rodada).

### Nota histórica — chave hardcoded (Sprint 0)

O serviço core tinha `TEMP_API_KEY_123` hardcoded no código; corrigido em
commit anterior à formalização desta ADR (nenhuma chave hardcoded encontrada
na auditoria, só placeholders em `.env.example`). Nunca repetir esse padrão
em nenhum dos dois serviços.

---

## ADR-011: Correções do conselho de especialistas — ✅ APLICADAS (rodada 1)

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
6. **Precedência comparava resposta contra o padrão, não entre respostas.**
   `resolver_tokens()` comparava cada resposta isolada contra `TOKENS_PADRAO`
   (já quase no extremo protetivo), então uma resposta legítima pedindo algo
   menos protetivo nunca vencia — mesmo sem nenhuma outra resposta pedindo mais
   proteção. 3 casos ficavam sem efeito por essa causa (`sensibilidade_sensorial:
   nao`, `busca_estimulo: sim`, `atencao: nao`). Corrigido: as respostas se
   conciliam entre si primeiro; o padrão só preenche o que ninguém respondeu.
   `respostas_sem_efeito()` também precisou de correção de semântica equivalente
   (comparação "leave-one-out" contra o conjunto completo, não isolada contra o
   padrão) para não ficar inconsistente com a correção de precedência.

**Regressão coberta por** `tests/test_correcoes_conselho.py` (10 testes) e
`tests/test_fluxos_perfis.py::test_kit_nao_aceita_nem_devolve_diagnostico`.
Suíte do core: **202 passando**. Workers: 20 passando. Gateway do satélite:
35 passando.

**Achado que NÃO foi corrigido nesta rodada, e é grande:** o motor de
acessibilidade quase não funciona mesmo após a correção nº 6. Medido rodando
`resolver_tokens()` sobre as 33 opções do catálogo: **17 ainda não mudam token
nenhum** (9 porque a opção legitimamente não declara token, 8 porque pedem
exatamente o valor que já é o padrão — nenhum dos dois é bug); `busca_estimulo`
e `linguagem_literal` continuam parcialmente inertes; e 6 valores de token
ainda são **inalcançáveis** pelo questionário do responsável (`movimento:
completo`, `som: sob_demanda`, `alvo_toque: normal`, `navegacao: livre`,
`linguagem: livre`, `entrada: texto`). A correção nº 2 torna isso **visível**
ao responsável, mas resolver por completo exige redesenhar o catálogo, decisão
pedagógica que não cabe numa correção pontual.

**Trabalho de backend que o conselho identificou e ainda não foi feito:**
reclassificação Bloom/Simpson sobre o texto **adaptado**, com reprovação
quando o nível cai, **junto com** transformar o `(default)` em estado
bloqueante · expansão da tabela de verbos, que falha em 8 de 9 enunciados
brasileiros reais (ver nota de dataset na ADR-006).

**Feito depois (rodada 2 do backend):** registro de aprovação no schema
`Adaptation`. `Adaptation` ganhou `adaptation_id`, `approved` (bool),
`approved_by` e `approved_at` (`cognikids-adapt/gateway/app/schemas/curriculum.py`);
nova rota `PUT /v1/curriculum/jobs/{job_id}/adaptations/{adaptation_id}/approve`
(`gateway/app/api/v1/curriculum.py`), só para `professor_autenticado` **e**
dono do job (`curriculum_service.eh_dono_do_job` — o aluno citado no job lê o
job mas não se autoaprova), idempotente por desenho (aprovar duas vezes não
sobrescreve `approved_by`/`approved_at` da primeira vez, mesmo padrão de
`gallery_model.approve_creation` no core). 404, não 403, para quem não é
dono — mesma filosofia de `consultar_job`. Coberto por
`tests/test_curriculum_rotas_seguranca.py` (5 testes novos: aprovação,
idempotência, professor alheio, adaptation_id inexistente, job inexistente)
e `tests/test_curriculum_contract.py`. Ainda **não implementado**: o worker
que de fato gera as `Adaptation` (`worker_adaptation.py` continua stub —
depende da integração com o LLM, ADR-002), então a rota de aprovação hoje só
tem o que aprovar em testes, não em produção.

Também nesta rodada: **versionamento de `accessibility_profiles`**. Antes,
`salvar_respostas` e `salvar_ajustes_crianca` (`accessibility_profile_model.py`)
só faziam `$set` — o professor não tinha como ver que o perfil mudou nem o
que mudou, e a AEE exige acompanhamento disso. Agora cada mudança real (não
cada chamada — responder o mesmo não gera evento) grava um evento imutável
em `accessibility_profile_events` no formato `{campo: {de, para}}`, mesmo
padrão de `consent_model`/`consent_events`. Nova rota
`GET /api/accessibility/<aluno_id>/history` (mesma permissão de leitura do
perfil, `pode_ver_aluno`), retornando o rastro mais recente primeiro. Coberto
por `tests/test_acessibilidade.py::TestHistoricoDoPerfil` (6 testes:
primeiro evento, de/para numa mudança real, idempotência de responder o
mesmo, ajuste da criança também gera evento com autor correto, leitura por
professor da turma, e bloqueio de responsável sem vínculo). Suíte completa
do core: 40 testes em `test_acessibilidade.py`, todos passando.

Também nesta rodada: **campo `habilidade_bncc`**. `CurriculumAdaptRequest`
passa a exigir o código da habilidade BNCC que a atividade original endereça
(ex.: `"EF03LP01"`) — sem isso não havia como verificar depois se uma versão
adaptada preservou o objetivo pedagógico ou virou modificação disfarçada de
acomodação. O campo flui pelo pipeline inteiro sem tocar nos workers
existentes (`worker_analysis.py`/`worker_profile.py` fazem passthrough de
dict, `{**job, "analysis": analise}`): fica gravado em `curriculum_jobs`,
publicado na fila `analysis`, e exposto em `CurriculumJobStatus`. `Adaptation`
também ganhou `habilidade_bncc` (o que a versão adaptada afirma preservar) e
`curriculum_service.preserva_habilidade(esperada, obtida)` faz a verificação
— igualdade de string normalizada (espaço/caixa), deliberadamente ingênua:
dá sinal automático e auditável, não substitui julgamento do professor.
Coberto por `TestPreservaHabilidade` (3 testes) em
`tests/test_curriculum_contract.py`. Mesma ressalva do item anterior: **ainda
não usado por nada em produção**, porque `worker_adaptation.py` continua
stub — a verificação existe e está testada, mas só passa a rodar de verdade
quando o worker gerar `Adaptation` de fato. Suíte completa do gateway: 45
testes, todos passando.
