"""
Consentimento granular (LGPD).

Cobre o que sustenta a base legal do sistema: quem pode consentir, o efeito
imediato da revogacao sobre a coleta, e a auditabilidade das mudancas.
"""

import pytest


class TestTermo:
    def test_lista_finalidades(self, responsavel):
        r = responsavel.get('/api/consent/terms')
        assert r.status_code == 200

        dados = r.get_json()['data']
        ids = {f['id'] for f in dados['finalidades']}
        assert ids == {
            'uso_app', 'coleta_biometrica', 'compartilhar_escola', 'uso_pesquisa'
        }

    def test_cada_finalidade_tem_descricao_em_linguagem_simples(self, responsavel):
        dados = responsavel.get('/api/consent/terms').get_json()['data']
        for finalidade in dados['finalidades']:
            assert finalidade['descricao']
            assert finalidade['titulo']


class TestConcessao:
    def test_responsavel_concede(self, vinculo_responsavel, estudante):
        r = vinculo_responsavel.put(f'/api/consent/{estudante.id}', json={
            'finalidades': {'uso_app': True, 'coleta_biometrica': True},
        })
        assert r.status_code == 200

        finalidades = r.get_json()['data']['finalidades']
        assert finalidades['uso_app'] is True
        assert finalidades['coleta_biometrica'] is True

    def test_negar_por_padrao(self, vinculo_responsavel, estudante):
        """Sem consentimento registrado, nada esta autorizado."""
        r = vinculo_responsavel.get(f'/api/consent/{estudante.id}')
        assert r.status_code == 200
        assert all(v is False for v in r.get_json()['data']['finalidades'].values())

    def test_dependencia_bloqueia_finalidade(self, vinculo_responsavel, estudante):
        """Coleta biometrica sem uso do app nao pode ser ativada."""
        r = vinculo_responsavel.put(f'/api/consent/{estudante.id}', json={
            'finalidades': {'uso_app': False, 'coleta_biometrica': True},
        })
        assert r.status_code == 200
        assert r.get_json()['data']['finalidades']['coleta_biometrica'] is False
        assert r.get_json()['avisos']

    def test_recusar_pesquisa_nao_impede_o_resto(self, vinculo_responsavel, estudante):
        """Recusa de pesquisa nao pode ter consequencia — exigencia etica."""
        r = vinculo_responsavel.put(f'/api/consent/{estudante.id}', json={
            'finalidades': {
                'uso_app': True, 'coleta_biometrica': True, 'uso_pesquisa': False,
            },
        })
        finalidades = r.get_json()['data']['finalidades']
        assert finalidades['uso_app'] is True
        assert finalidades['coleta_biometrica'] is True
        assert finalidades['uso_pesquisa'] is False

    def test_rejeita_finalidade_desconhecida(self, vinculo_responsavel, estudante):
        r = vinculo_responsavel.put(f'/api/consent/{estudante.id}', json={
            'finalidades': {'vender_dados': True},
        })
        assert r.status_code == 400


class TestQuemPodeConsentir:
    def test_professor_nao_concede(self, professor, turma, estudante):
        r = professor.put(f'/api/consent/{estudante.id}',
                          json={'finalidades': {'uso_app': True}})
        assert r.status_code == 403

    def test_aluno_nao_concede_por_si(self, estudante):
        r = estudante.put(f'/api/consent/{estudante.id}',
                          json={'finalidades': {'uso_app': True}})
        assert r.status_code == 403

    def test_responsavel_nao_concede_por_filho_alheio(self, responsavel, estudante):
        r = responsavel.put(f'/api/consent/{estudante.id}',
                            json={'finalidades': {'uso_app': True}})
        assert r.status_code == 403


class TestRevogacao:
    def test_revogar_tudo(self, vinculo_responsavel, estudante):
        vinculo_responsavel.put(f'/api/consent/{estudante.id}', json={
            'finalidades': {'uso_app': True, 'coleta_biometrica': True},
        })

        r = vinculo_responsavel.delete(f'/api/consent/{estudante.id}')
        assert r.status_code == 200
        assert all(v is False for v in r.get_json()['data']['finalidades'].values())

    def test_revogacao_interrompe_ingestao_imediatamente(
        self, client, api_key_headers, vinculo_responsavel, estudante, dispositivo, db
    ):
        """O efeito precisa ser imediato — art. 8o, §5o."""
        antes = client.post('/api/iot/data', headers=api_key_headers, json={
            'dispositivo_id': str(dispositivo),
            'dados_biometricos': {'bpm': 90},
        })
        assert antes.status_code == 201

        vinculo_responsavel.delete(f'/api/consent/{estudante.id}')

        depois = client.post('/api/iot/data', headers=api_key_headers, json={
            'dispositivo_id': str(dispositivo),
            'dados_biometricos': {'bpm': 90},
        })
        assert depois.status_code == 403
        assert db.registros_iot.count_documents({}) == 1


class TestEnforcementDaColeta:
    def test_ingestao_bloqueada_sem_consentimento(
        self, client, api_key_headers, estudante, db
    ):
        db.consents.delete_many({})
        dispositivo_id = db.dispositivos.insert_one({
            'aluno_id': estudante.oid, 'status': 'ativo',
        }).inserted_id

        r = client.post('/api/iot/data', headers=api_key_headers, json={
            'dispositivo_id': str(dispositivo_id),
            'dados_biometricos': {'bpm': 95},
        })
        assert r.status_code == 403
        assert db.registros_iot.count_documents({}) == 0

    def test_ingestao_liberada_com_consentimento(
        self, client, api_key_headers, estudante, dispositivo, db
    ):
        r = client.post('/api/iot/data', headers=api_key_headers, json={
            'dispositivo_id': str(dispositivo),
            'dados_biometricos': {'bpm': 95},
        })
        assert r.status_code == 201
        assert db.registros_iot.count_documents({}) == 1


class TestEnforcementDoCompartilhamento:
    def test_professor_nao_ve_aluno_sem_consentimento(
        self, professor, turma, estudante, db
    ):
        """Vinculo pedagogico nao basta: precisa de base legal."""
        db.consents.update_one(
            {'aluno_id': estudante.oid},
            {'$set': {'finalidades.compartilhar_escola': False}},
        )

        r = professor.get('/api/teachers/all_students')
        assert r.status_code == 200
        assert r.get_json()['data'] == []

    def test_professor_nao_le_alertas_sem_consentimento(
        self, professor, turma, estudante, alerta, db
    ):
        db.consents.update_one(
            {'aluno_id': estudante.oid},
            {'$set': {'finalidades.compartilhar_escola': False}},
        )

        assert professor.get(
            f'/api/teachers/students/{estudante.id}/alerts_history'
        ).status_code == 403

    def test_professor_volta_a_ver_apos_reconsentimento(
        self, professor, turma, estudante, db
    ):
        db.consents.update_one(
            {'aluno_id': estudante.oid},
            {'$set': {'finalidades.compartilhar_escola': False}},
        )
        assert professor.get('/api/teachers/all_students').get_json()['data'] == []

        db.consents.update_one(
            {'aluno_id': estudante.oid},
            {'$set': {'finalidades.compartilhar_escola': True}},
        )
        assert professor.get('/api/teachers/all_students').get_json()['total'] == 1

    def test_responsavel_ve_o_filho_independente_do_compartilhamento(
        self, vinculo_responsavel, estudante, db
    ):
        """Revogar o compartilhamento com a escola nao afeta a familia."""
        db.consents.update_one(
            {'aluno_id': estudante.oid},
            {'$set': {'finalidades.compartilhar_escola': False}},
            upsert=True,
        )
        assert vinculo_responsavel.get('/api/parents/children').get_json()['total'] == 1


class TestAuditoria:
    def test_registra_historico_de_mudancas(self, vinculo_responsavel, estudante):
        vinculo_responsavel.put(f'/api/consent/{estudante.id}',
                                json={'finalidades': {'uso_app': True}})
        vinculo_responsavel.delete(f'/api/consent/{estudante.id}')

        r = vinculo_responsavel.get(f'/api/consent/{estudante.id}/history')
        assert r.status_code == 200
        assert len(r.get_json()['data']) == 2

    def test_historico_registra_de_para(self, vinculo_responsavel, estudante):
        vinculo_responsavel.put(f'/api/consent/{estudante.id}',
                                json={'finalidades': {'uso_app': True}})

        evento = vinculo_responsavel.get(
            f'/api/consent/{estudante.id}/history'
        ).get_json()['data'][0]

        assert evento['mudancas']['uso_app'] == {'de': False, 'para': True}
        assert evento['autor_id']
        assert evento['data_hora']

    def test_professor_nao_acessa_historico(self, professor, turma, estudante):
        assert professor.get(
            f'/api/consent/{estudante.id}/history'
        ).status_code == 403
