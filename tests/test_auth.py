"""AU02–AU13: login real e ciclo de sessão. AU01 permanece em test_routes.py.

Os testes de segurança exigem rejeição segura, sem xfail nem asserções que
aceitem exceções/CSRF como requisitos. Falhas conhecidas ficam visíveis.
"""

from urllib.parse import parse_qs, urlsplit

import pytest
from werkzeug.security import check_password_hash, generate_password_hash

from app import db
from app.models import RoleEnum, User
from tests.helpers import get_csrf_token


PASSWORDS = {"admin": "Admin-seguro-123", "a": "Professor-A-123", "b": "Professor-B-456"}
JSON_HEADERS = {"Accept": "application/json"}


@pytest.fixture(scope="module")
def password_hashes():
    # Hashes reais com o algoritmo padrão; custo pago uma vez, sem compartilhar banco.
    return {key: generate_password_hash(password) for key, password in PASSWORDS.items()}


@pytest.fixture
def auth_users(app, password_hashes):
    assert app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite://"
    users = {}
    for key in PASSWORDS:
        user = User(nome=f"Usuario {key}", email=f"{key}@auth.test",
                    senha=password_hashes[key],
                    role=RoleEnum.ADMIN if key == "admin" else RoleEnum.PROFESSOR)
        db.session.add(user)
        users[key] = user
    db.session.commit()
    return {key: {"id": user.id, "nome": user.nome, "email": user.email,
                  "role": user.role.value} for key, user in users.items()}


@pytest.fixture
def auth_request(app, client):
    """Reutiliza client/app, mas não compartilha g._login_user entre requisições."""
    def send(path, *, browser=None, with_csrf=True, **kwargs):
        browser = browser if browser is not None else client
        if with_csrf and kwargs.get("method", "GET").upper() in {"POST", "PUT", "PATCH", "DELETE"}:
            headers = dict(kwargs.get("headers", {}))
            headers.setdefault("X-CSRFToken", get_csrf_token(browser))
            kwargs["headers"] = headers
        with app.app_context():
            return browser.open(path, **kwargs)
    return send


def database_state():
    db.session.remove()
    return {
        table.name: [dict(row) for row in db.session.execute(
            db.select(table).order_by(*table.primary_key.columns)
        ).mappings()]
        for table in db.metadata.sorted_tables
    }


def login(send, users, actor, **kwargs):
    return send("/auth/login", method="POST",
                data={"email": users[actor]["email"], "senha": PASSWORDS[actor]}, **kwargs)


def assert_identity(client, user_id):
    with client.session_transaction() as session:
        assert session["_user_id"] == str(user_id)
        assert session["_fresh"] is True
        assert "senha" not in session
        assert not any(password in repr(dict(session)) for password in PASSWORDS.values())


def assert_anonymous(client):
    with client.session_transaction() as session:
        assert "_user_id" not in session
        assert not session.get("_fresh", False)


def assert_login_redirect(response, next_path=None):
    assert response.status_code == 302
    target = urlsplit(response.headers["Location"])
    assert not target.netloc
    assert target.path == "/auth/login"
    if next_path is not None:
        assert parse_qs(target.query)["next"] == [next_path]


def test_au02_login_form_does_not_authenticate(client, auth_users, auth_request):
    before = database_state()
    response = auth_request("/auth/login")
    assert response.status_code == 200
    assert response.mimetype == "text/html"
    html = response.get_data(as_text=True)
    assert '<form method="POST"' in html
    assert 'type="email" id="usuario" name="email"' in html
    assert 'type="password" id="senha" name="senha"' in html
    assert '<label for="usuario">' in html
    assert '<label for="senha">' in html
    assert_anonymous(client)
    assert database_state() == before


@pytest.mark.parametrize("actor,destination", [
    pytest.param("admin", "/admin/", id="AU03-admin"),
    pytest.param("a", "/professor/dashboard", id="AU04-professor"),
])
def test_valid_login_creates_and_maintains_session(client, auth_users, auth_request,
                                                 actor, destination):
    before = database_state()
    stored = next(user for user in before["users"] if user["id"] == auth_users[actor]["id"])
    assert stored["senha"] != PASSWORDS[actor]
    assert check_password_hash(stored["senha"], PASSWORDS[actor])
    response = login(auth_request, auth_users, actor)
    assert response.status_code == 302
    assert response.headers["Location"] == destination
    assert_identity(client, auth_users[actor]["id"])
    # Duas requisições independentes confirmam manutenção via cookie, sem cache de g.
    for _ in range(2):
        response = auth_request(destination, headers=JSON_HEADERS)
        assert response.status_code == 200
        if actor == "admin":
            assert "Painel Administrativo" in response.get_data(as_text=True)
        else:
            assert response.get_json()["user"] == auth_users[actor]
        assert_identity(client, auth_users[actor]["id"])
    assert database_state() == before


@pytest.mark.parametrize("email,password", [
    ("ausente@auth.test", PASSWORDS["a"]),
    ("a@auth.test", "senha-errada"),
    ("a@auth.test", PASSWORDS["b"]),
    ("", PASSWORDS["a"]),
    ("a@auth.test", ""),
    ("", ""),
])
def test_au05_invalid_credentials_do_not_create_session(client, auth_users, auth_request, email, password):
    before = database_state()
    response = auth_request("/auth/login", method="POST", data={"email": email, "senha": password})
    assert response.status_code == 200
    assert 'name="senha"' in response.get_data(as_text=True)
    assert_anonymous(client)
    assert_login_redirect(auth_request("/professor/dashboard"), "/professor/dashboard")
    assert database_state() == before


@pytest.mark.parametrize("payload", [{}, {"email": "a@auth.test"}, {"senha": PASSWORDS["a"]}])
def test_au06_missing_form_fields_are_rejected(client, auth_users, auth_request, payload):
    before = database_state()
    response = auth_request("/auth/login", method="POST", data=payload)
    assert response.status_code == 400
    assert "CSRF" not in response.get_data(as_text=True)
    assert_anonymous(client)
    assert database_state() == before


@pytest.mark.parametrize("request_body", [
    {"json": {"email": "a@auth.test", "senha": PASSWORDS["a"]}},
    {"data": "email=a@auth.test&senha=Professor-A-123", "content_type": "text/plain"},
])
def test_au06_unsupported_login_formats_do_not_authenticate(client, auth_users, auth_request, request_body):
    before = database_state()
    response = auth_request("/auth/login", method="POST", **request_body)
    assert response.status_code == 400  # A rota atual lê exclusivamente request.form.
    assert "CSRF" not in response.get_data(as_text=True)
    assert_anonymous(client)
    assert database_state() == before


@pytest.mark.parametrize("email", ["A@AUTH.TEST", " a@auth.test "])
def test_au07_current_email_matching_is_exact_on_sqlite(client, auth_users, auth_request, email):
    """Caracterização, não política de segurança: normalização ainda não foi definida."""
    before = database_state()
    response = auth_request("/auth/login", method="POST", data={"email": email, "senha": PASSWORDS["a"]})
    assert response.status_code == 200
    assert 'name="email"' in response.get_data(as_text=True)
    assert_anonymous(client)
    assert database_state() == before


@pytest.mark.parametrize("actor,protected", [("admin", "/admin/"), ("a", "/professor/dashboard")])
def test_au08_logout_revokes_access(client, auth_users, auth_request, actor, protected):
    """Valida efeito do logout atual; não aprova GET como proteção contra CSRF."""
    before = database_state()
    assert login(auth_request, auth_users, actor).status_code == 302
    assert auth_request(protected).status_code == 200
    assert_login_redirect(auth_request("/auth/logout"))
    assert_anonymous(client)
    assert_login_redirect(auth_request(protected), protected)
    assert_anonymous(client)
    # Logout novamente não recria sessão autenticada.
    assert_login_redirect(auth_request("/auth/logout"))
    assert_anonymous(client)
    assert database_state() == before


def test_au09_deleted_user_loses_access(client, auth_users, auth_request):
    assert login(auth_request, auth_users, "a").status_code == 302
    assert auth_request("/professor/dashboard", headers=JSON_HEADERS).get_json()["user"] == auth_users["a"]
    user = db.session.get(User, auth_users["a"]["id"])
    db.session.delete(user)
    db.session.commit()
    before = database_state()
    assert_login_redirect(auth_request("/professor/dashboard"), "/professor/dashboard")
    assert database_state() == before
    # O cookie pode ainda guardar o ID; o importante é não restaurar o usuário removido.
    response = login(auth_request, auth_users, "a")
    assert response.status_code == 200
    assert_login_redirect(auth_request("/professor/dashboard"), "/professor/dashboard")
    assert database_state() == before


def test_au10_unknown_numeric_session_id_does_not_grant_access(client, auth_users, auth_request):
    before = database_state()
    with client.session_transaction() as session:
        session["_user_id"] = str(max(user["id"] for user in auth_users.values()) + 1)
        session["_fresh"] = True
    assert_login_redirect(auth_request("/professor/dashboard"), "/professor/dashboard")
    assert database_state() == before


def test_au10_malformed_session_id_is_rejected_without_server_error(client, auth_users, auth_request):
    """Segurança: ID não numérico deve falhar fechado, sem ValueError/HTTP 500.

    Atual: load_user executa int(user_id) sem tratar erro. Não aceitar a exceção
    como resultado esperado nem marcar xfail: manter a regressão visível.
    """
    before = database_state()
    with client.session_transaction() as session:
        session["_user_id"] = "id-invalido"
        session["_fresh"] = True
    try:
        response = auth_request("/professor/dashboard")
        assert_login_redirect(response, "/professor/dashboard")
    finally:
        assert database_state() == before


def test_au10_cookie_signed_with_another_key_is_rejected(app, client, auth_users, auth_request):
    from flask.sessions import SecureCookieSessionInterface

    # Cookie estruturalmente válido, porém assinado por outra aplicação/chave.
    from flask import Flask
    foreign_app = Flask("foreign-session")
    foreign_app.secret_key = "not-the-test-secret-key"
    serializer = SecureCookieSessionInterface().get_signing_serializer(foreign_app)
    cookie = serializer.dumps({"_user_id": str(auth_users["admin"]["id"]), "_fresh": True})
    client.set_cookie(app.config["SESSION_COOKIE_NAME"], cookie)
    before = database_state()
    assert_login_redirect(auth_request("/admin/"), "/admin/")
    assert_anonymous(client)
    assert database_state() == before


@pytest.mark.parametrize("actor,destination", [("admin", "/admin/"), ("a", "/professor/dashboard")])
@pytest.mark.parametrize("next_target", ["/professor/feedback", "https://external.example/path", "//external.example/path"])
def test_au11_next_never_overrides_role_destination(client, auth_users, auth_request, actor, destination, next_target):
    """Atual: next é ignorado. Destino fixo é seguro; não exigir redirecionamento externo."""
    before = database_state()
    response = login(auth_request, auth_users, actor, query_string={"next": next_target})
    assert response.status_code == 302
    target = urlsplit(response.headers["Location"])
    assert not target.scheme and not target.netloc
    assert target.path == destination
    assert_identity(client, auth_users[actor]["id"])
    assert database_state() == before


def test_au12_login_page_and_failed_relogin_preserve_existing_identity(client, auth_users, auth_request):
    before = database_state()
    assert login(auth_request, auth_users, "a").status_code == 302
    assert auth_request("/auth/login").status_code == 200
    assert_identity(client, auth_users["a"]["id"])
    response = auth_request("/auth/login", method="POST",
                            data={"email": auth_users["admin"]["email"], "senha": "errada"})
    assert response.status_code == 200
    assert_identity(client, auth_users["a"]["id"])
    assert auth_request("/professor/dashboard", headers=JSON_HEADERS).get_json()["user"] == auth_users["a"]
    assert auth_request("/admin/").status_code == 403
    assert database_state() == before


def test_session_switch_after_real_login_uses_new_identity(client, auth_users, auth_request):
    before = database_state()
    assert login(auth_request, auth_users, "admin").status_code == 302
    assert auth_request("/admin/").status_code == 200
    assert login(auth_request, auth_users, "a").status_code == 302
    assert_identity(client, auth_users["a"]["id"])
    assert auth_request("/admin/").status_code == 403
    assert auth_request("/professor/dashboard", headers=JSON_HEADERS).get_json()["user"] == auth_users["a"]
    assert database_state() == before


def test_sessions_are_independent_between_browsers(app, client, auth_users, auth_request):
    other = app.test_client()
    before = database_state()
    assert login(auth_request, auth_users, "a").status_code == 302
    assert_anonymous(other)
    assert login(auth_request, auth_users, "b", browser=other).status_code == 302
    for browser, actor in ((client, "a"), (other, "b")):
        assert_identity(browser, auth_users[actor]["id"])
        assert auth_request("/professor/dashboard", browser=browser, headers=JSON_HEADERS).get_json()["user"] == auth_users[actor]
    assert_login_redirect(auth_request("/auth/logout"))
    assert_login_redirect(auth_request("/professor/dashboard"), "/professor/dashboard")
    assert_identity(other, auth_users["b"]["id"])
    assert auth_request("/professor/dashboard", browser=other, headers=JSON_HEADERS).get_json()["user"] == auth_users["b"]
    assert database_state() == before


@pytest.mark.parametrize("existing_actor", [
    pytest.param(None, id="anonymous"),
    pytest.param("b", id="preserve-existing-identity"),
])
@pytest.mark.parametrize("token_kind", ["missing", "invalid", "other-session"])
def test_au13_cross_site_login_without_csrf_protection_is_rejected(
        app, client, auth_users, auth_request, existing_actor, token_kind):
    """POST externo sem token válido não deve autenticar nem substituir a identidade.

    A segurança depende da sessão e do acesso protegido, não do status do POST.
    """
    before = database_state()
    if existing_actor is not None:
        assert login(auth_request, auth_users, existing_actor).status_code == 302
        assert_identity(client, auth_users[existing_actor]["id"])
    else:
        assert_anonymous(client)

    headers = {
        "Origin": "https://external.example", "Referer": "https://external.example/form",
    }
    if token_kind != "missing":
        get_csrf_token(client)
        headers["X-CSRFToken"] = (
            "token-invalido" if token_kind == "invalid"
            else get_csrf_token(app.test_client())
        )
    login(auth_request, auth_users, "a", with_csrf=False, headers=headers)
    with client.session_transaction() as session:
        session_user_id = session.get("_user_id")
    protected = auth_request("/professor/dashboard", headers=JSON_HEADERS)

    if existing_actor is None:
        assert (session_user_id, protected.status_code) == (None, 302), (
            "Login cross-site sem token autenticou a sessão ou concedeu acesso protegido"
        )
        assert_anonymous(client)
        assert_login_redirect(protected, "/professor/dashboard")
    else:
        protected_user = (protected.get_json(silent=True) or {}).get("user")
        assert (session_user_id, protected.status_code, protected_user) == (
            str(auth_users[existing_actor]["id"]), 200, auth_users[existing_actor],
        ), "Login cross-site sem token alterou a identidade ou o acesso da sessão existente"
        assert_identity(client, auth_users[existing_actor]["id"])
    assert database_state() == before


def test_login_without_csrf_is_rejected_even_with_same_origin(client, auth_users, auth_request):
    before = database_state()
    response = login(auth_request, auth_users, "a", with_csrf=False, headers={
        "Origin": "http://localhost", "Referer": "http://localhost/auth/login",
    })
    assert response.status_code == 400
    assert "CSRF token is missing" in response.get_data(as_text=True)
    assert_anonymous(client)
    assert_login_redirect(auth_request("/professor/dashboard"), "/professor/dashboard")
    assert database_state() == before


def test_login_accepts_rendered_form_token(client, auth_users, auth_request):
    response = auth_request("/auth/login", method="POST", with_csrf=False, data={
        "email": auth_users["a"]["email"], "senha": PASSWORDS["a"],
        "csrf_token": get_csrf_token(client),
    })
    assert response.status_code == 302
    assert_identity(client, auth_users["a"]["id"])
    assert auth_request("/professor/dashboard", headers=JSON_HEADERS).get_json()["user"] == auth_users["a"]
