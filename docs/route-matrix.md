# Route Matrix

Resumo rápido (método → path → papel → retorno / nota)

Validação recente:
- a plataforma foi exercitada com smoke tests em `auth`, `admin`, `professor`, `tasks` e `trilhas`
- a exclusão de trilha passou a limpar dependências antes do `DELETE`
- o dashboard do professor e o contrato de progresso usam `completion_percentage` no endpoint JSON de progresso

- GET /auth/login -> pública -> HTML (login page)
- POST /auth/login -> pública -> form-data -> redirect por role (admin -> /admin, prof -> /professor/dashboard)
- GET /auth/logout -> autenticado -> encerra sessão + redirect

Professor:
- GET /professor/dashboard -> professor -> HTML (dashboard) ou JSON quando Accept: application/json
- GET /professor/trilhas/<id> -> professor -> HTML/JSON
- GET /professor/tarefas/<id> -> professor -> HTML/JSON
- GET /professor/feedback -> professor -> HTML/JSON contexto formulário
- POST /professor/feedback -> professor -> aceita form-data/JSON -> HTML redirect ou JSON 201

Tasks:
- POST /tasks/<id>/complete -> professor -> marca completo
- POST /tasks/<id>/incomplete -> professor -> marca pendente
- GET /tasks/<id>/status -> professor -> JSON
- PUT/PATCH /tasks/<id> -> admin -> atualiza
- DELETE /tasks/<id> -> admin -> deleta
- POST /tasks/trilhas/<trilha_id>/reorder -> admin -> reordena

Trilhas:
- GET /trilhas/ -> autenticado -> JSON lista
- GET /trilhas/<id> -> autenticado -> JSON
- POST /trilhas/ -> admin -> cria
- PUT/PATCH /trilhas/<id> -> admin -> atualiza
- DELETE /trilhas/<id> -> admin -> deleta
- POST /trilhas/<id>/start -> professor -> inicia matrícula
- GET /trilhas/<id>/progress -> professor -> progresso JSON
- POST /trilhas/<id>/tasks -> admin -> cria task na trilha

Admin (telas HTML):
- GET /admin/ -> admin -> HTML (dashboard)
- GET /admin/analytics -> admin -> JSON (summary + analytics para gráficos/insights)
- GET /admin/professores -> admin -> HTML
- POST /admin/professores -> admin -> cria (form) -> HTML redirect ou JSON 201
- PUT/PATCH /admin/professores/<id> -> admin -> atualiza (JSON)
- GET /admin/trilhas -> admin -> HTML
- GET /admin/tarefas-feedbacks -> admin -> HTML
- GET /admin/professores/<id>/editar -> admin -> HTML (tela de edição em jornada; 404 se não for professor)
- GET /admin/trilhas/<id>/editar -> admin -> HTML (tela de edição em jornada; 404 se inexistente)
- GET /admin/tarefas/<id>/editar -> admin -> HTML (tela de edição em jornada; 404 se inexistente)
- GET /admin/professores/<id> -> admin -> HTML (ficha: dados, trilhas com status/progresso, feedbacks)
- GET /admin/professores/<id>/trilhas -> admin -> HTML (atribuir/remover trilhas do professor)
- PUT /admin/professores/<id>/trilhas -> admin -> JSON (sincroniza atribuições; 400 em payload/status inválido)
- GET /admin/trilhas/<id>/professores -> admin -> HTML (atribuir/remover professores da trilha)
- PUT /admin/trilhas/<id>/professores -> admin -> JSON (sincroniza atribuições)
- GET /admin/trilhas/<id>/conteudo -> admin -> HTML (tarefas da trilha: ordem, editar, excluir)
- GET /admin/trilhas/<id>/tarefas/nova -> admin -> HTML (jornada para criar tarefa; salva via POST /trilhas/<id>/tasks)
- GET /admin/professores/novo -> admin -> HTML (jornada de cadastro; salva via POST /admin/professores)
- GET /admin/trilhas?status=<status> -> pré-seleciona o filtro "trilhas com professores nesse status"

Notas:
- Rotas sob /admin para listagens retornam HTML (padrão do projeto) — use JSON somente em endpoints que explicitamente retornam JSON.
- O dashboard administrativo atual usa gráficos e insights calculados no backend a partir de progresso, feedbacks e ativações de trilha.
- As telas de edição só renderizam o formulário; o salvamento reaproveita PATCH /admin/professores/<id>, PATCH /trilhas/<id> e PATCH /tasks/<id>.
- Status da atribuição professor × trilha: `nao_iniciado` (atribuída pelo admin) → `em_andamento` (professor inicia a trilha ou conclui a 1ª tarefa) → `concluido` (todas as tarefas feitas, automático). O admin pode alternar entre `nao_iniciado` e `em_andamento` e reabrir uma trilha concluída; `nao_iniciado` é recusado se já há tarefas concluídas.
- POST /trilhas/<id>/start também funciona para trilha já atribuída como `nao_iniciado` (passa para `em_andamento`).
- DELETE /tasks/<id> também apaga as conclusões de professores daquela tarefa (FK em professor_checklists).
- No HTML do professor, links de apoio e documento só viram <a> se forem http(s); documentos aceitam ainda PDF local e link do Drive.
- Remover uma atribuição apaga as conclusões de tarefa do professor naquela trilha.
- O nome da trilha é gravado com iniciais maiúsculas (preposições como "de" e "ao" ficam minúsculas; siglas são preservadas).
- A UI admin utiliza atualização incremental para operações de criação/edição sem exigir recarga total da página em todos os fluxos.
