import pytest

from app.models import RoleEnum
from app.services.task_service import TaskService
from app.services.trilha_service import TrilhaService
from app.utils import titulo_ptbr
from tests.helpers import testHelper, get_csrf_token


@pytest.mark.parametrize("entrada,esperado", [
    ("onboarding de professores", "Onboarding de Professores"),
    ("  comunicação   assertiva ", "Comunicação Assertiva"),
    ("LGPD e privacidade", "LGPD e Privacidade"),
    ("de volta para casa", "De Volta para Casa"),
    ("uso do iPhone", "Uso do iPhone"),
    ("Trilha A", "Trilha A"),
    ("plano B", "Plano B"),
    ("", ""),
    (None, None),
])
def test_titulo_ptbr(entrada, esperado):
    assert titulo_ptbr(entrada) == esperado


def test_trilha_criada_com_nome_capitalizado(app):
    trilha = TrilhaService.create_trilha("introdução ao azure")
    assert trilha.nome == "Introdução ao Azure"


def test_trilha_editada_com_nome_capitalizado(app):
    trilha = TrilhaService.create_trilha("Trilha")
    TrilhaService.update_trilha(trilha.id, nome="nova trilha de testes")
    assert TrilhaService.get_trilha(trilha.id).nome == "Nova Trilha de Testes"


def test_api_cria_trilha_com_nome_capitalizado(client):
    testHelper.authenticate_user(client, RoleEnum.ADMIN)
    response = client.post(
        "/trilhas/",
        json={"nome": "gestão de sala de aula"},
        headers={"X-CSRFToken": get_csrf_token(client), "Accept": "application/json"},
    )
    assert response.status_code == 201
    assert response.get_json()["nome"] == "Gestão de Sala de Aula"


@pytest.fixture
def dados(app):
    from app import db
    from app.models import User
    professor = User(nome="Maria Souza", email="maria@teste.com", senha="x", role=RoleEnum.PROFESSOR)
    db.session.add(professor)
    db.session.commit()
    trilha = TrilhaService.create_trilha("Trilha Exemplo")
    tarefa = TaskService.create_task(trilha.id, "Tarefa exemplo", ordem=1)
    return {"professor": professor.id, "trilha": trilha.id, "tarefa": tarefa.id}


def test_paginas_de_edicao_para_admin(client, dados):
    testHelper.authenticate_user(client, RoleEnum.ADMIN)

    pagina = client.get(f"/admin/professores/{dados['professor']}/editar")
    html = pagina.get_data(as_text=True)
    assert pagina.status_code == 200
    assert 'value="Maria Souza"' in html and 'data-endpoint="/admin/professores/' in html

    pagina = client.get(f"/admin/trilhas/{dados['trilha']}/editar")
    html = pagina.get_data(as_text=True)
    assert pagina.status_code == 200
    assert 'value="Trilha Exemplo"' in html and f'data-endpoint="/trilhas/{dados["trilha"]}"' in html

    pagina = client.get(f"/admin/tarefas/{dados['tarefa']}/editar")
    html = pagina.get_data(as_text=True)
    assert pagina.status_code == 200
    assert 'value="Tarefa exemplo"' in html and f'data-endpoint="/tasks/{dados["tarefa"]}"' in html


@pytest.mark.parametrize("caminho", [
    "/admin/professores/999/editar",
    "/admin/trilhas/999/editar",
    "/admin/tarefas/999/editar",
])
def test_edicao_de_id_inexistente_retorna_404(client, dados, caminho):
    testHelper.authenticate_user(client, RoleEnum.ADMIN)
    assert client.get(caminho).status_code == 404


def test_edicao_de_professor_nao_aceita_admin_como_alvo(client, dados):
    admin = testHelper.authenticate_user(client, RoleEnum.ADMIN)
    assert client.get(f"/admin/professores/{admin.id}/editar").status_code == 404


def test_listas_apontam_para_as_telas_de_edicao(client, dados):
    testHelper.authenticate_user(client, RoleEnum.ADMIN)
    assert f'/admin/professores/{dados["professor"]}/editar' in client.get("/admin/professores").get_data(as_text=True)
    assert f'/admin/trilhas/{dados["trilha"]}/editar' in client.get("/admin/trilhas").get_data(as_text=True)
    html = client.get("/admin/tarefas-feedbacks").get_data(as_text=True)
    assert f'/admin/tarefas/{dados["tarefa"]}/editar' in html
    assert "Edição em breve" not in html


def test_lista_de_professores_tem_campo_de_busca_parcial(client, dados):
    testHelper.authenticate_user(client, RoleEnum.ADMIN)
    html = client.get("/admin/professores").get_data(as_text=True)
    assert 'data-professor-name="maria souza"' in html
    assert 'id="prof-no-results"' in html
