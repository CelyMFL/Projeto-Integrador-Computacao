def test_pagina_inicial_route(client):
    response = client.get('/')
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]