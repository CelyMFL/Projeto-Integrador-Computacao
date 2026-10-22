from html.parser import HTMLParser

from app import db
from app.models.user import User, RoleEnum


class FormTokenParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tokens = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'input' and attrs.get('name') == 'csrf_token':
            self.tokens.append(attrs.get('value'))


def csrf_token_from_response(response):
    assert response.status_code == 200
    parser = FormTokenParser()
    parser.feed(response.get_data(as_text=True))
    assert parser.tokens and all(parser.tokens), 'Formulário sem token CSRF'
    return parser.tokens[0]


def get_csrf_token(client):
    # GET real: token assinado e cookie pertencem ao mesmo navegador.
    # Contexto separado evita compartilhar g._login_user / g.csrf_token.
    with client.application.app_context():
        return csrf_token_from_response(client.get('/auth/login'))




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