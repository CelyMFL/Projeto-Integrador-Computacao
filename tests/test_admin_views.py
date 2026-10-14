import pytest

from app import db
from app.models.user import User, RoleEnum


def autenticar_usuario(client, role):
    usuario = User(
        nome="Usuário de Teste",
        email=f"{role.value}@teste.com",
        senha="senhatemporaria",
        role=role
    )

    db.session.add(usuario)
    db.session.commit()

    with client.session_transaction() as session:
        session['_user_id'] = str(usuario.id)
        session['_fresh'] = True  # Marca a sessão como "fresh" para simular um login bem-sucedido


def test_acess_admin_routes(client):
    # Autenticar como usuário com role ADMIN
    autenticar_usuario(client, RoleEnum.ADMIN)

    routes = [
        '/admin/',
        #'/admin/analytics',
        '/admin/professores',
        '/admin/trilhas',
        '/admin/tarefas-feedbacks',
    ]

    # Acessar a rota /admin
    for route in routes:
        response = client.get(route)
        assert response.status_code == 200
