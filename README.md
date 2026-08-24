<div align="center">

<img src="cognikids-front-end/assets/images/logo%20CogniKids.png" alt="CogniKids — Logo Oficial" width="220"/>

# CogniKids

### Sinergia entre IoT e Inteligência Artificial para o Suporte Colaborativo Família-Escola na Educação Inclusiva

[![License: PolyForm NC 1.0.0](https://img.shields.io/badge/License-PolyForm%20NC%201.0.0-blue.svg)](https://polyformproject.org/licenses/noncommercial/1.0.0/)
[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)](https://www.docker.com/)
[![MQTT](https://img.shields.io/badge/MQTT-Mosquitto-660066.svg)](https://mosquitto.org/)
[![Redis](https://img.shields.io/badge/Redis-Buffer-DC382D.svg?logo=redis&logoColor=white)](https://redis.io/)
[![MongoDB](https://img.shields.io/badge/MongoDB-Persistence-47A248.svg?logo=mongodb&logoColor=white)](https://www.mongodb.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B.svg?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Status](https://img.shields.io/badge/Status-Fase%201%20%7C%20Prova%20de%20Conceito-orange.svg)]()

> Repositório oficial com o código-fonte do CogniKids — uma plataforma educacional
> e terapêutica para crianças neurodivergentes que conecta Professor, Pais e Aluno
> em torno de dados reais de comportamento e aprendizagem.

</div>

---

## Sumário

- [Resumo](#resumo)
- [Status do Projeto](#status-do-projeto)
- [Resultados Obtidos](#resultados-obtidos)
- [Arquitetura da Solução](#arquitetura-da-solução)
- [Estrutura do Repositório](#estrutura-do-repositório)
- [Considerações Éticas](#considerações-éticas)
- [Reprodutibilidade](#reprodutibilidade)
- [Material Complementar](#material-complementar)
- [Licença](#licença)
- [Autores](#autores)

---

## Resumo

Este projeto avalia a viabilidade técnica do **CogniKids**, uma Prova de Conceito baseada em **IoT pervasiva** para o monitoramento contínuo de estados emocionais de estudantes neurodivergentes. Fundamentado no paradigma da **Computação Ubíqua**, o sistema utiliza uma arquitetura distribuída orientada a eventos, com sensores vestíveis não intrusivos e Aprendizado de Máquina para detecção contextualizada de crises de desregulação emocional.

A solução foi concebida como ponte tecnológica entre o ambiente escolar e familiar, fornecendo aos educadores informações sensíveis ao contexto que apoiam intervenções pedagógicas oportunas, sem interromper o fluxo de aprendizagem.

---

## Status do Projeto

> **Este repositório corresponde à Fase 1 do projeto CogniKids — Prova de Conceito (PoC) e validação técnica em ambiente de simulação estocástica.**

| Item                       | Situação                                                                                  |
|----------------------------|-------------------------------------------------------------------------------------------|
| **Fase Atual**             | **Fase 1** — viabilidade técnica e arquitetural com dados sintéticos.                     |
| **Fase 2 (planejada)**     | Validação clínica supervisionada com aprovação de Comitê de Ética (CEP/CONEP).            |
| **Fase 3 (planejada)**     | Implantação piloto em ambiente escolar inclusivo e estudo longitudinal.                   |

A divisão em fases segue uma estratégia incremental: a Fase 1 demonstra a sustentação tecnológica do sistema (latência, escalabilidade, acurácia preditiva); as fases subsequentes endereçarão a coleta de dados reais sob protocolo ético e a avaliação do impacto pedagógico em campo.

---

## Resultados Obtidos

| Métrica                          | Valor                | Descrição                                                |
|----------------------------------|----------------------|----------------------------------------------------------|
| Acurácia do Modelo               | **85%**              | Random Forest aplicado a dados sintéticos (TEA)          |
| Revocação (*Recall*)             | **84%**              | Capacidade de recuperar episódios de crise               |
| Latência média do *backend*      | **50,27 ms**         | Sob carga de 50.000 registros simulados                  |
| Volume de dados validados        | 50.000+ registros    | Geração estocástica baseada em literatura médica         |

> Os resultados confirmam a **viabilidade técnica** de um suporte contínuo, escalável e de baixa latência, adequado ao ambiente escolar inclusivo.

---

## Arquitetura da Solução

A arquitetura técnica foi estruturada em **quatro camadas desacopladas**, garantindo escalabilidade horizontal, baixa latência e tolerância a falhas:

```
┌──────────────────────────┐
│ 1. Percepção (IoT)       │  Pulseira M5StickC + sensores biométricos (BPM, GSR, Acelerômetro)
└────────────┬─────────────┘
             │  MQTT/TLS (Mosquitto)
             ▼
┌──────────────────────────┐
│ 2. Comunicação & Buffer  │  Bridge Python → Cluster Redis (buffer elástico)
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│ 3. Inteligência (ML)     │  Worker Python + Random Forest (scikit-learn) → MongoDB
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│ 4. Aplicação (Dashboard) │  Streamlit (alertas, gráficos, monitoramento em tempo real)
└──────────────────────────┘
```

### 1. Camada de Percepção (IoT)
Sensores vestíveis (*wearables*) monitoram parâmetros biométricos e comportamentais essenciais:
- **Frequência Cardíaca (BPM)**
- **Condutância Galvânica da Pele (GSR)**
- **Índice de Movimento (Acelerômetro)**

A transmissão é feita via protocolo **MQTT** através do *broker* Mosquitto com suporte **TLS**, visando segurança e baixo *overhead* energético.

### 2. Camada de Comunicação e Buffer
Um serviço de ponte (*bridge*) em Python consome as mensagens MQTT e as enfileira em um cluster **Redis**, atuando como *buffer* elástico que **desacopla a ingestão assíncrona** dos sensores do processamento de inferência.

### 3. Camada de Processamento e Inteligência (Machine Learning)
Um *worker* consome os dados em memória e aplica o modelo pré-treinado **Random Forest** (`scikit-learn`) para predição em tempo real de crises de desregulação emocional. Os logs brutos e os resultados classificados são persistidos no **MongoDB**, viabilizando rastreabilidade e estudos longitudinais.

### 4. Camada de Aplicação (Dashboard)
Interface sensível ao contexto desenvolvida em **Streamlit**, fornecendo aos educadores:
- Monitoramento em tempo real;
- Emissão de alertas sonoros e visuais;
- Gráficos de tendências comportamentais;
- Relatórios de evolução por aluno.

---

## Estrutura do Repositório

```
CogniKids/
├── cognikids-backend/              # API Flask, brokers, workers e infraestrutura Docker (core)
│   ├── app/                        # Controllers, Models, Views, Utils
│   ├── docker-compose.yml          # MongoDB + Redis + Mosquitto + API
│   ├── mqtt_to_redis_bridge.py     # Bridge MQTT -> Redis
│   ├── alert_monitor.py            # Worker de inferência (Random Forest)
│   └── scripts/                    # Seeds, demos e utilitários
│
├── cognikids-front-end/            # Dashboard Streamlit para educadores
│   ├── app.py
│   ├── modules/                    # Login, Dashboard, Atividades, Relatórios
│   └── assets/
│
├── cognikids-adapt/                # Serviço satélite: motor de adaptação curricular com IA
│   ├── gateway/                    # FastAPI
│   ├── workers/                    # Workers RabbitMQ
│   └── notebooks/                  # Mineração de dados (CRISP-DM)
│
├── cognikids-pulseira-m5stack/     # Firmware MicroPython (M5StickC)
│   ├── boot.py
│   ├── main.py
│   └── config.example.py
│
└── docs/data-science/              # Notebooks, EDA e visualizações
    ├── Analise_EDA.ipynb
    ├── Apresentacao_CRISP-DM.md
    ├── confusion_matrix.png
    ├── feature_importance.png
    └── roc_curve.png
```

---

## Considerações Éticas

Devido às restrições éticas rigorosas atreladas à coleta de dados biométricos de **menores de idade** — conforme estabelecido pela **LGPD (Lei nº 13.709/2018)** e por princípios bioéticos —, a validação desta Prova de Conceito foi integralmente conduzida em um **ambiente de simulação estocástica**.

Todos os dados biométricos utilizados para o treinamento dos modelos e aferição de latência da rede são **sintéticos**, gerados a partir de padrões descritos na literatura médica para o **Transtorno do Espectro Autista (TEA)**.

> **Nenhum dado real de menores foi coletado, processado ou armazenado nesta etapa de pesquisa.**

---

## Reprodutibilidade

### Pré-requisitos
- [Docker](https://docs.docker.com/get-docker/) e [Docker Compose](https://docs.docker.com/compose/install/)
- [Python 3.9+](https://www.python.org/downloads/)
- (Opcional) Pulseira **M5StickC** com firmware **MicroPython**

### 1. Iniciar Infraestrutura e Backend (core)
Inicializa os contêineres do MongoDB, Redis, *Broker* MQTT e a API Flask:
```bash
cd cognikids-backend
cp .env.example .env
docker-compose up -d
```

### 2. Iniciar o Dashboard (Frontend)
Sobe a interface visual de monitoramento em Streamlit:
```bash
cd cognikids-front-end
pip install -r requirements.txt
streamlit run app.py
```
A aplicação será disponibilizada em `http://localhost:8501`.

### 3. Simulação IoT (Hardware Opcional)
O firmware em **MicroPython** para os *wearables* encontra-se em `cognikids-pulseira-m5stack/`.
Renomeie `config.example.py` para `config.py` e edite as credenciais do *broker* MQTT em execução.

### 4. Verificação
```bash
curl http://localhost:5001/api/status
```
Documentação interativa da API: `http://localhost:5001/docs`

---

## Material Complementar

| Recurso                                | Localização                                          |
|----------------------------------------|------------------------------------------------------|
| Análise Exploratória (EDA)             | [`docs/data-science/Analise_EDA.ipynb`](docs/data-science/Analise_EDA.ipynb) |
| Metodologia CRISP-DM                   | [`docs/data-science/Apresentacao_CRISP-DM.md`](docs/data-science/Apresentacao_CRISP-DM.md) |
| Matriz de Confusão                     | [`docs/data-science/confusion_matrix.png`](docs/data-science/confusion_matrix.png) |
| Importância das *Features*             | [`docs/data-science/feature_importance.png`](docs/data-science/feature_importance.png) |
| Curva ROC                              | [`docs/data-science/roc_curve.png`](docs/data-science/roc_curve.png) |
| Distribuição de Latência               | [`docs/data-science/latencia_distribuicao_real.png`](docs/data-science/latencia_distribuicao_real.png) |

---

## Licença

Distribuído sob a **PolyForm Noncommercial License 1.0.0**.

Esta licença permite **uso acadêmico, científico, educacional e de pesquisa** — incluindo replicação, modificação e estudos derivados —, mas **proíbe expressamente o uso comercial**. Consulte o arquivo [`LICENSE`](LICENSE) ou o [texto oficial da licença](https://polyformproject.org/licenses/noncommercial/1.0.0/) para mais informações.

> **Para uso comercial**, entre em contato com os autores para negociação de licença específica.

---

## Autores

| Autor(a)                            | Filiação                                       |
|-------------------------------------|------------------------------------------------|
| **Maria Clara Ribeiro Di Bragança** | Faculdade SENAI Fatesg — Goiânia, GO, Brasil   |
| **Frederico Lemes Rosa**            | Faculdade SENAI Fatesg — Goiânia, GO, Brasil   |
| **Willgnner Ferreira Santos**       | Faculdade SENAI Fatesg — Goiânia, GO, Brasil   |
| **Alisson Rodrigues Alves**         | Faculdade SENAI Fatesg — Goiânia, GO, Brasil   |
