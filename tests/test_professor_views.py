from app.models import RoleEnum
from app.services.task_service import TaskService
from app.services.trilha_service import TrilhaService
from tests.helpers import testHelper


def test_acess_professor_routes(client):
    trilha = TrilhaService.create_trilha("Trilha de teste", "Descrição da trilha")
    tarefa = TaskService.create_task(trilha.id, "Tarefa de teste", ordem=1)

    # Autenticar como usuário com role PROFESSOR
    helper = testHelper()
    helper.authenticate_user(client, RoleEnum.PROFESSOR)

    routes = [
        '/professor/dashboard',
        f'/professor/trilhas/{trilha.id}',
        f'/professor/tarefas/{tarefa.id}',
        '/professor/feedback',
    ]

    # Acessar as rotas do professor
    for route in routes:
        response = client.get(route)
        assert response.status_code == 200, f"{route} retornou {response.status_code}"