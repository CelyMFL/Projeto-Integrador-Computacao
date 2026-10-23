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

Notas:
- Rotas sob /admin para listagens retornam HTML (padrão do projeto) — use JSON somente em endpoints que explicitamente retornam JSON.
- O dashboard administrativo atual usa gráficos e insights calculados no backend a partir de progresso, feedbacks e ativações de trilha.
- A UI admin utiliza atualização incremental para operações de criação/edição sem exigir recarga total da página em todos os fluxos.
