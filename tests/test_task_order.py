import pytest

from app import db
from app.models import RoleEnum, Task, User
from app.services.task_service import TaskService
from app.services.trilha_service import TrilhaService
from tests.helpers import testHelper


def ordens(trilha_id):
    db.session.expire_all()
    return [(t.descricao, t.ordem) for t in Task.query.filter_by(checklist_id=trilha_id).order_by(Task.ordem)]


@pytest.fixture
def trilha(app):
    return TrilhaService.create_trilha("Trilha")


def test_nova_tarefa_sem_ordem_vai_para_o_fim_e_corrige_buracos(trilha):
    db.session.add_all([
        Task(descricao="A", ordem=1, checklist_id=trilha.id),
        Task(descricao="B", ordem=4, checklist_id=trilha.id),
    ])
    db.session.commit()

    TaskService.create_task(trilha.id, "C")

    assert ordens(trilha.id) == [("A", 1), ("B", 2), ("C", 3)]


def test_nova_tarefa_com_posicao_empurra_as_demais(trilha):
    for nome in ("A", "B"):
        TaskService.create_task(trilha.id, nome)

    TaskService.create_task(trilha.id, "Nova", ordem=1)

    assert ordens(trilha.id) == [("Nova", 1), ("A", 2), ("B", 3)]


def test_nova_tarefa_com_posicao_alem_do_fim_vai_para_o_fim(trilha):
    TaskService.create_task(trilha.id, "A")
    TaskService.create_task(trilha.id, "Nova", ordem=99)
    assert ordens(trilha.id) == [("A", 1), ("Nova", 2)]


def test_mover_tarefa_renumera_sem_duplicar(trilha):
    a, b, c = (TaskService.create_task(trilha.id, nome) for nome in ("A", "B", "C"))

    TaskService.update_task(c.id, ordem=1)
    assert ordens(trilha.id) == [("C", 1), ("A", 2), ("B", 3)]

    TaskService.update_task(c.id, ordem=3)
    assert ordens(trilha.id) == [("A", 1), ("B", 2), ("C", 3)]

    TaskService.update_task(a.id, ordem=50)
    assert ordens(trilha.id) == [("B", 1), ("C", 2), ("A", 3)]


@pytest.mark.parametrize("valor", [0, -1, "2", 1.5])
def test_posicao_invalida_e_recusada(trilha, valor):
    tarefa = TaskService.create_task(trilha.id, "A")
    with pytest.raises(ValueError):
        TaskService.update_task(tarefa.id, ordem=valor)


def test_posicoes_nao_misturam_trilhas(trilha):
    outra = TrilhaService.create_trilha("Outra")
    TaskService.create_task(outra.id, "X")
    TaskService.create_task(outra.id, "Y")
    TaskService.create_task(trilha.id, "A")

    TaskService.create_task(trilha.id, "B", ordem=1)

    assert ordens(outra.id) == [("X", 1), ("Y", 2)]


def test_tela_de_edicao_mostra_a_posicao_real_e_o_limite(client, trilha):
    db.session.add_all([
        Task(descricao="A", ordem=1, checklist_id=trilha.id),
        Task(descricao="B", ordem=4, checklist_id=trilha.id),
    ])
    db.session.commit()
    segunda = Task.query.filter_by(descricao="B").one()
    testHelper.authenticate_user(client, RoleEnum.ADMIN)

    html = client.get(f"/admin/tarefas/{segunda.id}/editar").get_data(as_text=True)

    assert 'min="1" max="2" value="2"' in html
    assert "Posição na trilha" in html


def test_tela_de_nova_tarefa_permite_posicao_ate_o_fim(client, trilha):
    TaskService.create_task(trilha.id, "A")
    testHelper.authenticate_user(client, RoleEnum.ADMIN)
    html = client.get(f"/admin/trilhas/{trilha.id}/tarefas/nova").get_data(as_text=True)
    assert 'min="1" max="2"' in html


def test_cabecalho_do_admin_nao_tem_selos_decorativos(client, trilha):
    testHelper.authenticate_user(client, RoleEnum.ADMIN)
    html = client.get("/admin/trilhas").get_data(as_text=True)
    for texto in ("Painel Executivo", "Operação Diária", "Qualidade Pedagógica"):
        assert texto not in html


def test_nome_longo_do_professor_fica_acessivel_no_cabecalho(client, app):
    nome = "Maria Aparecida de Fátima Nascimento Albuquerque Lima"
    professor = User(nome=nome, email="longo@teste.com", senha="x", role=RoleEnum.PROFESSOR)
    db.session.add(professor)
    db.session.commit()
    with client.session_transaction() as sessao:
        sessao["_user_id"] = str(professor.id)
        sessao["_fresh"] = True

    html = client.get("/professor/dashboard").get_data(as_text=True)

    assert f'<strong title="{nome}">{nome}</strong>' in html
