# CogniKids — Master Prompt

Plataforma para crianças neurodivergentes (TEA/TDAH/Dislexia): Professor,
Pais, Aluno. Índice de documentação detalhada: §6.

## 1. Economia de Tokens & Output
- Sem saudação/preâmbulo/resumo final.
- Nunca reescrever arquivo inteiro: diff/bloco com contexto mínimo de linha.
- Ler seletivo (grep/offset+limit) antes de `Read` completo; nunca reler arquivo editado.
- Nunca inventar dado/número/URL — se não verificado, declare isso. Cite `arquivo:linha`.

## 2. Fronteiras Arquiteturais & LGPD
- Monorepo, dois microserviços **independentes em runtime**: `cognikids-backend`
  (Flask :5001, Mongo :27017) e `cognikids-adapt` (FastAPI :8001, Mongo :27018).
- Satélite nunca escreve no Mongo do core; nenhum importa código do outro —
  só HTTP + JWT HS256 (`CORE_JWT_SECRET`). Core roda sem o satélite.
- Zero diagnóstico médico — só tokens comportamentais. Nunca hardcodar segredo.
- Detalhe: `docs/architecture/ADRS.md` (ADRs, auditorias, LGPD).

## 3. Princípio Pedagógico Inegociável (UDL 3.0)
Conteúdo nunca muda — só formato/linguagem. Professor sempre aprova cada
versão antes do aluno ver. Perfis: TEA (zero animação/neon, passo a passo,
áudio) · TDAH (chunks curtos, sem streak/comparação) · Dislexia (fonte
legível, nunca justificar texto, espaçamento amplo). ADR-005/007 em
`docs/architecture/ADRS.md`.

## 4. Stack e Fluxo Ativo do Satélite
Gateway FastAPI :8001. RabbitMQ `cognikids`: pipeline analysis→profile→
adaptation; `telemetry` é fila própria e independente (`worker_ingestion`).
Mongo satélite :27018 (`student_graphs` sem TTL, é estado). LLM: Gemma 4
12B/Ollama local → fallback Gemini free (nunca enviar `profile_tokens_used`
sem consentimento — ADR-002).

## 5. Contratos Canônicos
`TelemetryEvent`: event_id, student_id, activity_id, session_id, event_type
(step_completed|audio_played|abandoned|hint_requested), step_number?,
concept?, correct?, duration_ms, timestamp, metadata. `concept`+`correct` só
em `step_completed` avaliável.

Fluxo: gateway publica em `analysis` → `worker_analysis` (Bloom/Simpson
PT-BR) → `profile` (tokens+grafo) → `adaptation` → `worker_adaptation`
(LLM, **stub hoje**). `worker_ingestion` consome `telemetry` e refina o grafo.

API: `POST /v1/curriculum/adapt`→202 job_id · `GET /v1/curriculum/jobs/{id}`→
status+adaptations[] · `POST /v1/telemetry/events`→201.

## 6. Índice de Documentação Detalhada
- `docs/architecture/ADRS.md` — ADRs, segurança, conselho, LGPD.
- `docs/architecture/DATASETS_ETL.md` — datasets, downloads, grafo, PySpark/JVM.
- `docs/project/ROADMAP_HISTORICO.md` — Sprints 0–4, stress test, FL, aceite.
- `docs/data-science/Apresentacao_CRISP-DM.md` — padrão de notebook.

*Apresentação: nov/dez 2026.*
