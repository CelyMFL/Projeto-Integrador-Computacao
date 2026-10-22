# Projeto Integrador - Onboarding Docente

Aplicação Flask para onboarding de professores com autenticação por sessão, trilhas, tarefas, acompanhamento de progresso e feedback.

O projeto combina duas formas de entrega no mesmo backend:
- telas HTML server-side renderizadas com Jinja2
- endpoints JSON para integração com front-end/API clients

## Escopo atual

Perfis:
- professor
- admin

Fluxos implementados:
- login/logout com Flask-Login
- dashboard do professor (trilhas atribuídas, progresso geral, próximas tarefas)
- detalhe de trilha e detalhe de tarefa
- marcar tarefa como concluída/pendente
- envio de feedback do professor
- painel administrativo com métricas
- gestão administrativa de professores, trilhas e tarefas

## Arquitetura

Camadas principais:
- routes: contratos HTTP e controle de acesso
- services: regras de negócio e validações
- models: entidades SQLAlchemy
- templates/static: interface renderizada pelo backend
- database: MySQL

Estrutura:
- app/models
- app/services
- app/routes
- app/templates
- app/static
- app/__init__.py

## Stack

- Python 3
- Flask
- Flask-Login
- Flask-SQLAlchemy / SQLAlchemy
- PyMySQL
- MySQL 8 (docker-compose)

## Execução local

1. Crie o arquivo `.env` a partir do exemplo:

```bash
cp .env.example .env
```

No Windows PowerShell, use `Copy-Item .env.example .env`.

2. Subir MySQL:

```bash
docker compose up -d
```

3. Instalar dependências:

```bash
pip install -r requirements.txt
```

4. Criar schema:

```bash
python create_db.py
```

5. Rodar app:

```bash
python run.py
```

Aplicação: http://localhost:5000

## Publicar imagem no Azure Container Registry

O script `deploy_acr.py` constrói e publica uma nova versão da imagem no ACR,
sem alterar o Azure App Service. Consulte o [guia de publicação no Azure](docs/deploy-acr.md)
para pré-requisitos, detalhes do versionamento e instruções completas.

Simule antes de publicar:

```bash
python deploy_acr.py --dry-run
```

Para publicar a imagem no ACR:

```bash
python deploy_acr.py
```

## Atualizações recentes

- telas administrativas ganharam formulários inline para criar/editar trilhas, criar tarefas e editar professores
- `seed.py` foi ajustado para resetar o banco MySQL com segurança operacional, inclusive em presença de FKs legadas
- a exclusão de trilha agora remove dependências ligadas (`feedbacks`, `professor_trilhas` e `professor_checklists`) antes de apagar a trilha
- a plataforma foi validada com smoke tests exaustivos em `auth`, `admin`, `professor`, `tasks` e `trilhas`

## Popular dados de desenvolvimento (opcional)

Para resetar e popular o banco com dados de exemplo:

```bash
python seed.py
```

Credenciais de seed:
- admin: admin@test.com / 123
- professor: prof@test.com / 123

## Modelo de dados

User:
- id, nome, email, senha (hash)
- role: professor | admin

Checklist (trilha):
- id, nome, descricao
- tipo: pedagógica | institucional | tecnológica
- obrigatoria (bool)

Task:
- id, descricao, ordem
- checklist_id
- material_apoio, link_apoio, documento_apoio

ProfessorTrilha:
- professor_id, trilha_id
- status: nao_iniciado | em_andamento | concluido
- data_inicio, data_conclusao

ProfessorChecklist:
- professor_id, task_id
- concluido, data_conclusao

Feedback:
- professor_id
- trilha_id (opcional)
- comentario, data_envio

## Rotas principais

### Autenticação

- GET /auth/login: tela de login
- POST /auth/login: autentica e redireciona por role
- GET /auth/logout: encerra sessão

### Professor

- GET /professor/dashboard
- GET /professor/trilhas/<trilha_id>
- GET /professor/tarefas/<task_id>
- GET /professor/feedback
- POST /professor/feedback

Observação de resposta:
- as rotas GET acima retornam HTML por padrão no navegador
- retornam JSON somente quando o cliente pede explicitamente Accept: application/json (sem preferência por HTML)

### Tasks

- POST /tasks/<task_id>/complete
- POST /tasks/<task_id>/incomplete
- GET /tasks/<task_id>/status
- PUT/PATCH /tasks/<task_id> (admin)
- DELETE /tasks/<task_id> (admin)
- POST /tasks/trilhas/<trilha_id>/reorder (admin)

### Trilhas

- GET /trilhas/
- GET /trilhas/<trilha_id>
- POST /trilhas/ (admin)
- PUT/PATCH /trilhas/<trilha_id> (admin)
- DELETE /trilhas/<trilha_id> (admin)
- POST /trilhas/<trilha_id>/start (professor)
- GET /trilhas/<trilha_id>/progress (professor)
- POST /trilhas/<trilha_id>/tasks (admin)

### Admin

- GET /admin/: dashboard HTML
- GET /admin/analytics: métricas JSON
- GET /admin/professores: gestão HTML
- POST /admin/professores: cria professor (redirect HTML ou JSON 201)
- PUT/PATCH /admin/professores/<user_id>: atualiza professor (JSON)
- GET /admin/trilhas: gestão HTML
- GET /admin/tarefas-feedbacks: gestão HTML

## Permissões

- rotas /admin: somente admin
- jornada /professor: somente professor
- create/update/delete de trilha/tarefa: somente admin
- completar tarefa e consultar status da própria tarefa: somente professor
- /trilhas/ (listar/obter): exige login, sem restrição explícita por role

## Regras de negócio importantes

- ao concluir tarefa, o sistema registra ProfessorChecklist e tenta concluir automaticamente a trilha quando todas as tarefas estão concluídas
- ao voltar tarefa para pendente, trilha concluída pode retornar para em_andamento
- ordenação de tarefas usa campo ordem e endpoint dedicado de reorder
- ao remover uma trilha, o serviço também remove feedbacks, vínculos de professor e conclusões de tarefas associados para evitar falhas de integridade

## Validação realizada

Smoke tests executados com sucesso cobrindo:
- autenticação e logout
- páginas administrativas HTML
- criação/edição/exclusão de trilha
- criação/edição/exclusão de tarefa
- dashboard e páginas JSON do professor
- envio de feedback
- marcação de tarefa concluída e pendente

Observação:
- `GET /trilhas/<id>/progress` retorna `completion_percentage` no JSON atual

## Documentação da API

Detalhes de payloads e modos de resposta estão em:
- docs/frontend-api-reference.md

## Observações técnicas

- sem migrations automáticas: schema é gerenciado com create_all/drop_all
- seed.py executa drop_all e apaga dados existentes
- app/services/checklist_service.py está presente, porém sem implementação
