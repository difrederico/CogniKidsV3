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

**O sistema original foi publicado e apresentado:**
- 📄 Artigo publicado no SBCUP 2026 (Simpósio Brasileiro de Computação Ubíqua e Pervasiva — CSBC)
- 🏆 3º Melhor Artigo do congresso
- 📅 Apresentação: 21 de julho de 2026
- 🏫 Instituição: SENAI FATESG — Tecnologia em Inteligência Artificial

**Equipe:**
- Frederico Lemes Rosa — responsável técnico (AI Analyst, NIAA/SENAI FATESG)
- Maria Clara Ribeiro Di Bragança — apresentará o projeto do 3º período (nov/dez 2026)

---

## 2. O que o sistema legado (SBCUP) já tem

O repositório legado existe separado e está **congelado** — não será modificado
neste projeto, exceto pelo item de higiene descrito no Sprint 0.

```
cognikids-backend/  (Flask + MongoDB — REPOSITÓRIO LEGADO)
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
└── cognikids-frontend/  (Streamlit — dívida técnica: duplicado)
```

**O que o legado faz hoje:**
- Recebe dados biométricos da pulseira (BPM + GSR) via MQTT → Redis
- Classifica risco de crise com Random Forest (dados sintéticos)
- Gerencia perfis de acessibilidade configurados pelos pais
- Controla notas, desafios, galeria, fórum, agenda, Q&A
- Implementa consentimento LGPD com revogação imediata
- Emite alertas em tempo real para a professora

**O que o legado NÃO faz (e este projeto resolve):**
O perfil de acessibilidade existe mas não é usado para adaptar conteúdo
pedagógico real. O professor não tem como enviar uma atividade e receber
versões adaptadas automaticamente para cada criança. Este projeto fecha
esse ciclo.

---

## 3. O que ESTE repositório vai construir

Este repositório (CogniKidsV3) é o **sistema satélite** — completamente novo,
desenvolvido do zero neste semestre, sem tocar no legado.

**O módulo central é o Motor de Adaptação Curricular:**

```
Professor insere atividade (texto livre ou banco)
→ Gateway FastAPI :8001  [A CRIAR]
→ RabbitMQ               [A CRIAR]
→ Worker de análise: Text Mining (CommonLit + Bloom's Taxonomy)  [A CRIAR]
→ Worker de perfil: lê tokens do legado (read-only)  [A CRIAR]
→ Worker de adaptação: LLM gera versão adaptada por criança  [A CRIAR]
→ Professor revisa e aprova
→ Atividade chega no app do aluno no formato ideal  [A CRIAR]
→ Logs de interação → realimentam Data Mining  [A CRIAR]
```

**Tudo neste repositório será criado do zero durante o semestre.**
Hoje o repositório está vazio — ou contém apenas arquivos iniciais.

---

## 4. Arquitetura do Satélite (a construir)

```
CogniKidsV3/                   ← ESTE REPOSITÓRIO (tudo a criar)
├── gateway/                   ← FastAPI :8001
├── workers/                   ← Workers RabbitMQ
│   ├── worker_analysis.py     ← Text Mining + Bloom's Taxonomy
│   ├── worker_profile.py      ← lê perfil do legado (read-only)
│   └── worker_adaptation.py   ← chama LLM, gera versão adaptada
├── pipeline/                  ← PySpark ETL + XGBoost + SHAP
├── graph/                     ← NetworkX (grafo de conhecimento)
├── federated/                 ← Flower (Federated Learning)
├── mobile/                    ← Flutter app (3 perfis)
├── scripts/                   ← emulador de carga, testes de contrato
├── docker-compose.yml
├── .env.example
└── CLAUDE.md                  ← este arquivo
```

### Regras da fronteira — NUNCA violar
1. O satélite **nunca escreve** no banco MongoDB do legado
2. O satélite **nunca importa** código do legado
3. O legado **continua funcionando** mesmo que o satélite esteja offline
4. Integração apenas por: JWT compartilhado + GET read-only no legado

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

Os perfis reais vêm dos tokens configurados no legado pelos pais.
Esses exemplos são apenas ilustrativos para guiar o desenvolvimento.

---

## 6. Stack Tecnológica (a implementar)

### Backend Satélite
- **Gateway:** FastAPI :8001 + Pydantic v2 + async/await
- **Mensageria:** RabbitMQ (exchange: cognikids, filas: analysis, profile, adaptation)
- **Banco:** MongoDB TimeSeries :27018 (separado do legado :27017)
- **LLM:** Google Gemini Flash 1.5 (fallback: Claude Haiku)
- **Auth:** JWT HS256 — mesmo SECRET_KEY do legado (via variável de ambiente)

### Data & ML
- **ETL:** PySpark 3.5 — dataset DSB2019 (PBS KIDS, 11.3M registros, público)
- **Modelo:** XGBoost + SHAP (previsão de risco de frustração/fadiga)
- **Grafos:** NetworkX (grafo de trilhas + Rede de Cuidado)
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
    student_id: str        # ID do aluno no legado
    activity_id: str       # ID da atividade adaptada
    session_id: str        # UUID da sessão
    event_type: str        # step_completed | audio_played | abandoned | hint_requested
    step_number: int | None
    duration_ms: int       # tempo no passo atual
    timestamp: datetime    # UTC
    metadata: dict         # dados extras sem schema fixo
```

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

## 9. Variáveis de Ambiente (.env.example a criar)

```bash
# Legado (apenas leitura)
LEGACY_MONGO_URI=mongodb://localhost:27017/cognikids
LEGACY_JWT_SECRET=<mesmo secret do Flask legado>

# Satélite (novo)
SATELLITE_MONGO_URI=mongodb://localhost:27018/cognikids_satellite
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
RABBITMQ_EXCHANGE=cognikids

# LLM
GEMINI_API_KEY=<sua chave Gemini>

# Gateway
GATEWAY_PORT=8001
GATEWAY_HOST=0.0.0.0
```

> ⚠️ O repositório legado tinha `TEMP_API_KEY_123` hardcoded no código.
> Sprint 0 corrige isso. Nunca repetir esse padrão neste repositório.

---

## 10. Roadmap de Sprints

### Sprint 0 — Higiene e estrutura (Ago · sem 1) ← COMEÇAR AQUI
- [ ] Criar estrutura de pastas conforme seção 4
- [ ] docker-compose.yml (gateway + rabbitmq + mongodb satélite)
- [ ] .env.example com todas as variáveis documentadas
- [ ] Script de health check: verifica se legado está acessível via GET
- [ ] Teste de contrato: TelemetryEvent válido aceito, inválido rejeitado
- [ ] Mover API key hardcoded do legado para variável de ambiente

### Sprint 1 — Gateway + Telemetria (Ago–Set)
- [ ] FastAPI gateway: /v1/curriculum/adapt + /v1/telemetry/events
- [ ] RabbitMQ: exchange + 3 filas
- [ ] Worker de ingestão: consome fila → persiste MongoDB TimeSeries
- [ ] Emulador de carga: 100 sessões paralelas
- [ ] Relatório de stress test: latência com e sem carga

### Sprint 2 — Motor de Adaptação (Set–Out)
- [ ] Text Mining: complexidade (CommonLit) + Bloom's Taxonomy
- [ ] Worker de perfil: GET read-only no legado + parse dos tokens
- [ ] Worker de adaptação: prompt engineering + LLM + resposta estruturada
- [ ] Flutter: skeleton + login + tela Professor (inserir atividade)
- [ ] Flutter: tela Aluno (atividade adaptada passo a passo + áudio)

### Sprint 3 — Graph Mining + FL (Out–Nov)
- [ ] NetworkX: grafo de trilhas (conceitos → recomendação)
- [ ] Rede de Cuidado: centralidade + alertas de nós isolados
- [ ] Flower: FedAvg com N escolas simuladas
- [ ] Flutter: tela Pais (histórico + comparativo original/adaptado)

### Sprint 4 — XAI + Pitch (Nov–Dez)
- [ ] SHAP cards em linguagem acessível (pais) e técnica (professor)
- [ ] PySpark ETL completo sobre DSB2019
- [ ] XGBoost treinado + validação estratificada
- [ ] Business Model Canvas + pitch deck
- [ ] Ensaio da demo ao vivo com banca simulada

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

### ADR-001: Arquitetura Satélite
**Decisão:** Código novo em repositório separado, sem modificar o legado.
**Motivo:** Preservar o sistema premiado no SBCUP sem risco de regressão.

### ADR-002: LLM via API
**Decisão:** Gemini Flash 1.5. Custo estimado < R$ 0,01 por adaptação.
**Fallback:** Claude Haiku se Gemini indisponível.

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

- ❌ Modificar arquivos do repositório legado (exceto Sprint 0: env vars)
- ❌ Usar dados reais de crianças — usar DSB2019 (público) nesta fase
- ❌ Hardcodar chaves, senhas ou tokens no código
- ❌ Usar neon, animações ou movimento na interface do aluno TEA
- ❌ Armazenar diagnóstico médico — apenas tokens comportamentais
- ❌ Justificar texto na interface do aluno com dislexia
- ❌ Escrever no banco MongoDB do legado
- ❌ Adicionar funcionalidades fora do escopo sem avaliar impacto no prazo

---

## 14. Critérios de aceite — a demo está pronta quando

- [ ] Professor insere atividade → 3 versões geradas em < 10 segundos
- [ ] Aluno abre app e encontra atividade no formato correto para seu perfil
- [ ] Pais visualizam histórico + explicação da adaptação em linguagem simples
- [ ] Stress test: 100 sessões paralelas sem degradar o legado
- [ ] Grafo gera recomendação visível no app
- [ ] Card SHAP explicável aparece na interface do professor
- [ ] Experimento FL: centralizado vs. federado com resultado quantificado

---

*Criado: Agosto de 2026*
*Apresentação prevista: Novembro / Dezembro de 2026*
*Base acadêmica: CogniKids SBCUP 2026 — apresentado em 21 de julho de 2026*
*Repositório legado: CogniKids-SBCUP2026 (congelado)*
*Este repositório: CogniKidsV3 — construção do zero neste semestre*
