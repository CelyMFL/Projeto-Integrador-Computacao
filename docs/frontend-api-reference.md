# Front-end API Reference

Guia atualizado dos contratos HTTP atuais do projeto.

Base local: http://localhost:5000

## Convenções gerais

- Rotas protegidas exigem sessão autenticada via cookie do Flask-Login.
- Erro de permissão: HTTP 403 com {"error": "Acesso negado"} (quando aplicável).
- Erro de validação/regra de negócio: HTTP 400 com {"error": "..."}.
- Algumas rotas aceitam tanto JSON quanto form-data.
- Em rotas híbridas (HTML + JSON), JSON só é retornado quando o cliente pede explicitamente Accept: application/json sem preferência por HTML.
- O front-end atual usa formulários inline e `fetch()` nas telas administrativas para criar/editar trilhas, tarefas e professores.

## 1) Autenticação

### GET /auth/login

Retorno:
- HTML (tela de login)

### POST /auth/login

Entrada:
- application/x-www-form-urlencoded
- campos: email, senha

Comportamento:
- credenciais válidas + role admin: redirect para /admin/
- credenciais válidas + role professor: redirect para /professor/dashboard
- falha: renderiza novamente a tela de login

### GET /auth/logout

Comportamento:
- encerra sessão
- redirect para /auth/login

## 2) Professor

### GET /professor/dashboard

Permissão:
- apenas professor

Retorno:
- HTML: renderiza dashboard.html
- JSON (quando solicitado): payload de dashboard

Exemplo JSON:

```json
{
  "user": {
    "id": 3,
    "nome": "Professor Teste",
    "email": "prof@test.com",
    "role": "professor"
  },
  "trilhas_atribuidas": [
    {
      "id": 1,
      "nome": "Trilha Pedagógica",
      "tipo": "pedagógica",
      "descricao": "Orientações sobre práticas pedagógicas",
      "obrigatoria": true,
      "status": "em_andamento",
      "progresso": {
        "total_tarefas": 5,
        "tarefas_concluidas": 2,
        "percentual": 40.0
      },
      "tasks": [
        {
          "id": 10,
          "descricao": "Atividade Pedagógica 1",
          "ordem": 1,
          "status": "concluido",
          "material_apoio": null,
          "link_apoio": null,
          "documento_apoio": null
        }
      ]
    }
  ],
  "progresso_geral": {
    "total_tarefas": 9,
    "tarefas_concluidas": 3,
    "percentual": 33.33333333333333
  },
  "proximas_tarefas": [
    {
      "task_id": 11,
      "descricao": "Atividade Pedagógica 2",
      "trilha_id": 1
    }
  ],
  "trilhas_obrigatorias": [
    {
      "id": 1,
      "nome": "Trilha Pedagógica",
      "status": "em_andamento"
    }
  ]
}
```

Observação:
- o percentual exibido no dashboard é calculado dinamicamente a partir das conclusões do professor.

### GET /professor/trilhas

Permissão:
- apenas professor

Retorno:
- HTML (trilhas.html) com as trilhas atribuídas, status e progresso
- JSON {"trilhas": [...]} quando Accept: application/json (mesmo formato de trilha usado no dashboard)

### GET /professor/trilhas/<trilha_id>

Permissão:
- apenas professor

Retorno:
- HTML: renderiza trilha.html
- JSON (quando solicitado): trilha serializada com progresso e tasks

Erros:
- 404 quando trilha não existe

### GET /professor/tarefas/<task_id>

Permissão:
- apenas professor

Retorno:
- HTML: renderiza tarefa.html
- JSON (quando solicitado): dados da tarefa + status (concluido|pendente)

Erros:
- 404 quando tarefa não existe

### GET /professor/feedback

Permissão:
- apenas professor

Retorno:
- HTML: renderiza feedback.html
- JSON (quando solicitado): contexto do formulário

Exemplo JSON:

```json
{
  "message": "Formulário de feedback disponível",
  "campos": ["comentario", "trilha_id (opcional)"],
  "trilhas_disponiveis": [
    {"id": 1, "nome": "Trilha Pedagógica"}
  ]
}
```

### POST /professor/feedback

Permissão:
- apenas professor

Entrada:
- JSON ou form-data
- campos:
  - comentario (obrigatório)
  - trilha_id (opcional)

Retorno:
- se cliente HTML: redirect para /professor/dashboard
- se cliente JSON: HTTP 201 com feedback criado

Exemplo resposta JSON 201:

```json
{
  "id": 7,
  "comentario": "A trilha foi clara e bem estruturada.",
  "trilha_id": 1,
  "data_envio": "2026-05-12T14:10:11.778899"
}
```

## 3) Tasks

### POST /tasks/<task_id>/complete

Permissão:
- apenas professor

Retorno:
- se cliente HTML: redirect para /professor/tarefas/<task_id>
- se cliente JSON: status da conclusão

Exemplo JSON:

```json
{
  "message": "Tarefa concluída com sucesso",
  "task_id": 10,
  "concluido": true
}
```

### POST /tasks/<task_id>/incomplete

Permissão:
- apenas professor

Retorno:
- se cliente HTML: redirect para /professor/tarefas/<task_id>
- se cliente JSON: status atualizado

### GET /tasks/<task_id>/status

Permissão:
- apenas professor

Retorno:
- JSON sempre

Exemplo:

```json
{
  "task_id": 10,
  "concluido": true,
  "data_conclusao": "2026-05-12T13:03:47.123456"
}
```

Se não houver registro de conclusão:

```json
{
  "task_id": 10,
  "concluido": false
}
```

### PUT/PATCH /tasks/<task_id>

Permissão:
- apenas admin

Entrada:
- JSON ou form-data
- campos opcionais: descricao, ordem, material_apoio, link_apoio, documento_apoio
- ordem é a posição na trilha (1..N): a tarefa entra nessa posição, valores acima de N vão para o fim e as demais são renumeradas sem buracos

Retorno:
- JSON da tarefa atualizada

### DELETE /tasks/<task_id>

Permissão:
- apenas admin

Retorno:

```json
{"message": "Tarefa removida com sucesso"}
```

### POST /tasks/trilhas/<trilha_id>/reorder

Permissão:
- apenas admin

Entrada:
- JSON/form-data com task_ids
- task_ids pode ser lista ou string CSV

Exemplo:

```json
{
  "task_ids": [12, 10, 11]
}
```

Retorno:

```json
{"message": "Tarefas reordenadas com sucesso"}
```

## 4) Trilhas

### GET /trilhas/

Permissão:
- usuário autenticado (admin ou professor)

Retorno:
- JSON (lista completa de trilhas com tasks ordenadas)

### GET /trilhas/<trilha_id>

Permissão:
- usuário autenticado (admin ou professor)

Retorno:
- JSON de uma trilha com tasks

### POST /trilhas/

Permissão:
- apenas admin

Entrada:
- JSON ou form-data
- nome (obrigatório; salvo com iniciais maiúsculas, ex.: "introdução ao azure" → "Introdução ao Azure")
- descricao (opcional)
- tipo (opcional): pedagógica | institucional | tecnológica
- obrigatoria (opcional): true/false, 1/0, sim/yes

Retorno:
- HTTP 201 com trilha criada

### PUT/PATCH /trilhas/<trilha_id>

Permissão:
- apenas admin

Entrada:
- campos opcionais: nome, descricao, tipo, obrigatoria

Retorno:
- JSON da trilha atualizada

### DELETE /trilhas/<trilha_id>

Permissão:
- apenas admin

Retorno:

```json
{"message": "Trilha removida com sucesso"}
```

Comportamento adicional:
- a exclusão limpa dependências ligadas à trilha antes do `DELETE`, incluindo `feedbacks`, `professor_trilhas` e `professor_checklists` associados às `tasks` da trilha.

### POST /trilhas/<trilha_id>/start

Permissão:
- apenas professor

Retorno:
- HTTP 201 com status inicial em_andamento

### GET /trilhas/<trilha_id>/progress

Permissão:
- apenas professor

Retorno:
- JSON de progresso

Exemplo:

```json
{
  "status": "em_andamento",
  "total_tasks": 5,
  "completed_tasks": 2,
  "completion_percentage": 40.0,
  "data_inicio": "2026-05-12T12:00:00",
  "data_conclusao": null
}
```

Observação:
- este contrato usa `completion_percentage` e não `percentual`.

### POST /trilhas/<trilha_id>/tasks

Permissão:
- apenas admin

Entrada:
- JSON ou form-data
- descricao (obrigatório)
- ordem (opcional): posição na trilha; vazio coloca no final e as demais são renumeradas
- material_apoio, link_apoio, documento_apoio (opcionais)

Retorno:
- HTTP 201 com tarefa criada

## 5) Admin

### GET /admin/

Permissão:
- apenas admin

Retorno:
- HTML (admin_dashboard.html) com métricas

### GET /admin/analytics

Permissão:
- apenas admin

Retorno:
- JSON sempre

```json
{
  "summary": {
    "total_users": 12,
    "total_professores": 10,
    "total_trilhas": 6,
    "total_obrigatorias": 3,
    "total_feedbacks": 15,
    "trilhas_concluidas": 9,
    "trilhas_em_andamento": 4,
    "conclusao_global_percentual": 64.3,
    "tempo_medio_conclusao_dias": 11.2,
    "feedbacks_ultimos_30_dias": 6,
    "ativacoes_ultimos_30_dias": 8
  },
  "analytics": {
    "status_distribution": {
      "labels": ["Não iniciado", "Em andamento", "Concluído"],
      "values": [2, 4, 9]
    },
    "trilhas_por_tipo": {
      "labels": ["Pedagógica", "Institucional", "Tecnológica"],
      "values": [3, 1, 2]
    },
    "feedback_timeline": {
      "labels": ["2026-05", "2026-06", "2026-07"],
      "values": [2, 1, 3]
    },
    "ativacoes_timeline": {
      "labels": ["2026-05", "2026-06", "2026-07"],
      "values": [4, 2, 3]
    },
    "completion_by_trilha": {
      "labels": ["Trilha Pedagógica", "Trilha Tecnológica"],
      "values": [72.5, 48.0]
    },
    "insights": [
      "Taxa global de conclusão em 64.3%.",
      "Tempo médio de conclusão estimado em 11.2 dias."
    ]
  }
}
```

Observação:
- o campo `ativacoes_timeline` funciona como proxy de acesso/engajamento usando inícios de trilha (`data_inicio`).

### GET /admin/professores

Permissão:
- apenas admin

Retorno:
- HTML (admin_professores.html)

Observação:
- apesar de montar payload interno com dados de progresso, esta rota atualmente renderiza template (não expõe JSON).

### POST /admin/professores

Permissão:
- apenas admin

Entrada:
- JSON ou form-data com nome, email, senha

Retorno:
- cliente HTML: redirect para /admin/professores
- cliente JSON: HTTP 201 com usuário criado

### PUT/PATCH /admin/professores/<user_id>

Permissão:
- apenas admin

Entrada:
- JSON ou form-data com nome/email/senha (opcionais)

Retorno:
- JSON sempre

### GET /admin/trilhas

Permissão:
- apenas admin

Retorno:
- HTML (admin_trilhas.html)

### GET /admin/tarefas-feedbacks

Permissão:
- apenas admin

Retorno:
- HTML (admin_tarefas.html)

### GET /admin/professores/novo

Permissão:
- apenas admin

Retorno:
- HTML (admin_professor_novo.html): jornada em 2 passos; ao confirmar chama POST /admin/professores (JSON 201) e volta para a lista

### GET /admin/professores/<user_id>

Permissão:
- apenas admin

Retorno:
- HTML (admin_professor_ficha.html): dados, trilhas atribuídas com status e progresso, feedbacks enviados
- 404 se o usuário não existir ou não for professor

### GET /admin/professores/<user_id>/trilhas
### GET /admin/trilhas/<trilha_id>/professores

Permissão:
- apenas admin

Retorno:
- HTML: jornada em 2 passos (Selecionar → Revisão) para atribuir/remover. 404 se o alvo não existir.

### PUT /admin/professores/<user_id>/trilhas
### PUT /admin/trilhas/<trilha_id>/professores

Permissão:
- apenas admin (CSRF obrigatório: header X-CSRFToken)

Entrada (JSON):
- atribuicoes: lista com o estado final desejado; o que não estiver na lista é removido
- cada item: {"trilha_id": 1, "status": "em_andamento"} (por professor) ou {"professor_id": 2, "status": "nao_iniciado"} (por trilha)
- status (opcional, padrão nao_iniciado): nao_iniciado | em_andamento | concluido

Regras:
- concluido só é aceito para atribuição que já está concluída (sem mudança); é calculado automaticamente
- nao_iniciado é recusado (400) se o professor já concluiu tarefas daquela trilha
- reabrir (concluido → em_andamento) limpa data_conclusao
- remover apaga as conclusões de tarefa do professor na trilha
- a operação é atômica: se qualquer item falhar nada é salvo

Retorno:
- 200 {"message": "...", "added": n, "updated": n, "removed": n}
- 400 {"error": "..."} (payload inválido, status inválido, id inexistente ou regra violada)
- 404 se o professor/trilha da URL não existir

### GET /admin/trilhas/<trilha_id>/conteudo

Permissão:
- apenas admin

Retorno:
- HTML (admin_trilha_conteudo.html): tarefas em ordem com editar, excluir e mover (usa POST /tasks/trilhas/<id>/reorder e DELETE /tasks/<id>)

### GET /admin/trilhas/<trilha_id>/tarefas/nova

Permissão:
- apenas admin

Retorno:
- HTML (admin_tarefa_nova.html): jornada em 2 passos; ao confirmar chama POST /trilhas/<trilha_id>/tasks

### GET /admin/professores/<user_id>/editar

Permissão:
- apenas admin

Retorno:
- HTML (admin_professor_editar.html): jornada em 2 passos (Dados → Revisão)
- 404 se o usuário não existir ou não for professor
- ao confirmar, a tela chama PATCH /admin/professores/<user_id> e volta para a lista

### GET /admin/trilhas/<trilha_id>/editar

Permissão:
- apenas admin

Retorno:
- HTML (admin_trilha_editar.html), 404 se a trilha não existir
- ao confirmar, a tela chama PATCH /trilhas/<trilha_id> e volta para a lista

### GET /admin/tarefas/<task_id>/editar

Permissão:
- apenas admin

Retorno:
- HTML (admin_tarefa_editar.html), 404 se a tarefa não existir
- ao confirmar, a tela chama PATCH /tasks/<task_id> e volta para a lista

## 6) Erros e status comuns

- 201: criação bem-sucedida
- 400: validação ou regra de negócio
- 403: acesso negado por role
- 404: recurso não encontrado (principalmente em professor/trilhas e professor/tarefas)

## 7) Observações para integração de front-end

- Endpoints do namespace /admin para listagem principal retornam HTML, não JSON.
- Endpoints do namespace /trilhas retornam JSON.
- Endpoints de professor GET são híbridos (HTML/JSON conforme Accept).
- Endpoints de completar/incompletar tarefa podem redirecionar no fluxo HTML tradicional.
