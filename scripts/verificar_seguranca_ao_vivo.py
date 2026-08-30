"""Verificacao go/no-go de seguranca — encena os ataques da ADR-010 ao vivo.

Diferente dos testes de unidade (mongomock + TestClient), aqui o core Flask e
o gateway FastAPI precisam estar NO AR de verdade, em containers, com Mongo e
RabbitMQ reais. E a prova forte, e a unica que cobre a camada de rede (o
Ataque 4 so faz sentido contra portas realmente publicadas).

Rodar antes de qualquer uso com dado real, e depois de qualquer mudanca em
docker-compose.yml, authz.py, auth_controller.py ou nas rotas do gateway.

Pre-requisitos:
    docker compose up -d
    docker compose -f cognikids-backend/docker-compose.yml \
        --project-directory cognikids-backend up -d

Uso:
    python scripts/verificar_seguranca_ao_vivo.py

Sai com codigo 1 se qualquer ataque passar. Deixa a base limpa: os usuarios
de teste criados ficam com e-mail @cognikids.test e o job inserido no
satelite e removido no fim.
"""

import uuid

import requests
from pymongo import MongoClient
from pymongo.errors import OperationFailure

CORE = "http://localhost:5001"
GATEWAY = "http://localhost:8001"
MONGO_SATELITE = "mongodb://localhost:27018/cognikids_adapt"

falhas = []


def checar(nome, condicao, detalhe=""):
    marca = "OK  " if condicao else "FALHA"
    print(f"[{marca}] {nome}" + (f"  -> {detalhe}" if detalhe else ""))
    if not condicao:
        falhas.append(nome)


def registrar(tipo, sufixo):
    email = f"ataque-{sufixo}-{uuid.uuid4().hex[:8]}@cognikids.test"
    r = requests.post(f"{CORE}/api/register", json={
        "nome": f"Ataque {sufixo}", "email": email,
        "senha": "senha-de-teste-123", "tipo": tipo,
    }, timeout=10)
    return r, email


def logar(email):
    r = requests.post(f"{CORE}/api/login", json={
        "email": email, "senha": "senha-de-teste-123",
    }, timeout=10)
    r.raise_for_status()
    corpo = r.json()
    return corpo["token"], corpo["user"]["id"]


print("=" * 70)
print("ATAQUE 1 — escalonamento de privilegio pelo cadastro publico")
print("=" * 70)

r, email_admin = registrar("admin", "admin")
checar("POST /api/register recusa tipo='admin'", r.status_code == 400,
       f"HTTP {r.status_code}: {r.text[:110]}")

r_alias, _ = registrar("administrador", "alias")
checar("POST /api/register recusa o alias 'administrador'", r_alias.status_code == 400,
       f"HTTP {r_alias.status_code}")

# Nada pode ter sido gravado
cli_core = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=3000)
achado = None
for nome_db in cli_core.list_database_names():
    if nome_db in ("admin", "config", "local"):
        continue
    if cli_core[nome_db].users.find_one({"email": email_admin}):
        achado = nome_db
checar("nenhum usuario admin foi gravado no banco", achado is None,
       f"encontrado em {achado}" if achado else "")

print()
print("=" * 70)
print("ATAQUE 2 — /adapt aceitando aluno fora da turma")
print("=" * 70)

r_prof_a, email_a = registrar("professor", "profA")
checar("cadastro legitimo de professor continua funcionando", r_prof_a.status_code == 201,
       f"HTTP {r_prof_a.status_code}")

token_a, id_a = logar(email_a)

r = requests.post(f"{GATEWAY}/v1/curriculum/adapt", json={
    "teacher_id": id_a,
    "title": "Frações",
    "subject": "Matemática",
    "original_content": "Divida a pizza em partes iguais.",
    "student_ids": ["68000000000000000000dead"],
}, headers={"Authorization": f"Bearer {token_a}"}, timeout=15)
checar("/adapt recusa aluno que nao e da turma do professor", r.status_code == 403,
       f"HTTP {r.status_code}: {r.text[:140]}")

print()
print("=" * 70)
print("ATAQUE 3 — IDOR: ler job de outro professor")
print("=" * 70)

cli_sat = MongoClient(MONGO_SATELITE, serverSelectionTimeoutMS=3000)
db_sat = cli_sat.get_default_database()

job_id = f"ataque-{uuid.uuid4()}"
db_sat.curriculum_jobs.insert_one({
    "job_id": job_id,
    "status": "queued",
    "teacher_id": id_a,
    "title": "Atividade sigilosa",
    "subject": "Matemática",
    "original_content": "CONTEUDO-QUE-NAO-PODE-VAZAR",
    "student_ids": ["aluno-do-prof-a"],
    "adaptations": [],
})

r = requests.get(f"{GATEWAY}/v1/curriculum/jobs/{job_id}",
                 headers={"Authorization": f"Bearer {token_a}"}, timeout=10)
checar("professor dono LE o proprio job", r.status_code == 200, f"HTTP {r.status_code}")

r_prof_b, email_b = registrar("professor", "profB")
token_b, id_b = logar(email_b)

r = requests.get(f"{GATEWAY}/v1/curriculum/jobs/{job_id}",
                 headers={"Authorization": f"Bearer {token_b}"}, timeout=10)
checar("professor ALHEIO nao le o job", r.status_code == 404, f"HTTP {r.status_code}")
checar("resposta negada nao vaza o conteudo da atividade",
       "CONTEUDO-QUE-NAO-PODE-VAZAR" not in r.text)

r_est, email_est = registrar("estudante", "aluno")
token_est, _ = logar(email_est)
r = requests.get(f"{GATEWAY}/v1/curriculum/jobs/{job_id}",
                 headers={"Authorization": f"Bearer {token_est}"}, timeout=10)
checar("aluno de fora nao le o job", r.status_code == 404, f"HTTP {r.status_code}")

db_sat.curriculum_jobs.delete_one({"job_id": job_id})

print()
print("=" * 70)
print("ATAQUE 4 — infraestrutura publicada na rede")
print("=" * 70)

import socket  # noqa: E402


def porta_em(host, porta):
    s = socket.socket()
    s.settimeout(2)
    try:
        s.connect((host, porta))
        return True
    except Exception:
        return False
    finally:
        s.close()


ip_lan = socket.gethostbyname(socket.gethostname())
print(f"IP desta maquina na rede: {ip_lan}")

for nome, porta in (("console RabbitMQ", 15672), ("AMQP RabbitMQ", 5672), ("Mongo satelite", 27018)):
    pelo_loopback = porta_em("127.0.0.1", porta)
    pela_rede = porta_em(ip_lan, porta)
    checar(f"{nome} ({porta}) NAO alcancavel pela rede", not pela_rede,
           f"loopback={pelo_loopback} rede={pela_rede}")

print()
print("=" * 70)
print("ATAQUE 5 — Mongo satelite sem autenticacao real (ADR-010)")
print("=" * 70)

# So o loopback nao basta: qualquer processo na mesma maquina (ou alguem que
# chegue ao loopback via tunel SSH, port-forward, ou um container vizinho
# comprometido) alcanca esta porta. MONGO_INITDB_ROOT_USERNAME so tem efeito
# em volume VAZIO — com mongo-adapt-data ja populado ela e' ignorada em
# silencio e o banco fica rodando sem auth "parecendo" protegido. Este
# ataque conecta SEM credenciais e tenta uma operacao que so teria sucesso
# se a autenticacao NAO estiver sendo exigida de verdade.
cli_sem_auth = None
try:
    cli_sem_auth = MongoClient(
        "mongodb://localhost:27018/", serverSelectionTimeoutMS=3000
    )
    nomes_bancos = cli_sem_auth.list_database_names()
    checar(
        "Mongo satelite exige autenticacao (conexao sem credenciais deveria falhar)",
        False,
        f"conectou sem credenciais e listou bancos: {nomes_bancos}",
    )
except OperationFailure:
    # E exatamente o esperado: sem credenciais, o comando e' recusado.
    checar("Mongo satelite exige autenticacao", True)
except Exception as e:
    # Erro de conexao (Mongo fora do ar, porta fechada) nao prova que a
    # autenticacao existe — nao afirmar seguranca por um motivo errado.
    checar("Mongo satelite exige autenticacao", False,
           f"nao foi possivel verificar (Mongo acessivel?): {e}")
finally:
    if cli_sem_auth is not None:
        cli_sem_auth.close()

print()
print("=" * 70)
if falhas:
    print(f"RESULTADO: {len(falhas)} FALHA(S) -> {falhas}")
    raise SystemExit(1)
print("RESULTADO: todos os ataques foram bloqueados.")
