import uuid
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.clients import rabbitmq
from app.schemas.curriculum import CurriculumAdaptRequest, CurriculumJobStatus

COLLECTION = "curriculum_jobs"


def _estimar_segundos(quantidade_alunos: int) -> int:
    # Heurística simples: tempo base de fila + tempo proporcional por aluno
    # (cada aluno gera uma chamada de análise + adaptação em paralelo, ver CLAUDE.md seção 10)
    return 5 + 2 * quantidade_alunos


async def criar_job(request: CurriculumAdaptRequest, db: AsyncIOMotorDatabase) -> tuple[str, int]:
    job_id = str(uuid.uuid4())
    estimativa = _estimar_segundos(len(request.student_ids))

    await db[COLLECTION].insert_one({
        "job_id": job_id,
        "status": "queued",
        "teacher_id": request.teacher_id,
        "title": request.title,
        "subject": request.subject,
        "original_content": request.original_content,
        "student_ids": request.student_ids,
        "adaptations": [],
        "created_at": datetime.now(timezone.utc),
    })

    await rabbitmq.publish("analysis", {
        "job_id": job_id,
        "teacher_id": request.teacher_id,
        "title": request.title,
        "subject": request.subject,
        "original_content": request.original_content,
        "student_ids": request.student_ids,
    })

    return job_id, estimativa


async def buscar_job(job_id: str, db: AsyncIOMotorDatabase) -> dict | None:
    """Documento bruto do job — inclui teacher_id/student_ids, que o schema
    de resposta nao expoe mas a checagem de propriedade precisa.
    """
    return await db[COLLECTION].find_one({"job_id": job_id}, {"_id": 0})


def pode_ver_job(documento: dict, usuario: dict) -> bool:
    """So o professor que criou o job e os alunos citados nele podem le-lo.

    Antes desta checagem, GET /v1/curriculum/jobs/{job_id} exigia apenas um
    JWT valido de qualquer perfil: quem obtivesse um job_id (log, URL, app)
    lia `original_content`, a lista de alunos e — quando o worker de
    adaptacao existir — `profile_tokens_used`, que e o perfil funcional da
    crianca.

    Responsavel ainda nao entra aqui: liberar o pai exige perguntar ao core
    se aquele aluno e filho dele, e negar por padrao e' o lado seguro
    enquanto essa chamada nao existe.
    """
    user_id = usuario.get("user_id")
    if documento.get("teacher_id") == user_id:
        return True
    return user_id in (documento.get("student_ids") or [])


def montar_status(documento: dict) -> CurriculumJobStatus:
    return CurriculumJobStatus(**documento)
