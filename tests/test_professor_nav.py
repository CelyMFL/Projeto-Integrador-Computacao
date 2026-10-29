import pytest

from app import db
from app.models import ProfessorTrilha, RoleEnum, StatusEnum
from app.services.task_service import TaskService
from app.services.trilha_service import TrilhaService
from tests.helpers import testHelper


@pytest.fixture
def dados(app):
    atribuida = TrilhaService.create_trilha("Trilha Atribuída")
    outra = TrilhaService.create_trilha("Trilha Sem Atribuição")
    tarefa = TaskService.create_task(atribuida.id, "Ler o guia", ordem=1)
    return {"atribuida": atribuida.id, "outra": outra.id, "tarefa": tarefa.id}


def atribuir(professor, trilha_id, status=StatusEnum.EM_ANDAMENTO):
    db.session.add(ProfessorTrilha(professor_id=professor.id, trilha_id=trilha_id, status=status))
    db.session.commit()


def test_lista_de_trilhas_mostra_so_as_atribuidas_com_status(client, dados):
    professor = testHelper.authenticate_user(client, RoleEnum.PROFESSOR)
    atribuir(professor, dados["atribuida"])

    resposta = client.get("/professor/trilhas")
    html = resposta.get_data(as_text=True)

    assert resposta.status_code == 200
    assert "Trilha Atribuída" in html and "Em andamento" in html
    assert "Trilha Sem Atribuição" not in html
    assert f'/professor/trilhas/{dados["atribuida"]}' in html


def test_lista_de_trilhas_vazia(client, dados):
    testHelper.authenticate_user(client, RoleEnum.PROFESSOR)
    assert "Nenhuma trilha atribuída" in client.get("/professor/trilhas").get_data(as_text=True)


def test_lista_de_trilhas_em_json(client, dados):
    professor = testHelper.authenticate_user(client, RoleEnum.PROFESSOR)
    atribuir(professor, dados["atribuida"], StatusEnum.NAO_INICIADO)

    resposta = client.get("/professor/trilhas", headers={"Accept": "application/json"})

    assert resposta.status_code == 200
    trilhas = resposta.get_json()["trilhas"]
    assert [t["nome"] for t in trilhas] == ["Trilha Atribuída"]
    assert trilhas[0]["status"] == "nao_iniciado"


def test_admin_nao_acessa_lista_de_trilhas_do_professor(client, dados):
    testHelper.authenticate_user(client, RoleEnum.ADMIN)
    assert client.get("/professor/trilhas").status_code == 403


@pytest.mark.parametrize("caminho,ativo", [
    ("/professor/dashboard", "Dashboard"),
    ("/professor/trilhas", "Trilhas"),
    ("/professor/trilhas/{atribuida}", "Trilhas"),
    ("/professor/tarefas/{tarefa}", "Trilhas"),
    ("/professor/feedback", "Feedback"),
])
def test_menu_do_professor_tem_trilhas_e_sair_em_todas_as_telas(client, dados, caminho, ativo):
    testHelper.authenticate_user(client, RoleEnum.PROFESSOR)

    html = client.get(caminho.format(**dados)).get_data(as_text=True)

    assert 'href="/auth/logout"' in html and ">Sair</a>" in html
    assert 'href="/professor/trilhas"' in html
    assert f'class="active" aria-current="page">{ativo}</a>' in html
    assert 'href="#"' not in html.split("<main", 1)[0]


@pytest.mark.parametrize("caminho", [
    "/admin/", "/admin/professores", "/admin/trilhas", "/admin/tarefas-feedbacks",
    "/admin/professores/novo", "/admin/trilhas/{atribuida}/conteudo",
])
def test_telas_do_admin_tem_sair(client, dados, caminho):
    testHelper.authenticate_user(client, RoleEnum.ADMIN)
    html = client.get(caminho.format(**dados)).get_data(as_text=True)
    assert 'href="/auth/logout"' in html and "Sair" in html
