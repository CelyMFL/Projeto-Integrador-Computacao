# Glossário de Métricas e Insights

Este documento define as métricas exibidas no dashboard administrativo e seus critérios de cálculo.

## Fonte de dados

- `users`
- `checklists`
- `tasks`
- `professor_trilhas`
- `professor_checklists`
- `feedbacks`

## Métricas de sumário

### total_users
Quantidade total de usuários cadastrados.

### total_professores
Quantidade de usuários com `role = professor`.

### total_trilhas
Quantidade de trilhas cadastradas.

### total_obrigatorias
Quantidade de trilhas com `obrigatoria = true`.

### total_feedbacks
Quantidade total de feedbacks recebidos.

### trilhas_concluidas
Total de registros em `professor_trilhas` com `status = concluido`.

### trilhas_em_andamento
Total de registros em `professor_trilhas` com `status = em_andamento`.

### conclusao_global_percentual
Cálculo: `trilhas_concluidas / total_jornadas * 100`.

### tempo_medio_conclusao_dias
Média de dias entre `data_inicio` e `data_conclusao` para trilhas concluídas com ambos os campos preenchidos.

### feedbacks_ultimos_30_dias
Contagem de `feedbacks` com `data_envio` nos últimos 30 dias.

### ativacoes_ultimos_30_dias
Contagem de registros de `professor_trilhas` com `data_inicio` nos últimos 30 dias.

## Séries de gráficos

### status_distribution
Distribuição de jornadas por status:
- não iniciado
- em andamento
- concluído

### trilhas_por_tipo
Distribuição de trilhas por tipo:
- pedagógica
- institucional
- tecnológica

### feedback_timeline
Série temporal mensal de feedbacks.

### ativacoes_timeline
Série temporal mensal de ativações de trilha (proxy de acesso/engajamento).

### completion_by_trilha
Para cada trilha:
1. identifica tarefas da trilha
2. calcula percentual de conclusão por professor inscrito
3. calcula média dos percentuais da trilha

## Insights automáticos

O backend gera frases orientativas usando:
- taxa global de conclusão
- tempo médio de conclusão
- atividade recente (feedback e ativações)
- melhor e pior trilha por conclusão média

## Limitações atuais

- não há tracking de sessão por página em nível de evento (acesso detalhado por rota)
- tempo de estudo é inferido por jornada de trilha, não por tempo ativo de tarefa

## Evolução recomendada

- adicionar eventos de acesso por rota e sessão
- registrar tempo ativo por tarefa
- separar métricas de adoção, engajamento, conclusão e satisfação em coortes
