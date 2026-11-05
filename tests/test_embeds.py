from app import db
from app.models import ProfessorChecklist, RoleEnum
from app.services.task_service import TaskService
from app.services.trilha_service import TrilhaService
from app.utils import youtube_embed, pdf_src
from tests.helpers import csrf_token_from_response, testHelper


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

    # Contrato estatico; nao executa JavaScript nem substitui teste em navegador.
    assert 'id="task-status-form"' in html
    assert 'name="csrf_token"' in html
    script = client.get('/static/js/video-progress.js')
    assert script.status_code == 200
    source = script.get_data(as_text=True)
    assert "document.getElementById('task-status-form')" in source
    assert "form.querySelector('input[name=\"csrf_token\"]')" in source
    assert "'X-CSRFToken': csrfToken ? csrfToken.value : ''" in source


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
    professor = testHelper.authenticate_user(client, RoleEnum.PROFESSOR)
    professor_id, tarefa_id = professor.id, tarefa.id
    token = csrf_token_from_response(client.get(f'/professor/tarefas/{tarefa_id}'))

    resposta = client.post(
        f"/tasks/{tarefa_id}/complete",
        json={},
        headers={"Accept": "application/json", "X-CSRFToken": token},
    )
    assert resposta.status_code == 200
    assert resposta.get_json()["concluido"] is True
    assert resposta.get_json()["task_id"] == tarefa_id
    db.session.remove()
    registro = ProfessorChecklist.query.filter_by(
        professor_id=professor_id, task_id=tarefa_id,
    ).one()
    assert registro.concluido is True
    assert registro.data_conclusao is not None


def test_endpoint_do_video_sem_csrf_nao_modifica_dados(client):
    trilha = TrilhaService.create_trilha("Trilha", "Descricao")
    tarefa = TaskService.create_task(trilha.id, "Tarefa", ordem=1)
    tarefa_id = tarefa.id
    testHelper.authenticate_user(client, RoleEnum.PROFESSOR)
    # Ter cookie e token na pagina nao substitui envia-lo na requisicao.
    csrf_token_from_response(client.get(f'/professor/tarefas/{tarefa_id}'))

    def estado_do_banco():
        db.session.remove()
        return {
            table.name: [dict(row) for row in db.session.execute(
                db.select(table).order_by(*table.primary_key.columns)
            ).mappings()]
            for table in db.metadata.sorted_tables
        }

    antes = estado_do_banco()
    resposta = client.post(
        f'/tasks/{tarefa_id}/complete', json={},
        headers={"Accept": "application/json"},
    )
    assert resposta.status_code == 400
    assert "The CSRF token is missing." in resposta.get_data(as_text=True)
    assert estado_do_banco() == antes
