"""Jornadas HTTP com SQLite e CSRF real; não executam navegador/JavaScript."""

from html import unescape
import re

import pytest
from werkzeug.http import http_date

from app import db
from app.models import Feedback, ProfessorChecklist, ProfessorTrilha, RoleEnum, StatusEnum
from app.services.task_service import TaskService
from app.services.trilha_service import TrilhaService
from tests.helpers import csrf_token_from_response, get_csrf_token, testHelper


@pytest.fixture
def send(app):
    assert app.config['SQLALCHEMY_DATABASE_URI'] == 'sqlite://'
    assert app.config['WTF_CSRF_ENABLED'] is True
    assert app.config['WTF_CSRF_CHECK_DEFAULT'] is True

    def request(browser, path, **kwargs):
        # A fixture app mantém um contexto externo. Isole g entre requisições
        # para não reutilizar current_user entre sessões de professor e admin.
        with app.app_context():
            return browser.open(path, **kwargs)

    return request


def rows(model):
    """Relê colunas persistidas, descartando objetos em cache da sessão ORM."""
    db.session.remove()
    return [dict(row) for row in db.session.execute(
        db.select(model.__table__).order_by(model.id)
    ).mappings()]


def test_jornada_inscricao_conclusao_e_reabertura(client, send):
    professor_id = testHelper.authenticate_user(client, RoleEnum.PROFESSOR).id
    trilha_id = TrilhaService.create_trilha('Jornada docente', obrigatoria=True).id
    task_ids = [TaskService.create_task(trilha_id, descricao, ordem=ordem).id
                for ordem, descricao in enumerate(('Primeira etapa', 'Segunda etapa'), 1)]
    assert rows(ProfessorTrilha) == []
    assert rows(ProfessorChecklist) == []

    response = send(client, f'/trilhas/{trilha_id}/start', method='POST', json={},
                    headers={'X-CSRFToken': get_csrf_token(client), 'Accept': 'application/json'})
    assert response.status_code == 201
    assert response.get_json()['trilha_id'] == trilha_id
    assert response.get_json()['status'] == 'em_andamento'
    enrollment, = rows(ProfessorTrilha)
    started_at = enrollment['data_inicio']
    assert started_at is not None

    def assert_state(completed_ids, recorded_ids):
        records = rows(ProfessorChecklist)
        assert len(records) == len(recorded_ids)
        assert {r['task_id'] for r in records} == set(recorded_ids)
        for record in records:
            assert record['professor_id'] == professor_id
            completed = record['task_id'] in completed_ids
            assert record['concluido'] is completed
            if completed:
                assert record['data_conclusao'] >= started_at
            else:
                assert record['data_conclusao'] is None

        current, = rows(ProfessorTrilha)
        status = StatusEnum.CONCLUIDO if len(completed_ids) == 2 else StatusEnum.EM_ANDAMENTO
        assert current['id'] == enrollment['id']
        assert current['professor_id'] == professor_id
        assert current['trilha_id'] == trilha_id
        assert current['data_inicio'] == started_at
        assert current['status'] == status
        if status == StatusEnum.CONCLUIDO:
            assert current['data_conclusao'] >= max(r['data_conclusao'] for r in records)
        else:
            assert current['data_conclusao'] is None

        response = send(client, f'/trilhas/{trilha_id}/progress',
                        headers={'Accept': 'application/json'})
        assert response.status_code == 200
        assert response.get_json() == {
            'total_tasks': 2, 'completed_tasks': len(completed_ids),
            'completion_percentage': len(completed_ids) * 50,
            'status': status.value, 'data_inicio': http_date(started_at),
            'data_conclusao': http_date(current['data_conclusao'])
            if current['data_conclusao'] else None,
        }
        response = send(client, '/professor/dashboard', headers={'Accept': 'application/json'})
        assert response.status_code == 200
        dashboard = response.get_json()
        assert dashboard['user']['id'] == professor_id
        expected_progress = {'total_tarefas': 2, 'tarefas_concluidas': len(completed_ids),
                             'percentual': len(completed_ids) * 50}
        assert dashboard['progresso_geral'] == expected_progress
        track, = dashboard['trilhas_atribuidas']
        assert track['id'] == trilha_id
        assert track['status'] == status.value
        assert track['progresso'] == expected_progress
        assert [(task['id'], task['status']) for task in track['tasks']] == [
            (task_id, 'concluido' if task_id in completed_ids else 'pendente')
            for task_id in task_ids
        ]
        assert [task['task_id'] for task in dashboard['proximas_tarefas']] == [
            task_id for task_id in task_ids if task_id not in completed_ids
        ]
        response = send(client, '/professor/dashboard', headers={'Accept': 'text/html'})
        assert response.status_code == 200
        assert (f'Progresso geral da jornada: {len(completed_ids) * 50}%, '
                f'{len(completed_ids)} de 2 tarefas concluídas') in response.get_data(as_text=True)

    def change_task(task_id, operation):
        page = send(client, f'/professor/tarefas/{task_id}')
        token = csrf_token_from_response(page)
        response = send(client, f'/tasks/{task_id}/{operation}', method='POST', json={},
                        headers={'Accept': 'application/json', 'X-CSRFToken': token})
        assert response.status_code == 200
        assert response.get_json()['task_id'] == task_id
        assert response.get_json()['concluido'] is (operation == 'complete')

    first, second = task_ids
    assert_state(set(), set())
    change_task(first, 'complete')
    assert_state({first}, {first})
    first_completion = rows(ProfessorChecklist)
    before_enrollment = rows(ProfessorTrilha)
    change_task(first, 'complete')
    assert_state({first}, {first})
    assert rows(ProfessorChecklist) == first_completion
    assert rows(ProfessorTrilha) == before_enrollment
    change_task(second, 'complete')
    assert_state({first, second}, {first, second})
    completed_records = rows(ProfessorChecklist)
    assert completed_records[0] == first_completion[0]
    change_task(first, 'incomplete')
    assert_state({second}, {first, second})
    reopened = rows(ProfessorChecklist)
    assert reopened[0]['id'] == completed_records[0]['id']
    assert reopened[1] == completed_records[1]


def test_jornada_feedback_geral_ate_consulta_administrativa(app, client, send):
    professor = testHelper.authenticate_user(client, RoleEnum.PROFESSOR)
    professor.nome = 'Docente da jornada'
    admin_client = app.test_client()
    admin = testHelper.authenticate_user(admin_client, RoleEnum.ADMIN)
    admin.nome = 'Administrador da jornada'
    db.session.commit()
    professor_id, admin_id = professor.id, admin.id
    assert rows(Feedback) == []

    page = send(client, '/professor/feedback', headers={'Accept': 'text/html'})
    token = csrf_token_from_response(page)
    assert '<option value="">Nenhuma / Geral</option>' in page.get_data(as_text=True)
    comment = 'As orientações facilitaram minha integração docente.'
    response = send(client, '/professor/feedback', method='POST',
                    headers={'Accept': 'text/html'},
                    data={'csrf_token': token, 'comentario': comment, 'trilha_id': ''})
    assert response.status_code == 302
    assert response.headers['Location'] == '/professor/dashboard'
    destination = send(client, response.headers['Location'], headers={'Accept': 'application/json'})
    assert destination.status_code == 200
    assert destination.get_json()['user']['id'] == professor_id

    feedback, = rows(Feedback)
    assert feedback['professor_id'] == professor_id
    assert feedback['trilha_id'] is None
    assert feedback['comentario'] == comment
    assert feedback['data_envio'] is not None

    response = send(admin_client, '/admin/tarefas-feedbacks')
    assert response.status_code == 200
    assert response.mimetype == 'text/html'
    cards = re.findall(r'<li class="info-box">(.*?)</li>',
                       response.get_data(as_text=True), flags=re.DOTALL)
    matching = [unescape(card) for card in cards if comment in unescape(card)]
    assert len(matching) == 1
    assert 'Enviado por Docente da jornada em' in matching[0]
    assert 'Administrador da jornada' not in matching[0]
    assert feedback['data_envio'].isoformat() in matching[0]
    assert rows(Feedback) == [feedback]
    for browser, user_id in ((client, professor_id), (admin_client, admin_id)):
        with browser.session_transaction() as session:
            assert session['_user_id'] == str(user_id)


@pytest.fixture
def management_clients(app, client):
    professor_id = testHelper.authenticate_user(client, RoleEnum.PROFESSOR).id
    admin_client = app.test_client()
    testHelper.authenticate_user(admin_client, RoleEnum.ADMIN)
    return client, admin_client, professor_id


def post_journey(send, browser, path, payload=None):
    return send(browser, path, method='POST', json=payload or {},
                headers={'Accept': 'application/json', 'X-CSRFToken': get_csrf_token(browser)})


def test_jornada_exclusao_trilha_com_associacoes(management_clients, send):
    from app.models import Checklist, Task, User

    professor, admin, professor_id = management_clients
    track_ids, tasks_by_track = [], {}
    for name in ('Trilha removida', 'Trilha de controle'):
        track_id = TrilhaService.create_trilha(name, obrigatoria=True).id
        track_ids.append(track_id)
        task_ids = [TaskService.create_task(track_id, f'{name}: etapa {order}', ordem=order).id
                    for order in (1, 2)]
        tasks_by_track[track_id] = task_ids
        assert post_journey(send, professor, f'/trilhas/{track_id}/start').status_code == 201
        assert post_journey(send, professor, f'/tasks/{task_ids[0]}/complete').status_code == 200
        assert post_journey(send, professor, '/professor/feedback', {
            'comentario': f'Feedback de {name}', 'trilha_id': track_id,
        }).status_code == 201

    removed, control = track_ids
    models = (User, Checklist, Task, ProfessorTrilha, ProfessorChecklist, Feedback)
    before = {model: rows(model) for model in models}
    assert len(before[ProfessorTrilha]) == len(before[ProfessorChecklist]) == len(before[Feedback]) == 2
    assert {r['professor_id'] for r in before[ProfessorTrilha]} == {professor_id}
    response = send(admin, f'/trilhas/{removed}', method='DELETE',
                    headers={'X-CSRFToken': get_csrf_token(admin)})
    assert response.status_code == 200
    assert response.get_json() == {'message': 'Trilha removida com sucesso'}
    after = {model: rows(model) for model in models}
    # Comparação de todas as colunas: nenhuma alteração colateral no controle.
    assert after == {
        User: before[User],
        Checklist: [r for r in before[Checklist] if r['id'] != removed],
        Task: [r for r in before[Task] if r['checklist_id'] != removed],
        ProfessorTrilha: [r for r in before[ProfessorTrilha] if r['trilha_id'] != removed],
        ProfessorChecklist: [r for r in before[ProfessorChecklist]
                             if r['task_id'] not in tasks_by_track[removed]],
        Feedback: [r for r in before[Feedback] if r['trilha_id'] != removed],
    }
    for path in (f'/trilhas/{removed}', f'/professor/trilhas/{removed}',
                 *(f'/professor/tarefas/{task_id}' for task_id in tasks_by_track[removed])):
        response = send(professor, path, headers={'Accept': 'application/json'})
        assert response.status_code == 404
    catalog = send(professor, '/trilhas/')
    assert catalog.status_code == 200
    assert [track['id'] for track in catalog.get_json()] == [control]
    response = send(professor, '/professor/dashboard', headers={'Accept': 'application/json'})
    assert response.status_code == 200
    dashboard = response.get_json()
    assert [track['id'] for track in dashboard['trilhas_atribuidas']] == [control]
    assert dashboard['progresso_geral'] == {
        'total_tarefas': 2, 'tarefas_concluidas': 1, 'percentual': 50,
    }
    response = send(admin, '/admin/tarefas-feedbacks')
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'Feedback de Trilha removida' not in html
    assert 'Feedback de Trilha de controle' in html


def test_jornada_edicao_tarefa_refletida_para_professor(management_clients, send):
    from app.models import Checklist, Task

    professor, admin, _ = management_clients
    track_id = TrilhaService.create_trilha('Conteúdo docente').id
    task_id = TaskService.create_task(
        track_id, 'Descrição anterior', ordem=3, material_apoio='Material anterior',
        link_apoio='https://example.test/anterior', documento_apoio='anterior.pdf',
    ).id
    before, = rows(Task)
    tracks_before = rows(Checklist)
    changes = {
        'descricao': 'Descrição revisada', 'material_apoio': 'Guia atualizado',
        'link_apoio': 'https://example.test/revisado', 'documento_apoio': 'revisado.pdf',
    }
    response = send(admin, f'/tasks/{task_id}', method='PATCH', json=changes,
                    headers={'X-CSRFToken': get_csrf_token(admin)})
    assert response.status_code == 200
    expected = {**before, **changes}
    assert response.get_json() == expected
    assert rows(Task) == [expected]  # Inclui id, ordem e checklist_id omitidos no PATCH.
    assert rows(Checklist) == tracks_before
    response = send(professor, f'/professor/tarefas/{task_id}', headers={'Accept': 'text/html'})
    assert response.status_code == 200
    html = unescape(response.get_data(as_text=True))
    for value in changes.values():
        assert value in html
    for field in changes:
        assert before[field] not in html
    assert f'href="/professor/trilhas/{track_id}"' in html
    response = send(professor, f'/professor/trilhas/{track_id}', headers={'Accept': 'application/json'})
    assert response.status_code == 200
    task, = response.get_json()['tasks']
    assert task['id'] == task_id
    assert task['ordem'] == before['ordem']
    assert task['status'] == 'pendente'
    assert {field: task[field] for field in changes} == changes


def test_jornada_exclusao_tarefa_concluida(management_clients, send):
    from app.models import Checklist, Task, User

    professor, admin, professor_id = management_clients
    track_id = TrilhaService.create_trilha('Trilha com tarefa removível', obrigatoria=True).id
    first, second = [TaskService.create_task(track_id, f'Etapa {order}', ordem=order).id
                     for order in (1, 2)]
    assert post_journey(send, professor, f'/trilhas/{track_id}/start').status_code == 201
    response = post_journey(send, professor, f'/tasks/{first}/complete')
    assert response.status_code == 200
    assert response.get_json()['concluido'] is True
    completion, = rows(ProfessorChecklist)
    assert completion['professor_id'] == professor_id
    assert completion['task_id'] == first
    assert completion['concluido'] is True
    assert completion['data_conclusao'] is not None
    # Outro professor também concluiu a tarefa alvo. Os controles abrangem
    # outra tarefa da mesma trilha e uma tarefa de uma trilha independente.
    other = User(nome='Docente de controle', email='controle@journey.test',
                 senha='nao-utilizada', role=RoleEnum.PROFESSOR)
    db.session.add(other)
    db.session.commit()
    other_id = other.id
    control_track = TrilhaService.create_trilha('Trilha independente').id
    control_task = TaskService.create_task(control_track, 'Tarefa de controle', ordem=4).id
    stamp = completion['data_conclusao']
    db.session.add_all([
        ProfessorChecklist(professor_id=other_id, task_id=first,
                           concluido=True, data_conclusao=stamp),
        ProfessorChecklist(professor_id=professor_id, task_id=second,
                           concluido=False, data_conclusao=None),
        ProfessorChecklist(professor_id=other_id, task_id=control_task,
                           concluido=True, data_conclusao=stamp),
        ProfessorTrilha(professor_id=other_id, trilha_id=control_track,
                        status=StatusEnum.CONCLUIDO, data_inicio=stamp, data_conclusao=stamp),
        Feedback(professor_id=other_id, trilha_id=control_track,
                 comentario='Feedback preservado', data_envio=stamp),
    ])
    db.session.commit()
    completions_before = rows(ProfessorChecklist)
    assert {r['professor_id'] for r in completions_before if r['task_id'] == first} == {
        professor_id, other_id,
    }
    controls = [r for r in completions_before if r['task_id'] != first]
    assert len(controls) == 2
    control_task_before = next(r for r in rows(Task) if r['id'] == control_task)
    feedbacks_before = rows(Feedback)
    users_before = rows(User)
    remaining_before = next(r for r in rows(Task) if r['id'] == second)
    enrollment_before = rows(ProfessorTrilha)
    tracks_before = rows(Checklist)
    response = send(professor, f'/trilhas/{track_id}/progress')
    assert response.status_code == 200
    assert response.get_json()['completion_percentage'] == 50

    response = send(admin, f'/tasks/{first}', method='DELETE',
                    headers={'X-CSRFToken': get_csrf_token(admin)})
    assert response.status_code == 200
    assert response.get_json() == {'message': 'Tarefa removida com sucesso'}
    assert rows(Task) == [{**remaining_before, 'ordem': 1}, control_task_before]
    assert rows(Checklist) == tracks_before
    assert rows(ProfessorTrilha) == enrollment_before
    assert rows(Feedback) == feedbacks_before
    assert rows(User) == users_before
    response = send(professor, f'/professor/tarefas/{first}')
    assert response.status_code == 404
    response = send(professor, f'/trilhas/{track_id}')
    assert response.status_code == 200
    remaining, = response.get_json()['tasks']
    assert remaining['id'] == second
    assert remaining['ordem'] == 1
    response = send(professor, f'/trilhas/{track_id}/progress')
    assert response.status_code == 200
    progress = response.get_json()
    assert progress['total_tasks'] == 1
    assert progress['completed_tasks'] == 0
    assert progress['completion_percentage'] == 0
    assert progress['status'] == 'em_andamento'
    assert progress['data_conclusao'] is None
    response = send(professor, '/professor/dashboard', headers={'Accept': 'application/json'})
    assert response.status_code == 200
    assert response.get_json()['progresso_geral'] == {
        'total_tarefas': 1, 'tarefas_concluidas': 0, 'percentual': 0,
    }
    # Mesmo se o SQLite não aplicar FKs, exigimos integridade nos dados persistidos.
    completions_after = rows(ProfessorChecklist)
    assert not any(r['task_id'] == first for r in completions_after), 'Conclusão órfã após exclusão'
    assert completions_after == controls
    assert {r['task_id'] for r in completions_after} <= {r['id'] for r in rows(Task)}
