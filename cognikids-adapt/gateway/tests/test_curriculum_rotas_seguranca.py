"""Ataques ao nivel de HTTP — provam que a ROTA aplica a checagem.

Testar so `pode_ver_job` provaria que a funcao esta certa, nao que alguem a
chamou. Estes testes sobem o app de verdade e tentam o acesso indevido pela
rota, que e onde a falha existia.
"""

import pytest
from fastapi.testclient import TestClient

from app.api.v1 import curriculum
from app.core.security import professor_autenticado, usuario_autenticado
from app.db.mongo import get_db
from app.main import app

JOB = {
    "job_id": "job-1",
    "status": "queued",
    "teacher_id": "prof-dono",
    "student_ids": ["aluno-a"],
    "adaptations": [],
}


class _ColecaoFalsa:
    async def find_one(self, filtro, projecao=None):
        return dict(JOB) if filtro.get("job_id") == JOB["job_id"] else None


class _DbFalso:
    def __getitem__(self, _nome):
        return _ColecaoFalsa()


@pytest.fixture
def cliente():
    app.dependency_overrides[get_db] = lambda: _DbFalso()
    yield TestClient(app)
    app.dependency_overrides.clear()


def _autenticar_como(user_id, role):
    app.dependency_overrides[usuario_autenticado] = lambda: {"user_id": user_id, "role": role}
    app.dependency_overrides[professor_autenticado] = lambda: {"user_id": user_id, "role": role}


# --------------------------------------------------------------------------
# IDOR em GET /v1/curriculum/jobs/{job_id}
# --------------------------------------------------------------------------

def test_professor_dono_le_o_job(cliente):
    _autenticar_como("prof-dono", "professor")
    resposta = cliente.get("/v1/curriculum/jobs/job-1")
    assert resposta.status_code == 200
    assert resposta.json()["job_id"] == "job-1"


def test_professor_alheio_nao_le_o_job(cliente):
    """Antes da correcao isto devolvia 200 com o conteudo completo."""
    _autenticar_como("prof-alheio", "professor")
    resposta = cliente.get("/v1/curriculum/jobs/job-1")
    assert resposta.status_code == 404, (
        "REGRESSAO CRITICA: IDOR reaberto em GET /v1/curriculum/jobs"
    )


def test_resposta_negada_nao_vaza_conteudo_da_atividade(cliente):
    _autenticar_como("aluno-de-fora", "estudante")
    resposta = cliente.get("/v1/curriculum/jobs/job-1")
    assert "original_content" not in resposta.text
    assert "aluno-a" not in resposta.text


# --------------------------------------------------------------------------
# student_ids nao validados em POST /v1/curriculum/adapt
# --------------------------------------------------------------------------

def _corpo_adapt(student_ids):
    return {
        "teacher_id": "prof-dono",
        "title": "Frações",
        "subject": "Matemática",
        "original_content": "Divida a pizza em partes iguais.",
        "student_ids": student_ids,
    }


def test_adapt_recusa_aluno_fora_da_turma(cliente, monkeypatch):
    """Antes da correcao, qualquer professor pedia adaptacao para qualquer
    aluno da base, e o worker buscava os tokens com a conta de servico
    (admin), que ignora consentimento.
    """
    async def _permitidos(teacher_id, autorizacao):
        return {"aluno-a"}

    monkeypatch.setattr(curriculum, "alunos_visiveis_do_professor", _permitidos)
    _autenticar_como("prof-dono", "professor")

    resposta = cliente.post("/v1/curriculum/adapt", json=_corpo_adapt(["aluno-a", "aluno-alheio"]))

    assert resposta.status_code == 403, (
        "REGRESSAO CRITICA: /adapt voltou a aceitar aluno fora da turma"
    )
    assert "aluno-alheio" in resposta.json()["detail"]


def test_adapt_recusa_quando_core_esta_fora_do_ar(cliente, monkeypatch):
    """Sem confirmar a lista, o lado seguro e recusar, nunca liberar."""
    async def _indisponivel(teacher_id, autorizacao):
        return None

    monkeypatch.setattr(curriculum, "alunos_visiveis_do_professor", _indisponivel)
    _autenticar_como("prof-dono", "professor")

    resposta = cliente.post("/v1/curriculum/adapt", json=_corpo_adapt(["aluno-a"]))
    assert resposta.status_code == 503


def test_adapt_aceita_alunos_da_propria_turma(cliente, monkeypatch):
    async def _permitidos(teacher_id, autorizacao):
        return {"aluno-a", "aluno-b"}

    async def _criar_job(request, db):
        return "job-novo", 7

    monkeypatch.setattr(curriculum, "alunos_visiveis_do_professor", _permitidos)
    monkeypatch.setattr(curriculum.curriculum_service, "criar_job", _criar_job)
    _autenticar_como("prof-dono", "professor")

    resposta = cliente.post("/v1/curriculum/adapt", json=_corpo_adapt(["aluno-a", "aluno-b"]))
    assert resposta.status_code == 202, resposta.text
    assert resposta.json()["job_id"] == "job-novo"
