# Datasets, ETL e Ambiente de Data Science — CogniKids

> Arquivo de referência detalhada. Extraído do `CLAUDE.md` raiz na refatoração
> de eficiência de tokens. Consultar sob demanda ao trabalhar em notebooks,
> pipeline PySpark, ou ao reobter datasets brutos.

---

## Arcabouço Multi-Dataset + Grafo de Conhecimento (fonte: Documento de Arquitetura V2)

A mineração e o Grafo de Conhecimento não usam dado médico real — são calibrados
com datasets públicos numa fase offline, e depois realimentados continuamente
pelo uso real do aluno (fase online). Duas fases, um único grafo.

### Fase 1 — Calibração offline (datasets públicos)

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
> Comportamental em Interação".

### Fase 2 — Loop de feedback online (uso real, sem dado médico)

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

### Definição concreta de nós e arestas (Grafo de Conhecimento por criança)

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
  core que não produz esse dado, os datasets públicos de calibração também não
  o oferecem. Esse sinal só existirá com uso real do satélite via
  `TelemetryEvent` tipo `abandoned`/`hint_requested` — não dá pra calibrar essa
  parte na fase offline, só a fase online resolve isso.
- **Refinamento contínuo**: a cada atividade adaptada que a criança usa no
  satélite, o `TelemetryEvent` gerado atualiza o peso das arestas — o grafo
  fica mais preciso a cada sessão. O core hoje **não** produz esse dado fino
  (`challenge_model.py` só registra `completed_at`, sem acerto/latência/tentativas)
  — esse sinal é gerado inteiramente pelo satélite.
- **Uso na adaptação**: o motor de adaptação consulta o grafo antes de chamar
  o LLM — é o grafo que decide **o quê** adaptar (ex: "está fraco em
  causa-efeito visual, forte em sequência auditiva"), o LLM só decide **como**
  expressar isso em texto/áudio/pictograma. Isso é o que torna a adaptação
  explicável (`xai_explanation` no contrato de API).

---

## Stack de Data & ML

- **Datasets:** CommonLit Readability Prize · Educational Bloom's Taxonomy ·
  ASSISTments / EdNet · DSB2019 (PBS KIDS) / Jo Wilder PSP Raw — ver tabela
  acima para o papel de cada um.
- **Taxonomias sem dataset (classificação por regra):** Simpson's Taxonomy
  (domínio psicomotor) · Krathwohl's Taxonomy (domínio afetivo, ponte com IoT)
  · UDL 3.0 (framework de design, não classificador) — ver ADR-007.
- **ETL:** PySpark 3.5 — sobre os datasets acima (público, sem dado médico real).
- **Modelo:** XGBoost + SHAP (previsão de risco de frustração/fadiga, calibrado
  com ASSISTments 2009 — ver ADR-011 sobre o modelo *diferente* de crise
  biométrica, que não tem validação real).
- **Grafos:** NetworkX (Grafo de Conhecimento: aluno + conceitos + formatos,
  arestas calibradas com ASSISTments/EdNet e realimentadas pelo uso real).
- **FL:** Flower (FedAvg — privacidade das crianças).
- **Mobile:** Flutter 3.x + Riverpod, 3 perfis (Professor/Pais/Aluno, temas
  visuais distintos por neurologia), adaptação de dificuldade client-side
  offline.

---

## Nota de infraestrutura — PySpark no Windows

PySpark exige Java (JVM) — não é uma biblioteca Python pura, é uma API que se
comunica com o motor Spark (Scala/JVM) via Py4J. Sem JDK instalado,
`import pyspark` funciona mas qualquer operação real falha. JDK 17 (Microsoft
Build of OpenJDK) instalado na máquina de desenvolvimento para viabilizar isso.

No Windows, também é necessário setar `PYSPARK_PYTHON` explicitamente para o
caminho completo do `python.exe` — sem isso, o processo worker que o Spark
abre é interceptado pelo stub da Microsoft Store e a conexão do worker com o
driver expira (erro real encontrado e corrigido em sessão de desenvolvimento,
não hipotético).
