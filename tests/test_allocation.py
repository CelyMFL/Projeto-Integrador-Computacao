import pytest

from app import db
from app.models import (
    ProfessorChecklist, ProfessorTrilha, RoleEnum, StatusEnum, User,
)
from app.services.professor_checklist_service import ProfessorChecklistService
from app.services.professor_trilha_service import ProfessorTrilhaService
from app.services.task_service import TaskService
from app.services.trilha_service import TrilhaService
from tests.helpers import testHelper, get_csrf_token


@pytest.fixture
def dados(app):
    professor = User(nome="Maria Souza", email="maria@teste.com", senha="x", role=RoleEnum.PROFESSOR)
    outro = User(nome="João Lima", email="joao@teste.com", senha="x", role=RoleEnum.PROFESSOR)
    db.session.add_all([professor, outro])
    db.session.commit()

    trilha_a = TrilhaService.create_trilha("Trilha A")
    trilha_b = TrilhaService.create_trilha("Trilha B")
    tarefas_a = [TaskService.create_task(trilha_a.id, f"Tarefa A{i}", ordem=i) for i in (1, 2)]
    return {
        "prof": professor.id, "outro": outro.id,
        "a": trilha_a.id, "b": trilha_b.id,
        "tarefas_a": [t.id for t in tarefas_a],
    }


def enrollment(prof, trilha):
    db.session.expire_all()
    return ProfessorTrilha.query.filter_by(professor_id=prof, trilha_id=trilha).first()


# ---------------------------------------------------------------- services

def test_atribuir_cria_nao_iniciado_sem_data_inicio(dados):
    resumo = ProfessorTrilhaService.sync_professor_trilhas(dados["prof"], {dados["a"]: "nao_iniciado"})
    item = enrollment(dados["prof"], dados["a"])
    assert resumo == {"added": 1, "updated": 0, "removed": 0}
    assert item.status == StatusEnum.NAO_INICIADO
    assert item.data_inicio is None


def test_atribuir_em_andamento_define_data_inicio(dados):
    ProfessorTrilhaService.sync_professor_trilhas(dados["prof"], {dados["a"]: "em_andamento"})
    item = enrollment(dados["prof"], dados["a"])
    assert item.status == StatusEnum.EM_ANDAMENTO
    assert item.data_inicio is not None


def test_nao_permite_atribuir_como_concluido(dados):
    with pytest.raises(ValueError):
        ProfessorTrilhaService.sync_professor_trilhas(dados["prof"], {dados["a"]: "concluido"})
    assert enrollment(dados["prof"], dados["a"]) is None


def test_status_invalido_e_ids_inexistentes(dados):
    with pytest.raises(ValueError):
        ProfessorTrilhaService.sync_professor_trilhas(dados["prof"], {dados["a"]: "qualquer"})
    with pytest.raises(ValueError):
        ProfessorTrilhaService.sync_professor_trilhas(dados["prof"], {999: "nao_iniciado"})
    with pytest.raises(ValueError):
        ProfessorTrilhaService.sync_professor_trilhas(999, {dados["a"]: "nao_iniciado"})


def test_remover_atribuicao_apaga_conclusoes_da_trilha(dados):
    ProfessorTrilhaService.sync_professor_trilhas(
        dados["prof"], {dados["a"]: "nao_iniciado", dados["b"]: "nao_iniciado"}
    )
    ProfessorChecklistService.mark_task_complete(dados["prof"], dados["tarefas_a"][0])
    assert ProfessorTrilhaService.count_completed_tasks(dados["prof"], dados["a"]) == 1

    resumo = ProfessorTrilhaService.sync_professor_trilhas(dados["prof"], {dados["b"]: "nao_iniciado"})

    assert resumo["removed"] == 1
    assert enrollment(dados["prof"], dados["a"]) is None
    assert enrollment(dados["prof"], dados["b"]) is not None
    assert ProfessorChecklist.query.filter_by(professor_id=dados["prof"]).count() == 0


def test_primeira_tarefa_concluida_promove_para_em_andamento(dados):
    ProfessorTrilhaService.sync_professor_trilhas(dados["prof"], {dados["a"]: "nao_iniciado"})
    ProfessorChecklistService.mark_task_complete(dados["prof"], dados["tarefas_a"][0])
    item = enrollment(dados["prof"], dados["a"])
    assert item.status == StatusEnum.EM_ANDAMENTO
    assert item.data_inicio is not None


def test_concluir_todas_as_tarefas_conclui_a_trilha(dados):
    ProfessorTrilhaService.sync_professor_trilhas(dados["prof"], {dados["a"]: "nao_iniciado"})
    for task_id in dados["tarefas_a"]:
        ProfessorChecklistService.mark_task_complete(dados["prof"], task_id)
    assert enrollment(dados["prof"], dados["a"]).status == StatusEnum.CONCLUIDO


def test_professor_inicia_trilha_atribuida_pelo_admin(dados):
    ProfessorTrilhaService.sync_professor_trilhas(dados["prof"], {dados["a"]: "nao_iniciado"})
    item = ProfessorTrilhaService.start_trilha(dados["prof"], dados["a"])
    assert item.status == StatusEnum.EM_ANDAMENTO
    assert item.data_inicio is not None
    assert ProfessorTrilha.query.filter_by(professor_id=dados["prof"], trilha_id=dados["a"]).count() == 1

    with pytest.raises(ValueError):
        ProfessorTrilhaService.start_trilha(dados["prof"], dados["a"])


def test_reabrir_trilha_concluida_limpa_data_conclusao(dados):
    ProfessorTrilhaService.sync_professor_trilhas(dados["prof"], {dados["a"]: "nao_iniciado"})
    for task_id in dados["tarefas_a"]:
        ProfessorChecklistService.mark_task_complete(dados["prof"], task_id)

    ProfessorTrilhaService.sync_professor_trilhas(dados["prof"], {dados["a"]: "em_andamento"})

    item = enrollment(dados["prof"], dados["a"])
    assert item.status == StatusEnum.EM_ANDAMENTO
    assert item.data_conclusao is None


def test_concluido_mantido_nao_conta_como_alteracao(dados):
    ProfessorTrilhaService.sync_professor_trilhas(dados["prof"], {dados["a"]: "nao_iniciado"})
    for task_id in dados["tarefas_a"]:
        ProfessorChecklistService.mark_task_complete(dados["prof"], task_id)

    resumo = ProfessorTrilhaService.sync_professor_trilhas(dados["prof"], {dados["a"]: "concluido"})

    assert resumo == {"added": 0, "updated": 0, "removed": 0}
    assert enrollment(dados["prof"], dados["a"]).status == StatusEnum.CONCLUIDO


def test_nao_iniciado_com_progresso_e_recusado_e_nada_e_alterado(dados):
    ProfessorTrilhaService.sync_professor_trilhas(
        dados["prof"], {dados["a"]: "nao_iniciado", dados["b"]: "nao_iniciado"}
    )
    ProfessorChecklistService.mark_task_complete(dados["prof"], dados["tarefas_a"][0])

    # A remoção da trilha B vem na mesma requisição e deve ser desfeita junto com o erro.
    with pytest.raises(ValueError):
        ProfessorTrilhaService.sync_professor_trilhas(dados["prof"], {dados["a"]: "nao_iniciado"})

    assert enrollment(dados["prof"], dados["a"]).status == StatusEnum.EM_ANDAMENTO
    assert enrollment(dados["prof"], dados["b"]) is not None


def test_sincronizar_pela_trilha(dados):
    resumo = ProfessorTrilhaService.sync_trilha_professores(
        dados["a"], {dados["prof"]: "nao_iniciado", dados["outro"]: "em_andamento"}
    )
    assert resumo["added"] == 2
    resumo = ProfessorTrilhaService.sync_trilha_professores(dados["a"], {dados["outro"]: "em_andamento"})
    assert resumo == {"added": 0, "updated": 0, "removed": 1}
    assert enrollment(dados["prof"], dados["a"]) is None


def test_sincronizar_pela_trilha_recusa_usuario_nao_professor(app, dados):
    admin = User(nome="Admin", email="adm@teste.com", senha="x", role=RoleEnum.ADMIN)
    db.session.add(admin)
    db.session.commit()
    with pytest.raises(ValueError):
        ProfessorTrilhaService.sync_trilha_professores(dados["a"], {admin.id: "nao_iniciado"})


# ------------------------------------------------------------------ routes

def put_json(client, url, payload):
    return client.put(url, json=payload, headers={"X-CSRFToken": get_csrf_token(client), "Accept": "application/json"})


def test_put_atribuicoes_do_professor(client, dados):
    testHelper.authenticate_user(client, RoleEnum.ADMIN)
    response = put_json(client, f"/admin/professores/{dados['prof']}/trilhas", {
        "atribuicoes": [
            {"trilha_id": dados["a"], "status": "nao_iniciado"},
            {"trilha_id": dados["b"], "status": "em_andamento"},
        ],
    })
    assert response.status_code == 200
    assert response.get_json()["added"] == 2
    assert enrollment(dados["prof"], dados["b"]).status == StatusEnum.EM_ANDAMENTO


def test_put_atribuicoes_da_trilha(client, dados):
    testHelper.authenticate_user(client, RoleEnum.ADMIN)
    response = put_json(client, f"/admin/trilhas/{dados['a']}/professores", {
        "atribuicoes": [{"professor_id": dados["prof"]}, {"professor_id": dados["outro"], "status": "em_andamento"}],
    })
    assert response.status_code == 200
    assert enrollment(dados["prof"], dados["a"]).status == StatusEnum.NAO_INICIADO
    assert enrollment(dados["outro"], dados["a"]).status == StatusEnum.EM_ANDAMENTO


@pytest.mark.parametrize("payload", [
    {},
    {"atribuicoes": "x"},
    {"atribuicoes": [{"status": "em_andamento"}]},
    {"atribuicoes": [{"trilha_id": "abc"}]},
    {"atribuicoes": [{"trilha_id": 999}]},
    {"atribuicoes": [{"trilha_id": 1, "status": "concluido"}]},
])
def test_put_atribuicoes_invalidas_retornam_400(client, dados, payload):
    testHelper.authenticate_user(client, RoleEnum.ADMIN)
    response = put_json(client, f"/admin/professores/{dados['prof']}/trilhas", payload)
    assert response.status_code == 400
    assert "error" in response.get_json()
    assert ProfessorTrilha.query.count() == 0


def test_put_para_alvo_inexistente_ou_nao_professor_retorna_404(client, dados):
    admin = testHelper.authenticate_user(client, RoleEnum.ADMIN)
    assert put_json(client, "/admin/professores/999/trilhas", {"atribuicoes": []}).status_code == 404
    assert put_json(client, f"/admin/professores/{admin.id}/trilhas", {"atribuicoes": []}).status_code == 404
    assert put_json(client, "/admin/trilhas/999/professores", {"atribuicoes": []}).status_code == 404


def test_professor_nao_pode_atribuir_trilhas(client, dados):
    testHelper.authenticate_user(client, RoleEnum.PROFESSOR)
    response = put_json(client, f"/admin/professores/{dados['prof']}/trilhas", {"atribuicoes": [{"trilha_id": dados["a"]}]})
    assert response.status_code == 403
    assert ProfessorTrilha.query.count() == 0


def test_paginas_de_atribuicao_e_ficha(client, dados):
    ProfessorTrilhaService.sync_professor_trilhas(dados["prof"], {dados["a"]: "em_andamento"})
    testHelper.authenticate_user(client, RoleEnum.ADMIN)

    html = client.get(f"/admin/professores/{dados['prof']}/trilhas").get_data(as_text=True)
    assert 'data-key="trilha_id"' in html and f'id="assign-check-{dados["a"]}"' in html
    assert 'data-initial-status="em_andamento"' in html

    html = client.get(f"/admin/trilhas/{dados['a']}/professores").get_data(as_text=True)
    assert 'data-key="professor_id"' in html and "Maria Souza" in html and "João Lima" in html

    html = client.get(f"/admin/professores/{dados['prof']}").get_data(as_text=True)
    assert "Trilha A" in html and "Em andamento" in html and "Trilha B" not in html


@pytest.mark.parametrize("url", [
    "/admin/professores/999", "/admin/professores/999/trilhas",
    "/admin/trilhas/999/professores", "/admin/trilhas/999/conteudo", "/admin/trilhas/999/tarefas/nova",
])
def test_paginas_novas_retornam_404_para_id_inexistente(client, dados, url):
    testHelper.authenticate_user(client, RoleEnum.ADMIN)
    assert client.get(url).status_code == 404


def test_pagina_de_conteudo_lista_tarefas_em_ordem(client, dados):
    testHelper.authenticate_user(client, RoleEnum.ADMIN)
    html = client.get(f"/admin/trilhas/{dados['a']}/conteudo").get_data(as_text=True)
    assert html.index("Tarefa A1") < html.index("Tarefa A2")
    assert f'data-reorder-url="/tasks/trilhas/{dados["a"]}/reorder"' in html
    assert f"/admin/trilhas/{dados['a']}/tarefas/nova" in html

    pagina = client.get(f"/admin/trilhas/{dados['a']}/tarefas/nova").get_data(as_text=True)
    assert f'data-endpoint="/trilhas/{dados["a"]}/tasks"' in pagina and 'data-method="POST"' in pagina


def test_criar_tarefa_pelo_endpoint_usado_pela_tela_nova(client, dados):
    testHelper.authenticate_user(client, RoleEnum.ADMIN)
    response = client.post(
        f"/trilhas/{dados['a']}/tasks",
        json={"descricao": "Nova", "material_apoio": "", "link_apoio": "", "documento_apoio": ""},
        headers={"X-CSRFToken": get_csrf_token(client)},
    )
    assert response.status_code == 201
    assert response.get_json()["ordem"] == 3


def test_listas_mostram_links_e_filtro_de_status_das_trilhas(client, dados):
    ProfessorTrilhaService.sync_professor_trilhas(dados["prof"], {dados["a"]: "em_andamento"})
    testHelper.authenticate_user(client, RoleEnum.ADMIN)

    html = client.get("/admin/professores").get_data(as_text=True)
    assert f'/admin/professores/{dados["prof"]}/trilhas' in html
    assert "prof-status-filter" not in html and "Não iniciado" not in html
    assert 'data-professor-name="maria souza"' in html and 'data-professor-email="maria@teste.com"' in html
    assert "/admin/professores/novo" in html and "create-professor-form" not in html

    html = client.get("/admin/trilhas?status=em_andamento").get_data(as_text=True)
    assert 'data-count-em_andamento="1"' in html
    assert '<option value="em_andamento" selected>' in html
    assert f'/admin/trilhas/{dados["a"]}/conteudo' in html and f'/admin/trilhas/{dados["a"]}/professores' in html

    html = client.get("/admin/tarefas-feedbacks").get_data(as_text=True)
    assert "add-task-form" not in html and f'/admin/trilhas/{dados["a"]}/conteudo' in html


def test_status_invalido_na_lista_de_trilhas_e_ignorado(client, dados):
    testHelper.authenticate_user(client, RoleEnum.ADMIN)
    html = client.get("/admin/trilhas?status=<script>").get_data(as_text=True)
    assert "<script>" not in html.split("<main", 1)[1].split("</main>", 1)[0]


def test_pagina_de_cadastro_de_professor(client, dados):
    testHelper.authenticate_user(client, RoleEnum.ADMIN)
    html = client.get("/admin/professores/novo").get_data(as_text=True)
    assert 'data-method="POST"' in html and 'data-endpoint="/admin/professores"' in html
    for campo in ('name="nome"', 'name="email"', 'name="senha"'):
        assert campo in html


def test_cadastro_de_professor_pelo_endpoint_usado_pela_tela(client, dados):
    testHelper.authenticate_user(client, RoleEnum.ADMIN)
    response = client.post(
        "/admin/professores",
        json={"nome": "Carla Dias", "email": "Carla@Teste.com", "senha": "segredo"},
        headers={"X-CSRFToken": get_csrf_token(client), "Accept": "application/json"},
    )
    assert response.status_code == 201
    novo = User.query.filter_by(email="carla@teste.com").one()
    assert novo.role == RoleEnum.PROFESSOR and novo.senha != "segredo"


def test_pagina_de_cadastro_exige_admin(client, dados):
    testHelper.authenticate_user(client, RoleEnum.PROFESSOR)
    assert client.get("/admin/professores/novo").status_code == 403


def test_excluir_tarefa_com_conclusoes_de_professores(client, dados):
    ProfessorTrilhaService.sync_professor_trilhas(dados["prof"], {dados["a"]: "nao_iniciado"})
    tarefa = dados["tarefas_a"][0]
    ProfessorChecklistService.mark_task_complete(dados["prof"], tarefa)
    testHelper.authenticate_user(client, RoleEnum.ADMIN)

    response = client.delete(f"/tasks/{tarefa}", headers={"X-CSRFToken": get_csrf_token(client)})

    assert response.status_code == 200
    assert ProfessorChecklist.query.filter_by(task_id=tarefa).count() == 0
    assert [t.ordem for t in TaskService.list_tasks_by_trilha(dados["a"])] == [1]
