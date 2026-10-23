# Estratégia de Observabilidade do Produto

Documento de referência para medir comportamento de uso, qualidade de jornada e impactos de mudanças no onboarding docente.

## Objetivos

- detectar gargalos de adoção e conclusão
- medir uso real das áreas críticas
- apoiar decisões de UX e conteúdo com evidência

## Camadas de observabilidade

## 1) Métricas operacionais (já disponíveis)

- concluídas x em andamento
- evolução mensal de feedback
- ativação de trilhas (início da jornada)

## 2) Métricas de experiência (parcial)

- tempo médio de conclusão por trilha
- conclusão média por trilha

## 3) Métricas de acesso detalhado (pendente)

Planejar instrumentação por eventos:
- login efetuado
- dashboard visualizado
- trilha aberta
- tarefa aberta
- tarefa concluída
- feedback enviado

Campos mínimos por evento:
- `event_name`
- `user_id`
- `role`
- `entity_type` (trilha, tarefa, tela)
- `entity_id`
- `occurred_at`
- `metadata` (json com contexto)

## Padrões de coleta

- Coleta server-side para ações críticas
- Coleta client-side para interações de UX (ex.: filtro, drill-down)
- Persistência assíncrona quando possível para reduzir impacto de latência

## Alertas e monitoramento

Alertas de produto sugeridos:
- queda de ativação semanal acima de 20%
- queda de conclusão média por trilha acima de 15%
- aumento de feedback negativo por tema

## Rotina de análise

1. Revisão semanal de indicadores do dashboard
2. Revisão quinzenal de trilhas com pior conclusão
3. Revisão mensal de melhorias de UX com análise pré/pós

## Roadmap de evolução

Fase 1:
- consolidar métricas atuais e qualidade de dados
- padronizar nomenclatura de indicadores

Fase 2:
- implementar tabela de eventos de uso
- adicionar painel de acesso por tela/rota

Fase 3:
- calcular tempo ativo por tarefa
- gerar insights preditivos de abandono
