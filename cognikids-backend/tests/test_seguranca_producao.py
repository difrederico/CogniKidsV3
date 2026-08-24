"""Testes que TENTAM o ataque. Se algum passar, o build deve quebrar.

Diferente do resto da suite, que verifica se a funcionalidade funciona,
aqui cada teste encena uma exploracao real encontrada em auditoria e falha
se ela voltar a ser possivel. E o unico mecanismo que impede a regressao de
uma falha de seguranca ja corrigida.
"""

from bson.objectid import ObjectId


# --------------------------------------------------------------------------
# Escalonamento de privilegio pelo cadastro publico
# --------------------------------------------------------------------------

def test_registro_publico_recusa_admin(client):
    """POST /api/register e rota publica (sem token).

    Aceitar tipo='admin' do corpo permitia que qualquer pessoa com acesso de
    rede a API criasse para si um perfil que ignora consentimento em
    pode_ver_aluno e alunos_visiveis — ou seja, leitura de biometria,
    alertas, sentimentos, notas e perfil funcional de TODAS as criancas.
    """
    resposta = client.post('/api/register', json={
        'nome': 'Invasor',
        'email': 'invasor@exemplo.test',
        'senha': 'senha123',
        'tipo': 'admin',
    })

    assert resposta.status_code != 201, (
        'REGRESSAO CRITICA: o cadastro publico voltou a criar admin'
    )
    assert resposta.status_code == 400


def test_registro_publico_recusa_alias_de_admin(client):
    """normalizar_tipo mapeia 'administrador' -> 'admin' (Utils/roles.py).

    Bloquear so a string exata 'admin' deixaria a porta aberta pelo alias.
    """
    resposta = client.post('/api/register', json={
        'nome': 'Invasor',
        'email': 'invasor2@exemplo.test',
        'senha': 'senha123',
        'tipo': 'administrador',
    })

    assert resposta.status_code == 400


def test_registro_publico_nao_grava_usuario_admin(client, db):
    """Nao basta responder 400: nada pode ter sido gravado."""
    client.post('/api/register', json={
        'nome': 'Invasor',
        'email': 'invasor3@exemplo.test',
        'senha': 'senha123',
        'tipo': 'admin',
    })

    assert db.users.find_one({'email': 'invasor3@exemplo.test'}) is None


def test_registro_publico_aceita_perfis_legitimos(client):
    """A correcao nao pode ter fechado o cadastro normal."""
    for indice, tipo in enumerate(('estudante', 'professor', 'pai')):
        resposta = client.post('/api/register', json={
            'nome': f'Usuario {tipo}',
            'email': f'legitimo{indice}@exemplo.test',
            'senha': 'senha123',
            'tipo': tipo,
        })
        assert resposta.status_code == 201, (
            f'cadastro legitimo de {tipo} quebrou: {resposta.get_data(as_text=True)}'
        )


def test_admin_enxerga_aluno_sem_consentimento(app, estudante):
    """Documenta POR QUE admin nunca pode nascer de rota publica.

    Este teste afirma o comportamento atual — admin e' bypass incondicional
    de consentimento (Utils/authz.py). Nao e' um bug a corrigir aqui: e' a
    razao pela qual o perfil so pode ser criado por quem tem acesso ao
    servidor (scripts/criar_admin.py). Se algum dia o bypass for removido,
    este teste falha e obriga a revisar a decisao conscientemente.
    """
    from app.Utils.authz import alunos_visiveis

    admin = {'_id': ObjectId(), 'tipo': 'admin'}

    # O estudante nao tem nenhum consentimento gravado.
    assert estudante.oid in alunos_visiveis(admin)
