"""AC01–AC05: autorização HTTP e isolamento, sem testar login por senha.

Os IDs e payloads são válidos: uma validação de entrada não deve mascarar
uma autorização ausente. Cada comparação relê todas as colunas do banco.
"""

from copy import deepcopy
from datetime import datetime
from html import unescape
from urllib.parse import parse_qs, urlsplit

import pytest
from werkzeug.http import http_date
from tests.helpers import csrf_token_from_response, get_csrf_token

from app import db
from app.models import (
    Checklist, Feedback, ProfessorChecklist, ProfessorTrilha,
    RoleEnum, StatusEnum, Task, TipoEnum, User,
)


ADMIN_ROUTES = [
    ("GET", "/admin/"),
    ("GET", "/admin/analytics"),
    ("GET", "/admin/professores"),
    ("GET", "/admin/trilhas"),
    ("GET", "/admin/tarefas-feedbacks"),
    ("POST", "/admin/professores"),
    ("PUT", "/admin/professores/{a}"),
    ("PATCH", "/admin/professores/{a}"),
    ("GET", "/admin/professores/{a}/editar"),
    ("GET", "/admin/professores/novo"),
    ("GET", "/admin/professores/{a}"),
    ("GET", "/admin/professores/{a}/trilhas"),
    ("PUT", "/admin/professores/{a}/trilhas"),
    ("GET", "/admin/trilhas/{track}/professores"),
    ("PUT", "/admin/trilhas/{track}/professores"),
    ("GET", "/admin/trilhas/{track}/conteudo"),
    ("GET", "/admin/trilhas/{track}/tarefas/nova"),
    ("GET", "/admin/trilhas/{track}/editar"),
    ("GET", "/admin/tarefas/{task}/editar"),
    ("POST", "/trilhas/"),
    ("PUT", "/trilhas/{track}"),
    ("PATCH", "/trilhas/{track}"),
    ("DELETE", "/trilhas/{track}"),
    ("POST", "/trilhas/{track}/tasks"),
    ("PUT", "/tasks/{task}"),
    ("PATCH", "/tasks/{task}"),
    ("DELETE", "/tasks/{task}"),
    ("POST", "/tasks/trilhas/{track}/reorder"),
]
PROFESSOR_ROUTES = [
    ("GET", "/professor/dashboard"),
    ("GET", "/professor/trilhas"),
    ("GET", "/professor/trilhas/{track}"),
    ("GET", "/professor/tarefas/{task}"),
    ("GET", "/professor/feedback"),
    ("POST", "/professor/feedback"),
    ("POST", "/trilhas/{available}/start"),
    ("GET", "/trilhas/{track}/progress"),
    ("POST", "/tasks/{task}/complete"),
    ("POST", "/tasks/{task}/incomplete"),
    ("GET", "/tasks/{task}/status"),
]
SHARED_ROUTES = [("GET", "/trilhas/"), ("GET", "/trilhas/{track}")]
MODELS = (User, Checklist, Task, ProfessorTrilha, ProfessorChecklist, Feedback)
STAMP = datetime(2026, 1, 10, 12, 0)


@pytest.fixture
def permission_data(app):
    """Dois professores com estados opostos na mesma tarefa e trilhas próprias."""
    users = {
        key: User(nome=f"Pessoa {key}", email=f"{key}@permissoes.test",
                  senha="nao-usada-nestes-testes", role=role)
        for key, role in (("admin", RoleEnum.ADMIN),
                          ("a", RoleEnum.PROFESSOR), ("b", RoleEnum.PROFESSOR))
    }
    tracks = {
        key: Checklist(nome=f"Trilha {key}", descricao=f"Conteudo {key}",
                       tipo=TipoEnum.PEDAGOGICA, obrigatoria=True)
        for key in ("track", "only_a", "only_b", "available")
    }
    db.session.add_all([*users.values(), *tracks.values()])
    db.session.flush()
    tasks = {
        "task": Task(descricao="Tarefa compartilhada", ordem=1,
                     checklist_id=tracks["track"].id,
                     material_apoio="Material", link_apoio="https://example.test/apoio",
                     documento_apoio="Documento"),
        "task_a": Task(descricao="Tarefa A", ordem=1, checklist_id=tracks["only_a"].id),
        "task_b": Task(descricao="Tarefa B", ordem=1, checklist_id=tracks["only_b"].id),
    }
    db.session.add_all(tasks.values())
    db.session.flush()
    for key, user in users.items():
        completed = key != "a"
        db.session.add(ProfessorTrilha(
            professor_id=user.id, trilha_id=tracks["track"].id,
            status=StatusEnum.CONCLUIDO if completed else StatusEnum.EM_ANDAMENTO,
            data_inicio=STAMP, data_conclusao=STAMP if completed else None,
        ))
        db.session.add(ProfessorChecklist(
            professor_id=user.id, task_id=tasks["task"].id,
            concluido=completed, data_conclusao=STAMP if completed else None,
        ))
        db.session.add(Feedback(professor_id=user.id, trilha_id=tracks["track"].id,
                                comentario=f"Feedback privado {key}", data_envio=STAMP))
    for key in ("a", "b"):
        db.session.add(ProfessorTrilha(
            professor_id=users[key].id, trilha_id=tracks[f"only_{key}"].id,
            status=StatusEnum.EM_ANDAMENTO, data_inicio=STAMP,
        ))
    db.session.commit()
    return {key: item.id for key, item in {**users, **tracks, **tasks}.items()}


def authenticate(client, user_id):
    # Mesmo mecanismo do helper existente, reutilizando usuários da fixture.
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True


def snapshot():
    """Descarta o identity map e compara dados persistidos, não objetos em cache."""
    db.session.remove()
    return {
        model.__tablename__: [dict(row) for row in db.session.execute(
            db.select(model.__table__).order_by(model.id)
        ).mappings()]
        for model in MODELS
    }


def request_route(client, method, path, data, transport):
    payload = {
        "nome": "Alterado", "email": "novo@permissoes.test", "senha": "nova-senha",
        "descricao": "Alterada", "tipo": "institucional", "obrigatoria": "false",
        "ordem": 2, "comentario": "Novo feedback", "trilha_id": data["track"],
        "task_ids": f"{data['reorder_task']},{data['task']}" if "reorder_task" in data else str(data["task"]),
    }
    kwargs = {"headers": {"Accept": "application/json" if transport == "json" else "text/html"}}
    if method in ("POST", "PUT", "PATCH", "DELETE"):
        kwargs["headers"]["X-CSRFToken"] = get_csrf_token(client)
    if method in ("POST", "PUT", "PATCH"):
        kwargs["json" if transport == "json" else "data"] = payload
    return client.open(path.format(**data), method=method, **kwargs)


def prepare_observable_denial(data, path):
    """As operações proibidas devem ter efeito caso sejam executadas."""
    if path.endswith("/reorder"):
        task = Task(descricao="Segunda tarefa para reordenar", ordem=2,
                    checklist_id=data["track"])
        db.session.add(task)
        db.session.commit()
        data["reorder_task"] = task.id
    if path.endswith("/complete"):
        record = ProfessorChecklist.query.filter_by(
            professor_id=data["admin"], task_id=data["task"]
        ).one()
        record.concluido = False
        record.data_conclusao = None
        enrollment = ProfessorTrilha.query.filter_by(
            professor_id=data["admin"], trilha_id=data["track"]
        ).one()
        enrollment.status = StatusEnum.EM_ANDAMENTO
        enrollment.data_conclusao = None
        db.session.commit()


@pytest.mark.parametrize("method,path", ADMIN_ROUTES + PROFESSOR_ROUTES + SHARED_ROUTES)
@pytest.mark.parametrize("transport", ["json", "form"])
def test_ac01_anonymous_cannot_access_protected_routes(client, permission_data, method, path, transport):
    prepare_observable_denial(permission_data, path)
    before = snapshot()
    response = request_route(client, method, path, permission_data, transport)
    assert response.status_code == 302
    location = urlsplit(response.headers["Location"])
    assert location.path == "/auth/login"
    assert parse_qs(location.query)["next"] == [path.format(**permission_data)]
    with client.session_transaction() as session:
        assert "_user_id" not in session
    assert snapshot() == before


@pytest.mark.parametrize("method,path", ADMIN_ROUTES + [
    (method, f"/admin/professores/{{{target}}}")
    for target in ("b", "admin") for method in ("PUT", "PATCH")
])
@pytest.mark.parametrize("transport", ["json", "form"])
def test_ac02_professor_cannot_access_admin_operations(client, permission_data, method, path, transport):
    authenticate(client, permission_data["a"])
    prepare_observable_denial(permission_data, path)
    before = snapshot()
    response = request_route(client, method, path, permission_data, transport)
    assert response.status_code == 403
    if path == "/admin/":
        assert response.get_data(as_text=True) == "Acesso negado"
    else:
        assert response.get_json() == {"error": "Acesso negado"}
    assert snapshot() == before


@pytest.mark.parametrize("method,path", PROFESSOR_ROUTES)
@pytest.mark.parametrize("transport", ["json", "form"])
def test_ac03_admin_cannot_access_professor_operations(client, permission_data, method, path, transport):
    authenticate(client, permission_data["admin"])
    prepare_observable_denial(permission_data, path)
    before = snapshot()
    response = request_route(client, method, path, permission_data, transport)
    assert response.status_code == 403
    assert response.get_json() == {"error": "Acesso negado"}
    assert snapshot() == before


@pytest.mark.parametrize("actor", ["admin", "a"])
@pytest.mark.parametrize("method,path", SHARED_ROUTES)
def test_ac04_shared_catalog_is_available_to_both_roles(client, permission_data, actor, method, path):
    d = permission_data
    authenticate(client, d[actor])
    before = snapshot()
    response = request_route(client, method, path, d, "json")
    assert response.status_code == 200
    body = response.get_json()
    if path == "/trilhas/":
        assert {item["id"] for item in body} == {d[k] for k in ("track", "only_a", "only_b", "available")}
        body = next(item for item in body if item["id"] == d["track"])
    assert body == {
        "id": d["track"], "nome": "Trilha track", "descricao": "Conteudo track",
        "tipo": "pedagógica", "obrigatoria": True,
        "tasks": [{"id": d["task"], "descricao": "Tarefa compartilhada", "ordem": 1,
                   "material_apoio": "Material", "link_apoio": "https://example.test/apoio",
                   "documento_apoio": "Documento"}],
    }
    assert snapshot() == before


def assert_no_private_leaks(response, actor):
    """Catálogo é compartilhado; nomes, e-mails, senhas e feedbacks não são."""
    text = unescape(response.get_data(as_text=True))
    for other in ({"a", "b", "admin"} - {actor}):
        assert f"Pessoa {other}" not in text
        assert f"{other}@permissoes.test" not in text
    for user in ("a", "b", "admin"):
        assert f"Feedback privado {user}" not in text
    assert "nao-usada-nestes-testes" not in text


def expected_task(data, actor, own=False):
    return {
        "id": data[f"task_{actor}" if own else "task"],
        "descricao": f"Tarefa {actor.upper()}" if own else "Tarefa compartilhada",
        "ordem": 1,
        "status": "concluido" if actor == "b" and not own else "pendente",
        "material_apoio": None if own else "Material",
        "link_apoio": None if own else "https://example.test/apoio",
        "documento_apoio": None if own else "Documento",
    }


def expected_trilha(data, actor, own=False):
    key = f"only_{actor}" if own else "track"
    completed = actor == "b" and not own
    return {
        "id": data[key], "nome": f"Trilha {key}", "descricao": f"Conteudo {key}",
        "tipo": "pedagógica", "obrigatoria": True,
        "status": "concluido" if completed else "em_andamento",
        "progresso": {"total_tarefas": 1, "tarefas_concluidas": int(completed),
                      "percentual": 100.0 if completed else 0.0},
        "tasks": [expected_task(data, actor, own)],
    }


@pytest.mark.parametrize("actor", ["a", "b"])
@pytest.mark.parametrize("view", ["dashboard", "trilha", "tarefa", "status", "progress", "other_progress", "feedback"])
def test_ac05_reads_use_the_authenticated_professor(client, permission_data, actor, view):
    d = permission_data
    other = "b" if actor == "a" else "a"
    authenticate(client, d[actor])
    before = snapshot()
    paths = {
        "dashboard": "/professor/dashboard", "trilha": f"/professor/trilhas/{d['track']}",
        "tarefa": f"/professor/tarefas/{d['task']}", "status": f"/tasks/{d['task']}/status",
        "progress": f"/trilhas/{d['track']}/progress",
        "other_progress": f"/trilhas/{d[f'only_{other}']}/progress",
        "feedback": "/professor/feedback",
    }
    response = client.get(paths[view], query_string={"professor_id": d[other], "user_id": d[other]},
                          headers={"Accept": "application/json"})
    body = response.get_json()
    assert_no_private_leaks(response, actor)
    completed = actor == "b"
    if view == "other_progress":
        assert response.status_code == 400
        assert body == {"error": f"Professor {d[actor]} not enrolled in trilha {d[f'only_{other}']}"}
    else:
        assert response.status_code == 200
        if view == "dashboard":
            assert set(body) == {"user", "trilhas_atribuidas", "progresso_geral",
                                 "proximas_tarefas", "trilhas_obrigatorias"}
            assert body["user"] == {"id": d[actor], "nome": f"Pessoa {actor}",
                                    "email": f"{actor}@permissoes.test", "role": "professor"}
            assert body["progresso_geral"] == {"total_tarefas": 2, "tarefas_concluidas": int(completed),
                                                "percentual": 50.0 if completed else 0.0}
            assert sorted(body["trilhas_atribuidas"], key=lambda item: item["id"]) == sorted(
                [expected_trilha(d, actor), expected_trilha(d, actor, own=True)],
                key=lambda item: item["id"],
            )
            expected_pending = [{"task_id": d[f"task_{actor}"],
                                 "descricao": f"Tarefa {actor.upper()}",
                                 "trilha_id": d[f"only_{actor}"]}]
            if not completed:
                expected_pending.insert(0, {"task_id": d["task"],
                                           "descricao": "Tarefa compartilhada", "trilha_id": d["track"]})
            assert body["proximas_tarefas"] == expected_pending
            assert sorted(body["trilhas_obrigatorias"], key=lambda item: item["id"]) == sorted(
                [{"id": d["track"], "nome": "Trilha track",
                  "status": "concluido" if completed else "em_andamento"},
                 {"id": d[f"only_{actor}"], "nome": f"Trilha only_{actor}", "status": "em_andamento"}],
                key=lambda item: item["id"],
            )
        elif view == "trilha":
            assert body == expected_trilha(d, actor)
        elif view == "tarefa":
            expected = expected_task(d, actor)
            expected.pop("ordem")
            expected["checklist_id"] = d["track"]
            assert body == expected
        elif view == "status":
            assert body == {"task_id": d["task"], "concluido": completed,
                            "data_conclusao": http_date(STAMP) if completed else None}
        elif view == "progress":
            assert body == {"status": "concluido" if completed else "em_andamento",
                            "total_tasks": 1, "completed_tasks": int(completed),
                            "completion_percentage": 100.0 if completed else 0.0,
                            "data_inicio": http_date(STAMP),
                            "data_conclusao": http_date(STAMP) if completed else None}
        elif view == "feedback":
            assert body == {
                "message": "Formulário de feedback disponível",
                "campos": ["comentario", "trilha_id (opcional)"],
                "trilhas_disponiveis": [{"id": d[key], "nome": f"Trilha {key}"}
                                        for key in ("available", "only_a", "only_b", "track")],
            }
    assert snapshot() == before


@pytest.mark.parametrize("actor", ["a", "b"])
@pytest.mark.parametrize("view", ["dashboard", "trilha", "tarefa", "feedback"])
def test_ac05_html_preserves_personal_isolation(client, permission_data, actor, view):
    d = permission_data
    other = "b" if actor == "a" else "a"
    authenticate(client, d[actor])
    before = snapshot()
    paths = {"dashboard": "/professor/dashboard", "trilha": f"/professor/trilhas/{d['track']}",
             "tarefa": f"/professor/tarefas/{d['task']}", "feedback": "/professor/feedback"}
    response = client.get(paths[view], headers={"Accept": "text/html"},
                          query_string={"professor_id": d[other], "user_id": d[other]})
    assert response.status_code == 200
    assert response.mimetype == "text/html"
    assert_no_private_leaks(response, actor)
    html = unescape(response.get_data(as_text=True))
    completed = actor == "b"
    if view == "dashboard":
        assert f"Pessoa {actor}" in html
        assert f"Trilha only_{actor}" in html
        assert f"Trilha only_{other}" not in html
        assert f"Tarefa {other.upper()}" not in html
        assert f"Progresso geral da jornada: {50 if completed else 0}%, {int(completed)} de 2 tarefas concluídas" in html
    elif view == "trilha":
        assert "Trilha track" in html
        assert f"Progresso da trilha: {100 if completed else 0}%, {int(completed)} de 1 tarefas concluídas" in html
        label = "Ver tarefa concluída" if completed else "Abrir tarefa pendente"
        opposite = "Abrir tarefa pendente" if completed else "Ver tarefa concluída"
        assert f"{label}: Tarefa compartilhada" in html
        assert f"{opposite}: Tarefa compartilhada" not in html
    elif view == "tarefa":
        assert "Tarefa compartilhada" in html
        action, opposite = ("incomplete", "complete") if completed else ("complete", "incomplete")
        assert f'action="/tasks/{d["task"]}/{action}"' in html
        assert f'action="/tasks/{d["task"]}/{opposite}"' not in html
    else:
        # O formulário pode listar trilhas não inscritas; isso não é vazamento pessoal.
        for key in ("available", "only_a", "only_b", "track"):
            assert f'<option value="{d[key]}">Trilha {key}</option>' in html
    assert snapshot() == before


@pytest.mark.parametrize("operation,actor", [("complete", "a"), ("incomplete", "b"),
                                            ("first_complete", "a"),
                                            ("start", "a"), ("feedback", "a")])
@pytest.mark.parametrize("transport", ["json", "form"])
def test_ac05_mutations_ignore_forged_professor_id(client, permission_data, operation, actor, transport):
    d = permission_data
    other = "b" if actor == "a" else "a"
    authenticate(client, d[actor])
    completion_operation = operation in ("complete", "first_complete", "incomplete")
    if completion_operation:
        initially_complete = operation == "incomplete"
        # O outro professor precisa sofrer uma mudança observável se o filtro
        # de autoria desaparecer. Preserve também uma tarefa distinta do ator.
        for owner in (actor, other):
            record = ProfessorChecklist.query.filter_by(
                professor_id=d[owner], task_id=d["task"]
            ).one()
            record.concluido = initially_complete
            record.data_conclusao = STAMP if initially_complete else None
            enrollment = ProfessorTrilha.query.filter_by(
                professor_id=d[owner], trilha_id=d["track"]
            ).one()
            enrollment.status = StatusEnum.CONCLUIDO if initially_complete else StatusEnum.EM_ANDAMENTO
            enrollment.data_conclusao = STAMP if initially_complete else None
        db.session.add(ProfessorChecklist(
            professor_id=d[actor], task_id=d[f"task_{actor}"],
            concluido=initially_complete, data_conclusao=STAMP if initially_complete else None,
        ))
        own_enrollment = ProfessorTrilha.query.filter_by(
            professor_id=d[actor], trilha_id=d[f"only_{actor}"]
        ).one()
        own_enrollment.status = StatusEnum.CONCLUIDO if initially_complete else StatusEnum.EM_ANDAMENTO
        own_enrollment.data_conclusao = STAMP if initially_complete else None
        if operation == "first_complete":
            record = ProfessorChecklist.query.filter_by(
                professor_id=d[actor], task_id=d["task"]
            ).one()
            db.session.delete(record)
        db.session.commit()
    before = snapshot()
    paths = {"complete": f"/tasks/{d['task']}/complete", "incomplete": f"/tasks/{d['task']}/incomplete",
             "first_complete": f"/tasks/{d['task']}/complete",
             "start": f"/trilhas/{d['available']}/start", "feedback": "/professor/feedback"}
    payload = {"professor_id": d[other], "user_id": d[other],
               "comentario": "Feedback com autor forjado", "trilha_id": d["track"]}
    response = client.post(paths[operation], headers={"Accept": "application/json",
                                                    "X-CSRFToken": get_csrf_token(client)},
                           **{"json" if transport == "json" else "data": payload})
    assert response.status_code == (201 if operation in ("start", "feedback") else 200)
    body = response.get_json()
    after = snapshot()
    for table in ("users", "checklists", "tasks"):
        assert after[table] == before[table]
    for table in ("professor_trilhas", "professor_checklists", "feedbacks"):
        assert [r for r in after[table] if r["professor_id"] != d[actor]] == [
            r for r in before[table] if r["professor_id"] != d[actor]
        ]
    if completion_operation:
        completed = operation != "incomplete"
        assert body["task_id"] == d["task"]
        assert body["concluido"] is completed
        records = [r for r in after["professor_checklists"]
                   if r["professor_id"] == d[actor] and r["task_id"] == d["task"]]
        assert len(records) == 1
        record = records[0]
        assert record["concluido"] is completed
        assert (record["data_conclusao"] is not None) is completed
        enrollment = next(r for r in after["professor_trilhas"]
                          if r["professor_id"] == d[actor] and r["trilha_id"] == d["track"])
        assert enrollment["status"] == (StatusEnum.CONCLUIDO if completed else StatusEnum.EM_ANDAMENTO)
        assert (enrollment["data_conclusao"] is not None) is completed
        # Só estado e data final podem mudar; IDs, autoria, tarefa, inscrição,
        # data inicial e TODOS os outros registros devem permanecer intactos.
        expected = deepcopy(before)
        if operation == "first_complete":
            assert not any(r["professor_id"] == d[actor] and r["task_id"] == d["task"]
                           for r in before["professor_checklists"])
            assert record["id"] not in {r["id"] for r in before["professor_checklists"]}
            expected["professor_checklists"].append({
                "id": record["id"], "professor_id": d[actor], "task_id": d["task"],
                "concluido": True, "data_conclusao": record["data_conclusao"],
            })
            expected["professor_checklists"].sort(key=lambda row: row["id"])
        else:
            expected_record = next(r for r in expected["professor_checklists"]
                                   if r["professor_id"] == d[actor] and r["task_id"] == d["task"])
            expected_record.update(concluido=completed, data_conclusao=record["data_conclusao"])
        expected_enrollment = next(r for r in expected["professor_trilhas"]
                                   if r["professor_id"] == d[actor] and r["trilha_id"] == d["track"])
        expected_enrollment.update(status=StatusEnum.CONCLUIDO if completed else StatusEnum.EM_ANDAMENTO,
                                   data_conclusao=enrollment["data_conclusao"])
        assert after == expected
    elif operation == "start":
        new = [r for r in after["professor_trilhas"] if r not in before["professor_trilhas"]]
        assert len(new) == 1
        assert new[0]["professor_id"] == d[actor]
        assert new[0]["trilha_id"] == d["available"]
        assert new[0]["status"] == StatusEnum.EM_ANDAMENTO
        assert new[0]["data_inicio"] is not None
        assert new[0]["data_conclusao"] is None
        assert [r for r in after["professor_trilhas"] if r["id"] != new[0]["id"]] == before["professor_trilhas"]
        assert body["trilha_id"] == d["available"]
        assert body["status"] == "em_andamento"
        assert after["professor_checklists"] == before["professor_checklists"]
        assert after["feedbacks"] == before["feedbacks"]
    else:
        new = [r for r in after["feedbacks"] if r not in before["feedbacks"]]
        assert len(new) == 1
        assert new[0]["id"] == body["id"]
        assert new[0]["professor_id"] == d[actor]
        assert new[0]["trilha_id"] == d["track"]
        assert new[0]["comentario"] == payload["comentario"]
        assert new[0]["data_envio"] is not None
        assert [r for r in after["feedbacks"] if r["id"] != new[0]["id"]] == before["feedbacks"]
        assert after["professor_trilhas"] == before["professor_trilhas"]
        assert after["professor_checklists"] == before["professor_checklists"]


@pytest.mark.parametrize("method,path,actor", [
    (method, path, actor)
    for routes, actor in ((ADMIN_ROUTES, "admin"), (PROFESSOR_ROUTES, "a"))
    for method, path in routes if method != "GET"
])
@pytest.mark.parametrize("token", [None, "token-invalido"], ids=["missing", "invalid"])
def test_csrf_rejects_mutations_before_database_changes(client, permission_data, method, path, actor, token):
    authenticate(client, permission_data[actor])
    get_csrf_token(client)
    before = snapshot()
    headers = {} if token is None else {"X-CSRFToken": token}
    response = client.open(path.format(**permission_data), method=method, headers=headers)
    assert response.status_code == 400
    assert "CSRF token is" in response.get_data(as_text=True)
    assert snapshot() == before
    with client.session_transaction() as session:
        assert session["_user_id"] == str(permission_data[actor])


def test_csrf_admin_forms_and_javascript_mutations(app, client, permission_data):
    import json
    import re

    authenticate(client, permission_data["admin"])

    def send(path, **kwargs):
        with app.app_context():
            return client.open(path, **kwargs)

    def javascript_headers(page):
        # Usa o token realmente renderizado no cabeçalho dos fetch existentes.
        response = send(page)
        assert response.status_code == 200
        token = re.search(r"'X-CSRFToken': (\"[^\"]+\")", response.get_data(as_text=True))
        assert token is not None
        return {"X-CSRFToken": json.loads(token.group(1))}

    response = send("/admin/professores", method="POST", headers={"Accept": "text/html"}, data={
        "csrf_token": csrf_token_from_response(send("/admin/professores")),
        "nome": "Novo professor", "email": "novo@csrf.test", "senha": "Senha-segura-123",
    })
    assert response.status_code == 302
    user = User.query.filter_by(email="novo@csrf.test").one()
    user_id = user.id
    response = send(f"/admin/professores/{user_id}", method="PATCH",
                    headers=javascript_headers("/admin/professores"), json={"nome": "Nome atualizado"})
    assert response.status_code == 200
    db.session.expire_all()
    assert db.session.get(User, user_id).nome == "Nome atualizado"

    response = send("/trilhas/", method="POST", content_type="multipart/form-data", data={
        "csrf_token": csrf_token_from_response(send("/admin/trilhas")),
        "nome": "Trilha CSRF", "tipo": TipoEnum.PEDAGOGICA.value,
    })
    assert response.status_code == 201
    track_id = response.get_json()["id"]
    headers = javascript_headers("/admin/trilhas")
    for method in ("PUT", "PATCH"):
        response = send(f"/trilhas/{track_id}", method=method, headers=headers,
                        json={"nome": f"Trilha {method}"})
        assert response.status_code == 200
        db.session.expire_all()
        assert db.session.get(Checklist, track_id).nome == f"Trilha {method}"

    response = send(f"/trilhas/{track_id}/tasks", method="POST",
                    headers=javascript_headers("/admin/tarefas-feedbacks"), json={"descricao": "Tarefa CSRF"})
    assert response.status_code == 201
    task_id = response.get_json()["id"]
    assert db.session.get(Task, task_id).checklist_id == track_id
    response = send(f"/trilhas/{track_id}", method="DELETE", headers=headers)
    assert response.status_code == 200
    db.session.expire_all()
    assert db.session.get(Checklist, track_id) is None
    assert db.session.get(Task, task_id) is None


def test_csrf_professor_rendered_forms_keep_working(app, client, permission_data):
    authenticate(client, permission_data["a"])

    def send(path, **kwargs):
        with app.app_context():
            return client.open(path, **kwargs)

    task_id = permission_data["task"]
    for operation, completed in (("complete", True), ("incomplete", False)):
        token = csrf_token_from_response(send(f"/professor/tarefas/{task_id}"))
        response = send(f"/tasks/{task_id}/{operation}", method="POST", data={"csrf_token": token})
        assert response.status_code == 302
        db.session.expire_all()
        record = ProfessorChecklist.query.filter_by(professor_id=permission_data["a"], task_id=task_id).one()
        assert record.concluido is completed

    response = send("/professor/feedback", method="POST", headers={"Accept": "text/html"}, data={
        "csrf_token": csrf_token_from_response(send("/professor/feedback")),
        "comentario": "Feedback com CSRF", "trilha_id": permission_data["track"],
    })
    assert response.status_code == 302
    assert Feedback.query.filter_by(comentario="Feedback com CSRF").one().professor_id == permission_data["a"]
