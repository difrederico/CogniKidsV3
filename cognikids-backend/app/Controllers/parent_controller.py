"""
Endpoints do perfil Responsavel (pai/mae).

O responsavel enxerga exclusivamente os filhos vinculados a ele, e o vinculo
so pode ser criado informando o email do aluno.
"""

import datetime
import logging

from flask import Blueprint, request

from app import mongo
from app.Models.alert_model import Alert
from app.Models.class_model import Class
from app.Models.feeling_model import Feeling
from app.Models.goal_model import Goal
from app.Models.user_model import User
from app.Utils.authz import filhos_do_responsavel, pode_ver_aluno, to_object_id
from app.Utils.decorators import responsavel_required, token_required
from app.Utils.responses import (
    dados_invalidos,
    erro_interno,
    nao_autorizado,
    nao_encontrado,
    sucesso,
)
from app.Utils.roles import ESTUDANTE, normalizar_tipo

logger = logging.getLogger(__name__)

parent_blueprint = Blueprint('parent', __name__)
user_model = User()
feeling_model = Feeling()
alert_model = Alert()
goal_model = Goal()
class_model = Class()


@parent_blueprint.route('/link-child', methods=['POST'])
@token_required
@responsavel_required
def link_child(current_user):
    """Associa um filho ao responsavel pelo email do aluno."""
    try:
        data = request.get_json(silent=True) or {}
        child_email = (data.get('child_email') or '').strip().lower()

        if not child_email:
            return dados_invalidos('Email do filho em falta')

        child = user_model.find_user_by_email(child_email)
        if not child or normalizar_tipo(child.get('tipo')) != ESTUDANTE:
            return nao_encontrado('Aluno nao encontrado com este email')

        user_model.link_child_to_parent(current_user['_id'], child['_id'])

        return sucesso(
            message=f'Aluno {child["nome"]} associado com sucesso!',
            child_id=str(child['_id']),
        )

    except Exception as e:
        return erro_interno(e, 'ao associar filho')


@parent_blueprint.route('/unlink-child/<string:child_id>', methods=['DELETE'])
@token_required
@responsavel_required
def unlink_child(current_user, child_id):
    """Remove o vinculo com um filho."""
    try:
        child_oid = to_object_id(child_id)
        if child_oid is None:
            return dados_invalidos('ID do filho invalido')

        if child_oid not in filhos_do_responsavel(current_user):
            return nao_autorizado('Este aluno nao esta vinculado a voce')

        user_model.unlink_child_from_parent(current_user['_id'], child_oid)
        return sucesso(message='Vinculo removido com sucesso')

    except Exception as e:
        return erro_interno(e, 'ao remover vinculo')


@parent_blueprint.route('/children', methods=['GET'])
@token_required
@responsavel_required
def get_children(current_user):
    """Lista os filhos vinculados ao responsavel."""
    try:
        filhos_ids = filhos_do_responsavel(current_user)
        if not filhos_ids:
            return sucesso(data=[], total=0)

        filhos = []
        for filho in user_model.find_students_by_ids(filhos_ids):
            filho['_id'] = str(filho['_id'])
            if filho.get('turma_id'):
                filho['turma_id'] = str(filho['turma_id'])
            filhos.append(filho)

        return sucesso(data=filhos, total=len(filhos))

    except Exception as e:
        return erro_interno(e, 'ao listar filhos')


@parent_blueprint.route('/children/<string:child_id>/feelings', methods=['GET'])
@token_required
@responsavel_required
def get_child_feelings(current_user, child_id):
    """Sentimentos registrados por um filho."""
    try:
        child_oid = to_object_id(child_id)
        if child_oid is None:
            return dados_invalidos('ID do filho invalido')

        if not pode_ver_aluno(current_user, child_oid):
            return nao_autorizado('Este aluno nao esta vinculado a voce')

        feelings = feeling_model.find_feelings_by_aluno_id(str(child_oid))
        for f in feelings:
            f['_id'] = str(f['_id'])
            f['aluno_id'] = str(f['aluno_id'])
            if f.get('timestamp'):
                f['timestamp'] = f['timestamp'].isoformat()

        return sucesso(data=feelings)

    except Exception as e:
        return erro_interno(e, 'ao buscar sentimentos do filho')


@parent_blueprint.route('/children/<string:child_id>/alerts', methods=['GET'])
@token_required
@responsavel_required
def get_child_alerts(current_user, child_id):
    """Historico de alertas de crise de um filho."""
    try:
        child_oid = to_object_id(child_id)
        if child_oid is None:
            return dados_invalidos('ID do filho invalido')

        if not pode_ver_aluno(current_user, child_oid):
            return nao_autorizado('Este aluno nao esta vinculado a voce')

        dias = max(1, min(request.args.get('dias', 30, type=int) or 30, 365))
        desde = datetime.datetime.utcnow() - datetime.timedelta(days=dias)

        alertas = alert_model.find_by_aluno(child_oid, desde=desde, ordem=-1)
        serializados = [Alert.serializar(a) for a in alertas]

        return sucesso(data=serializados, count=len(serializados))

    except Exception as e:
        return erro_interno(e, 'ao buscar alertas do filho')


@parent_blueprint.route('/children/<string:child_id>/grades', methods=['GET'])
@token_required
@responsavel_required
def get_child_grades(current_user, child_id):
    """Notas de um filho."""
    try:
        child_oid = to_object_id(child_id)
        if child_oid is None:
            return dados_invalidos('ID do filho invalido')

        if not pode_ver_aluno(current_user, child_oid):
            return nao_autorizado('Este aluno nao esta vinculado a voce')

        from app.Models.grade_model import Grade
        notas = Grade().get_student_grades(str(child_oid))

        return sucesso(data=[Grade.serializar_nota(n) for n in notas])

    except Exception as e:
        return erro_interno(e, 'ao buscar notas do filho')


@parent_blueprint.route('/children/<string:child_id>/goals', methods=['GET'])
@token_required
@responsavel_required
def get_child_goals(current_user, child_id):
    """Metas de um filho."""
    try:
        child_oid = to_object_id(child_id)
        if child_oid is None:
            return dados_invalidos('ID do filho invalido')

        if not pode_ver_aluno(current_user, child_oid):
            return nao_autorizado('Este aluno nao esta vinculado a voce')

        metas = goal_model.find_by_student_id(child_oid)
        return sucesso(data=[Goal.serializar(m) for m in metas])

    except Exception as e:
        return erro_interno(e, 'ao buscar metas do filho')


@parent_blueprint.route('/dashboard', methods=['GET'])
@token_required
@responsavel_required
def get_dashboard(current_user):
    """Resumo consolidado dos filhos para a tela inicial do responsavel."""
    try:
        filhos_ids = filhos_do_responsavel(current_user)
        if not filhos_ids:
            return sucesso(data={'total_filhos': 0, 'alertas_recentes': [], 'filhos': []})

        desde = datetime.datetime.utcnow() - datetime.timedelta(days=7)
        alertas = alert_model.find_by_alunos(filhos_ids, desde=desde)

        filhos = []
        for filho in user_model.find_students_by_ids(filhos_ids):
            filhos.append({
                '_id': str(filho['_id']),
                'nome': filho.get('nome'),
                'turma_id': str(filho['turma_id']) if filho.get('turma_id') else None,
            })

        return sucesso(data={
            'total_filhos': len(filhos),
            'alertas_recentes': [Alert.serializar(a) for a in alertas[:10]],
            'total_alertas_semana': len(alertas),
            'filhos': filhos,
        })

    except Exception as e:
        return erro_interno(e, 'ao montar dashboard do responsavel')
