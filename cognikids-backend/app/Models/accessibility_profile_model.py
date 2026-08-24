"""
Perfil funcional de acessibilidade de um aluno.

Guarda as respostas do responsavel sobre necessidades observaveis e os
ajustes que a propria crianca fez no painel de conforto. Os tokens de
interface sao derivados (nunca persistidos como fonte de verdade), para que
mudancas no catalogo se apliquem a perfis ja existentes.

Nao armazena diagnostico — ver app/Utils/accessibility.py para o porque.
"""

import datetime

from bson.objectid import ObjectId

from app import mongo
from app.Utils.accessibility import (
    AJUSTAVEIS_PELA_CRIANCA,
    dimensoes_atendidas,
    resolver_tokens,
    respostas_sem_efeito,
)


def _to_object_id(valor):
    if isinstance(valor, ObjectId):
        return valor
    try:
        return ObjectId(valor)
    except Exception:
        return None


class AccessibilityProfile:
    def obter(self, aluno_id):
        oid = _to_object_id(aluno_id)
        if oid is None:
            return None
        return mongo.db.accessibility_profiles.find_one({'aluno_id': oid})

    def salvar_respostas(self, aluno_id, respostas, autor_id):
        """Grava as respostas do responsavel (linha de base do perfil)."""
        aluno_oid = _to_object_id(aluno_id)
        autor_oid = _to_object_id(autor_id)
        if aluno_oid is None or autor_oid is None:
            raise ValueError('IDs invalidos ao salvar perfil de acessibilidade')

        return mongo.db.accessibility_profiles.update_one(
            {'aluno_id': aluno_oid},
            {'$set': {
                'aluno_id': aluno_oid,
                'respostas': respostas,
                'atualizado_em': datetime.datetime.utcnow(),
                'atualizado_por': autor_oid,
            },
             '$setOnInsert': {'ajustes_crianca': {}}},
            upsert=True,
        )

    def salvar_ajustes_crianca(self, aluno_id, ajustes):
        """Grava as preferencias que a propria crianca escolheu.

        Apenas os tokens de AJUSTAVEIS_PELA_CRIANCA sao aceitos: os demais
        protegem a crianca e nao podem ser desfeitos por um toque acidental.
        """
        aluno_oid = _to_object_id(aluno_id)
        if aluno_oid is None:
            raise ValueError('ID invalido ao salvar ajustes')

        filtrados = {
            k: v for k, v in (ajustes or {}).items()
            if k in AJUSTAVEIS_PELA_CRIANCA
        }

        return mongo.db.accessibility_profiles.update_one(
            {'aluno_id': aluno_oid},
            {'$set': {
                'aluno_id': aluno_oid,
                'ajustes_crianca': filtrados,
                'ajustes_atualizados_em': datetime.datetime.utcnow(),
            }},
            upsert=True,
        )

    def tokens(self, aluno_id):
        """Tokens de interface finais para este aluno.

        Sem perfil preenchido, devolve os padroes conservadores.
        """
        perfil = self.obter(aluno_id) or {}
        return resolver_tokens(
            perfil.get('respostas', {}),
            perfil.get('ajustes_crianca', {}),
        )

    def serializar(self, aluno_id):
        perfil = self.obter(aluno_id) or {}
        respostas = perfil.get('respostas', {})
        atualizado = perfil.get('atualizado_em')

        return {
            'aluno_id': str(aluno_id),
            'configurado': bool(respostas),
            'respostas': respostas,
            'ajustes_crianca': perfil.get('ajustes_crianca', {}),
            'tokens': resolver_tokens(respostas, perfil.get('ajustes_crianca', {})),
            'dimensoes': dimensoes_atendidas(respostas),
            # O que o responsavel respondeu e nao produziu efeito. Sem isso a
            # UI nao tem como mostrar a divergencia entre declarado e aplicado.
            'respostas_sem_efeito': respostas_sem_efeito(respostas),
            'ajustaveis_pela_crianca': list(AJUSTAVEIS_PELA_CRIANCA),
            'atualizado_em': atualizado.isoformat() if atualizado else None,
        }
