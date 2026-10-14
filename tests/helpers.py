from app import db
from app.models.user import User, RoleEnum




class testHelper:

    @staticmethod
    def authenticate_user( client, role):
        """Helper function to authenticate a user."""
        user =  User(
            nome="Usuario de Teste",
            email=f"{role.value}@teste.com",
            senha="senhatemporaria",
            role=role
        )

        db.session.add(user)
        db.session.commit()

        with client.session_transaction() as session:
            session['_user_id'] = str(user.id)
            session['_fresh'] = True  # Marca a sessão como "fresh" para simular um login bem-sucedido

        return user