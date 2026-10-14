import pytest
from tests.helpers import testHelper
from app.models.user import RoleEnum




def test_acess_admin_routes(client):
    # Autenticar como usuário com role ADMIN
    testHelper.authenticate_user(client, RoleEnum.ADMIN)

    routes = [
        '/admin/',
        '/admin/professores',
        '/admin/trilhas',
        '/admin/tarefas-feedbacks',
    ]

    # Acessar a rota /admin
    for route in routes:
        response = client.get(route)
        assert response.status_code == 200
