import pytest
from pydantic import ValidationError

from app.schemas.curriculum import Adaptation, CurriculumAdaptRequest, CurriculumJobStatus

VALID_REQUEST = {
    "teacher_id": "professor-123",
    "title": "A fotossíntese",
    "subject": "Ciências",
    "original_content": "Explique o processo de fotossíntese nas plantas.",
    "student_ids": ["aluno-1", "aluno-2"],
}


def test_request_valida_e_aceita():
    request = CurriculumAdaptRequest(**VALID_REQUEST)
    assert request.teacher_id == "professor-123"
    assert len(request.student_ids) == 2


@pytest.mark.parametrize("campo_removido", ["teacher_id", "title", "original_content", "student_ids"])
def test_request_sem_campo_obrigatorio_e_rejeitada(campo_removido):
    dados = {k: v for k, v in VALID_REQUEST.items() if k != campo_removido}
    with pytest.raises(ValidationError):
        CurriculumAdaptRequest(**dados)


def test_request_com_student_ids_nao_lista_e_rejeitada():
    dados = {**VALID_REQUEST, "student_ids": "aluno-1"}
    with pytest.raises(ValidationError):
        CurriculumAdaptRequest(**dados)


def test_job_status_aceita_lista_de_adaptacoes_vazia_por_padrao():
    job = CurriculumJobStatus(job_id="abc", status="queued")
    assert job.adaptations == []


def test_adaptation_exige_todos_os_campos_do_contrato():
    adaptacao = Adaptation(
        student_id="aluno-1",
        adapted_content="Texto adaptado",
        format_applied=["passo_a_passo", "audio"],
        xai_explanation="Explicação",
        profile_tokens_used={"audio_disponivel": True},
    )
    assert adaptacao.format_applied == ["passo_a_passo", "audio"]
