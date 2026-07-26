import datetime
import logging

from flask import Blueprint, current_app, request
import jwt

from app import bcrypt
from app.Models.user_model import User
from app.Utils.decorators import token_required
from app.Utils.responses import dados_invalidos, erro, erro_interno, sucesso
from app.Utils.roles import (
    ROLE_FRONTEND,
    TIPOS_PERMITIDOS,
    normalizar_tipo,
)
from app.Utils.validators import validate_email

logger = logging.getLogger(__name__)

auth_blueprint = Blueprint('auth', __name__)
user_model = User()

TOKEN_VALIDADE_HORAS = 24
SENHA_MIN_LEN = 6


@auth_blueprint.route('/register', methods=['POST'])
def register():
    """Registra um novo usuario (estudante, professor, pai ou admin)."""
    try:
        data = request.get_json(silent=True) or {}

        nome = (data.get('nome') or '').strip()
        email = (data.get('email') or '').strip().lower()
        senha = data.get('senha') or ''
        tipo = normalizar_tipo(data.get('tipo'))

        if not all([nome, email, senha, data.get('tipo')]):
            return dados_invalidos(
                'Faltam campos essenciais: nome, email, senha ou tipo (role).'
            )

        if not validate_email(email):
            return dados_invalidos('Email invalido')

        if len(senha) < SENHA_MIN_LEN:
            return dados_invalidos(
                f'A senha deve ter pelo menos {SENHA_MIN_LEN} caracteres'
            )

        if tipo not in TIPOS_PERMITIDOS:
            return dados_invalidos(
                f'Tipo de usuario invalido. Tipos permitidos: {", ".join(TIPOS_PERMITIDOS)}'
            )

        if user_model.find_user_by_email(email):
            return erro('Email ja registado', 409)

        hashed_password = bcrypt.generate_password_hash(senha).decode('utf-8')

        result = user_model.create_user({
            'nome': nome,
            'email': email,
            'senha': hashed_password,
            'tipo': tipo,
            'turma_id': data.get('turma_id'),
        })

        if not result.get('success'):
            logger.error('Falha ao registrar usuario: %s', result.get('message'))
            return erro(result.get('message', 'Erro interno do servidor'), 500)

        return sucesso(
            message='Utilizador registado com sucesso!',
            status_code=201,
            user_id=result.get('user_id'),
        )

    except Exception as e:
        return erro_interno(e, 'no registro de usuario')


@auth_blueprint.route('/login', methods=['POST'])
def login():
    """Autentica o usuario e devolve um JWT valido por 24h."""
    try:
        data = request.get_json(silent=True) or {}

        email = (data.get('email') or '').strip().lower()
        senha = data.get('senha') or ''

        if not email or not senha:
            return dados_invalidos('Dados em falta: email e senha sao obrigatorios.')

        user = user_model.find_user_by_email(email)

        # Mensagem identica para email inexistente e senha errada, para nao
        # revelar quais emails estao cadastrados.
        credenciais_invalidas = erro('Email ou senha invalidos', 401)

        if not user:
            return credenciais_invalidas

        if not bcrypt.check_password_hash(user['senha'], senha):
            return credenciais_invalidas

        tipo = normalizar_tipo(user.get('tipo'))

        token = jwt.encode(
            {
                'user_id': str(user['_id']),
                'email': user['email'],
                'role': tipo,
                'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=TOKEN_VALIDADE_HORAS),
                'iat': datetime.datetime.utcnow(),
            },
            current_app.config['SECRET_KEY'],
            algorithm='HS256',
        )

        return sucesso(
            message='Login realizado com sucesso!',
            success=True,
            token=token,
            role=tipo,
            frontend_role=ROLE_FRONTEND.get(tipo, tipo),
            user={
                'id': str(user['_id']),
                'name': user['nome'],
                'email': user['email'],
                'role': tipo,
                'frontend_role': ROLE_FRONTEND.get(tipo, tipo),
            },
        )

    except Exception as e:
        return erro_interno(e, 'no login')


@auth_blueprint.route('/profile', methods=['GET'])
@token_required
def profile(current_user):
    """Dados do usuario autenticado."""
    tipo = normalizar_tipo(current_user.get('tipo'))
    user_data = {
        'id': str(current_user['_id']),
        'nome': current_user['nome'],
        'email': current_user['email'],
        'tipo': tipo,
        'frontend_role': ROLE_FRONTEND.get(tipo, tipo),
    }

    if current_user.get('turma_id'):
        user_data['turma_id'] = str(current_user['turma_id'])
    if current_user.get('turmas_ids'):
        user_data['turmas_ids'] = [str(t) for t in current_user['turmas_ids']]
    if current_user.get('filhos_ids'):
        user_data['filhos_ids'] = [str(f) for f in current_user['filhos_ids']]

    return sucesso(user=user_data, data=user_data)


@auth_blueprint.route('/profile', methods=['PUT'])
@token_required
def update_profile(current_user):
    """Atualiza nome e email do proprio usuario."""
    try:
        data = request.get_json(silent=True) or {}
        atualizacao = {}

        if data.get('nome'):
            atualizacao['nome'] = data['nome'].strip()

        if data.get('email'):
            email = data['email'].strip().lower()
            if not validate_email(email):
                return dados_invalidos('Email invalido')
            existente = user_model.find_user_by_email(email)
            if existente and str(existente['_id']) != str(current_user['_id']):
                return erro('Email ja registado por outro usuario', 409)
            atualizacao['email'] = email

        if not atualizacao:
            return dados_invalidos('Nenhum campo valido para atualizar')

        user_model.update_user(current_user['_id'], atualizacao)
        return sucesso(message='Perfil atualizado com sucesso')

    except Exception as e:
        return erro_interno(e, 'ao atualizar perfil')


@auth_blueprint.route('/change-password', methods=['PUT'])
@token_required
def change_password(current_user):
    """Troca a senha do proprio usuario, exigindo a senha atual."""
    try:
        data = request.get_json(silent=True) or {}
        senha_atual = data.get('senha_atual') or ''
        senha_nova = data.get('senha_nova') or ''

        if not senha_atual or not senha_nova:
            return dados_invalidos('senha_atual e senha_nova sao obrigatorias')

        if len(senha_nova) < SENHA_MIN_LEN:
            return dados_invalidos(
                f'A nova senha deve ter pelo menos {SENHA_MIN_LEN} caracteres'
            )

        if not bcrypt.check_password_hash(current_user['senha'], senha_atual):
            return erro('Senha atual incorreta', 401)

        novo_hash = bcrypt.generate_password_hash(senha_nova).decode('utf-8')
        user_model.update_password(current_user['_id'], novo_hash)

        return sucesso(message='Senha alterada com sucesso')

    except Exception as e:
        return erro_interno(e, 'ao alterar senha')
