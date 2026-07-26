# CogniKids — CLAUDE.md

PoC (Fase 1) de IoT + ML para monitoramento de estados emocionais de estudantes
neurodivergentes (TEA). Artigo aceito no **SBCUP 2026** (in press). Dados 100%
sintéticos — NENHUM dado real de menores. Licença PolyForm Noncommercial.

## ⚡ Economia de tokens (regras de ouro)
- **Zero enrolação:** sem saudações, sem "com certeza", sem resumos do que já
  foi dito. Comece pela ação (ferramenta/comando/resposta técnica direta).
- **Leitura cirúrgica:** nunca leia arquivo inteiro por uma função — use
  grep/glob e leia só o trecho. Só leia arquivos >150 linhas por completo em
  refatoração estrutural.
- **Explicação curta:** causa/solução em no máximo 2-3 frases. Responda só o
  que foi perguntado.
- **Diffs, não dumps:** mostre só as linhas alteradas + 2-3 de contexto. NUNCA
  reimprima arquivos/blocos que não mudaram.
- **Não re-explique** contexto já estabelecido na conversa.

## Precisão (evitar retrabalho)
- Investigar antes de editar: confirmar o comportamento real no código, não
  supor. Rodar o app/teste quando a mudança for arriscada.
- Não quebrar o que funciona: é uma PoC validada (85% acurácia, 50ms latência) —
  os números são do artigo, preservar reprodutibilidade.
- Confirmar antes de mudança de arquitetura ou decisão que afete o paper.
- Commit só quando eu pedir.

## Stack (não sugerir libs fora disto)
**Backend** (`cognikids-backend/`) — Python 3.9+
- Flask + Flask-PyMongo + Flask-Bcrypt + Flask-Cors + PyJWT + pydantic
- flasgger / flask-swagger-ui (docs em /docs)
- paho-mqtt (Mosquitto), redis, pymongo (MongoDB)
- scikit-learn + pandas + joblib (Random Forest)
- Docker Compose: MongoDB + Redis + Mosquitto + API

**Frontend** (`cognikids-front-end/`) — Streamlit + pandas + plotly + matplotlib

**Pulseira** (`cognikids-pulseira-m5stack/`) — MicroPython no M5StickC

## Arquitetura (4 camadas desacopladas, orientada a eventos)
1. **Percepção:** M5StickC → sensores (BPM, GSR, acelerômetro) → MQTT/TLS
2. **Buffer:** `mqtt_to_redis_bridge.py` consome MQTT → Redis (buffer elástico)
3. **Inteligência:** `alert_monitor.py` (worker) consome Redis → Random Forest →
   grava logs + classificação no MongoDB
4. **Aplicação:** dashboard Streamlit (alertas, gráficos, relatórios por aluno)

## Arquivos-chave (backend)
- `app.py` / `run.py` — entrada da API Flask
- `app/` — controllers, models, views, utils
- `mqtt_to_redis_bridge.py` — ponte MQTT→Redis
- `alert_monitor.py` — worker de inferência (Random Forest)
- `docker-compose.yml` · `mosquitto.conf` · `swagger.json`
- `scripts/` — seeds, demos, utilitários

## Rodar
```bash
# infra + API
cd cognikids-backend && cp .env.example .env && docker-compose up -d
# dashboard
cd cognikids-front-end && pip install -r requirements.txt && streamlit run app.py  # :8501
# verificar API
curl http://localhost:5001/api/status   # docs: :5001/docs
```

## Contexto científico (importante ao mexer em ML/dados)
- Todos os dados são **sintéticos** (geração estocástica baseada em literatura de
  TEA). Nunca introduzir/sugerir coleta de dados reais nesta fase.
- Métricas do artigo: acurácia 85%, recall 84%, latência média 50,27ms sob
  50k registros. Mudanças no modelo/pipeline devem preservar ou documentar
  impacto nesses números.
- Notebooks/EDA em `docs/data-science/`.
