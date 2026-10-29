from app import create_app
from app.models import RoleEnum
from app.services.task_service import TaskService
from app.services.trilha_service import TrilhaService
from app.utils import youtube_embed, pdf_src, external_url
from tests.helpers import testHelper


def test_youtube_embed_formatos_validos():
    esperado = "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"
    assert youtube_embed("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == esperado
    assert youtube_embed("https://youtu.be/dQw4w9WgXcQ") == esperado
    assert youtube_embed("https://www.youtube.com/embed/dQw4w9WgXcQ") == esperado


def test_youtube_embed_rejeita_outros_links():
    assert youtube_embed(None) is None
    assert youtube_embed("https://exemplo.com/video") is None
    assert youtube_embed('https://youtu.be/"><script>alert(1)</script>') is None


def test_pdf_src(app):
    with app.test_request_context():
        assert pdf_src("guia.pdf") == "/static/docs/guia.pdf"
        assert pdf_src("../../config.py") is None
        assert pdf_src("../../segredo.pdf") == "/static/docs/segredo.pdf"  # só o nome do arquivo é usado
        assert pdf_src("https://outro-site.com/a.pdf") is None
        assert (
            pdf_src("https://drive.google.com/file/d/ABC_123-x/view?usp=sharing")
            == "https://drive.google.com/file/d/ABC_123-x/preview"
        )
        assert pdf_src(None) is None


def test_pagina_da_tarefa_mostra_embeds(client):
    trilha = TrilhaService.create_trilha("Trilha", "Descricao")
    tarefa = TaskService.create_task(
        trilha.id, "Tarefa com midia", ordem=1,
        link_apoio="https://youtu.be/dQw4w9WgXcQ",
        documento_apoio="guia.pdf",
    )
    testHelper.authenticate_user(client, RoleEnum.PROFESSOR)

    html = client.get(f"/professor/tarefas/{tarefa.id}").get_data(as_text=True)
    assert "youtube-nocookie.com/embed/dQw4w9WgXcQ" in html
    assert "/static/docs/guia.pdf" in html


def test_pagina_da_tarefa_sem_midia_nao_tem_iframe(client):
    trilha = TrilhaService.create_trilha("Trilha", "Descricao")
    tarefa = TaskService.create_task(trilha.id, "Tarefa simples", ordem=1)
    testHelper.authenticate_user(client, RoleEnum.PROFESSOR)

    html = client.get(f"/professor/tarefas/{tarefa.id}").get_data(as_text=True)
    assert "<iframe" not in html


def test_pagina_do_video_prepara_a_iframe_api(client):
    trilha = TrilhaService.create_trilha("Trilha", "Descricao")
    tarefa = TaskService.create_task(
        trilha.id, "Tarefa com video", ordem=1,
        link_apoio="https://youtu.be/dQw4w9WgXcQ",
    )
    testHelper.authenticate_user(client, RoleEnum.PROFESSOR)

    html = client.get(f"/professor/tarefas/{tarefa.id}").get_data(as_text=True)
    assert "enablejsapi=1" in html                      # liga a API no player
    assert f'data-complete-url="/tasks/{tarefa.id}/complete"' in html
    assert "js/video-progress.js" in html


def test_pagina_sem_video_nao_carrega_o_script_da_api(client):
    trilha = TrilhaService.create_trilha("Trilha", "Descricao")
    tarefa = TaskService.create_task(trilha.id, "Tarefa simples", ordem=1)
    testHelper.authenticate_user(client, RoleEnum.PROFESSOR)

    html = client.get(f"/professor/tarefas/{tarefa.id}").get_data(as_text=True)
    assert "video-progress.js" not in html


def test_endpoint_que_o_js_chama_responde_json(client):
    """O JavaScript faz POST com Accept: application/json e espera 'concluido': true."""
    trilha = TrilhaService.create_trilha("Trilha", "Descricao")
    tarefa = TaskService.create_task(trilha.id, "Tarefa", ordem=1)
    testHelper.authenticate_user(client, RoleEnum.PROFESSOR)

    resposta = client.post(
        f"/tasks/{tarefa.id}/complete",
        json={},
        headers={"Accept": "application/json"},
    )
    assert resposta.status_code == 200
    assert resposta.get_json()["concluido"] is True


def test_external_url_aceita_so_http_e_https():
    assert external_url(" https://www.python.org/ ") == "https://www.python.org/"
    assert external_url("http://exemplo.com/a.pdf") == "http://exemplo.com/a.pdf"
    assert external_url("javascript:alert(1)") is None
    assert external_url("data:text/html,<b>x</b>") is None
    assert external_url("guia.pdf") is None
    assert external_url("https://") is None
    assert external_url(None) is None


def test_pagina_da_tarefa_abre_documento_externo_em_nova_aba(client):
    testHelper.authenticate_user(client, RoleEnum.PROFESSOR)
    trilha = TrilhaService.create_trilha("Trilha", "Descricao")
    tarefa = TaskService.create_task(
        trilha.id, "Tarefa", ordem=1,
        link_apoio="javascript:alert(1)", documento_apoio="https://www.python.org/",
    )

    html = client.get(f"/professor/tarefas/{tarefa.id}").get_data(as_text=True)

    assert 'href="https://www.python.org/" target="_blank" rel="noopener noreferrer"' in html
    assert 'href="javascript:alert(1)"' not in html
    assert 'href="#"' not in html
