"""
Consentimento granular e revogavel (LGPD).

O tratamento de dados pessoais de criancas exige consentimento especifico e
em destaque dado por ao menos um dos pais ou responsavel legal (LGPD art.
14, §1o). Dados de saude e biometricos sao categoria especial (art. 11).

Por isso o consentimento aqui e:

- Granular: quatro finalidades independentes. Negar coleta biometrica nao
  impede a crianca de usar o app.
- Revogavel: revogar e tao facil quanto conceder (art. 8o, §5o), e o efeito
  e imediato — a ingestao IoT passa a rejeitar os dados daquele aluno.
- Auditavel: cada concessao e revogacao vira um registro imutavel em
  consent_events, com data e autor. E o que sustenta a prestacao de contas
  perante um comite de etica.

O documento vigente fica em 'consents' (um por aluno); o rastro completo
fica em 'consent_events'.
"""

import datetime

from bson.objectid import ObjectId

from app import mongo

# --------------------------------------------------------------------------
# Finalidades
# --------------------------------------------------------------------------

USO_APP = 'uso_app'
COLETA_BIOMETRICA = 'coleta_biometrica'
COMPARTILHAR_ESCOLA = 'compartilhar_escola'
USO_PESQUISA = 'uso_pesquisa'

FINALIDADES = {
    USO_APP: {
        'titulo': 'Usar o aplicativo',
        'descricao': (
            'Seu filho pode entrar no app, registrar como esta se sentindo e '
            'pedir uma pausa quando precisar.'
        ),
        'obrigatorio': True,
        'implica': [],
    },
    COLETA_BIOMETRICA: {
        'titulo': 'Coletar dados da pulseira',
        'descricao': (
            'A pulseira mede batimentos cardiacos e movimento. Sem isso, o app '
            'continua funcionando, mas nao identifica sinais de desregulacao.'
        ),
        'obrigatorio': False,
        'implica': [USO_APP],
    },
    COMPARTILHAR_ESCOLA: {
        'titulo': 'Compartilhar com a escola',
        'descricao': (
            'O professor da turma pode ver os registros e os alertas do seu '
            'filho para apoia-lo durante a aula.'
        ),
        'obrigatorio': False,
        'implica': [USO_APP],
    },
    USO_PESQUISA: {
        'titulo': 'Usar os dados em pesquisa',
        'descricao': (
            'Dados sem identificacao podem ser usados em pesquisa academica '
            'para melhorar o sistema. Voce pode recusar sem prejuizo algum.'
        ),
        'obrigatorio': False,
        'implica': [],
    },
}

VERSAO_TERMO = '1.0.0'


def _to_object_id(valor):
    if isinstance(valor, ObjectId):
        return valor
    try:
        return ObjectId(valor)
    except Exception:
        return None


class Consent:
    def obter(self, aluno_id):
        """Documento de consentimento vigente do aluno (ou None)."""
        oid = _to_object_id(aluno_id)
        if oid is None:
            return None
        return mongo.db.consents.find_one({'aluno_id': oid})

    def estado(self, aluno_id):
        """Mapa {finalidade: bool} do que esta concedido agora."""
        documento = self.obter(aluno_id) or {}
        concedidos = documento.get('finalidades', {})
        return {f: bool(concedidos.get(f)) for f in FINALIDADES}

    def permite(self, aluno_id, finalidade):
        """Ha consentimento vigente para esta finalidade?"""
        return self.estado(aluno_id).get(finalidade, False)

    def registrar(self, aluno_id, finalidades, autor_id, ip=None):
        """Grava o consentimento e o evento de auditoria.

        Args:
            finalidades: {finalidade: bool}
            autor_id: responsavel que assinou

        Returns:
            (estado_final, avisos)
        """
        aluno_oid = _to_object_id(aluno_id)
        autor_oid = _to_object_id(autor_id)
        if aluno_oid is None or autor_oid is None:
            raise ValueError('IDs invalidos ao registrar consentimento')

        anterior = self.estado(aluno_id)
        novo = dict(anterior)
        avisos = []

        for finalidade, concedido in (finalidades or {}).items():
            if finalidade not in FINALIDADES:
                continue
            novo[finalidade] = bool(concedido)

        # Dependencias: negar uma finalidade derruba as que dependem dela.
        # Ex.: sem uso do app, nao ha como coletar biometria.
        for finalidade, meta in FINALIDADES.items():
            if not novo.get(finalidade):
                continue
            faltando = [d for d in meta['implica'] if not novo.get(d)]
            if faltando:
                novo[finalidade] = False
                titulos = ', '.join(FINALIDADES[d]['titulo'] for d in faltando)
                avisos.append(
                    f"'{meta['titulo']}' depende de: {titulos}. Nao foi ativado."
                )

        agora = datetime.datetime.utcnow()

        mongo.db.consents.update_one(
            {'aluno_id': aluno_oid},
            {'$set': {
                'aluno_id': aluno_oid,
                'finalidades': novo,
                'versao_termo': VERSAO_TERMO,
                'atualizado_em': agora,
                'atualizado_por': autor_oid,
            }},
            upsert=True,
        )

        # Rastro de auditoria: apenas o que mudou
        mudancas = {
            f: {'de': anterior.get(f, False), 'para': novo[f]}
            for f in FINALIDADES
            if anterior.get(f, False) != novo[f]
        }

        if mudancas:
            mongo.db.consent_events.insert_one({
                'aluno_id': aluno_oid,
                'autor_id': autor_oid,
                'mudancas': mudancas,
                'versao_termo': VERSAO_TERMO,
                'data_hora': agora,
                'ip': ip,
            })

        return novo, avisos

    def revogar_tudo(self, aluno_id, autor_id, ip=None):
        """Revoga todas as finalidades de uma vez."""
        return self.registrar(
            aluno_id, {f: False for f in FINALIDADES}, autor_id, ip
        )

    def historico(self, aluno_id, limite=100):
        """Rastro de auditoria do consentimento."""
        oid = _to_object_id(aluno_id)
        if oid is None:
            return []
        return list(
            mongo.db.consent_events.find({'aluno_id': oid})
            .sort('data_hora', -1)
            .limit(limite)
        )

    @staticmethod
    def termo_publico():
        """Texto das finalidades para exibir ao responsavel."""
        return {
            'versao': VERSAO_TERMO,
            'finalidades': [
                {
                    'id': fid,
                    'titulo': meta['titulo'],
                    'descricao': meta['descricao'],
                    'obrigatorio': meta['obrigatorio'],
                    'depende_de': meta['implica'],
                }
                for fid, meta in FINALIDADES.items()
            ],
        }

    @staticmethod
    def serializar_evento(evento):
        data_hora = evento.get('data_hora')
        return {
            '_id': str(evento.get('_id')),
            'aluno_id': str(evento.get('aluno_id')),
            'autor_id': str(evento.get('autor_id')),
            'mudancas': evento.get('mudancas', {}),
            'versao_termo': evento.get('versao_termo'),
            'data_hora': data_hora.isoformat() if data_hora else None,
        }
