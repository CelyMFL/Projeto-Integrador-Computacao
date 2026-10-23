# Design System do Front-end

Este documento define a base visual e de interação do projeto, com foco em consistência, acessibilidade e evolução iterativa.

## Objetivos

- padronizar tokens visuais (cores, tipografia, espaçamento e bordas)
- reduzir divergência entre telas server-side
- acelerar entregas de UI sem regressão de usabilidade

## Escopo atual

- Tema geral em `app/static/style.css`
- Tema administrativo em `app/static/css/admin-modern.css`
- Regras de acessibilidade em `app/static/css/accessibility.css` e `app/static/js/accessibility.js`

## Tokens principais

Tema base (plataforma):
- `--primary`, `--primary-dark`: ação primária
- `--success`, `--warning`: estados
- `--bg`, `--surface`, `--border`: superfícies e contraste

Tema admin (jornada):
- `--admin-primary`, `--admin-accent`: direção visual das telas de gestão
- `--admin-ok`, `--admin-warn`, `--admin-danger`: semântica de feedback
- `--admin-bg`, `--admin-surface`, `--admin-border`: atmosfera e legibilidade

## Tipografia

- Base da plataforma: Arial/Helvetica (legado)
- Admin: família `Manrope` para hierarquia mais clara em métricas e navegação
- Escalas devem priorizar leitura em desktop e mobile com no mínimo 16px para corpo

## Componentes canônicos

- Navegação: `topnav` e `admin-topnav`
- Cartões: `card`, `metric-tile`, `panel`
- Ações: `button`, `button secondary`, `button ghost`, `button danger`
- Listas de fluxo: `task-list`, `task-preview-list`, `feedback-stream`
- Estado/etiqueta: `tag`, `status-pill`, `required`, `optional`

## Padrões de interação

- Ações destrutivas exigem confirmação (`A11y.confirmAction`)
- Feedback de operação é anunciado por região viva (`A11y.announce`)
- Atualizações incrementais priorizadas em telas admin para reduzir recarga total

## Responsividade

- Grid 2 e 3 colunas colapsa para 1 coluna em viewport menor que 960px
- Navegação principal usa wrapping para evitar corte de ações
- Elementos de formulário ocupam largura disponível

## Acessibilidade mínima para novas telas

- landmarks semânticas (`header`, `main`, `nav`, `section`, `aside`)
- alvos de toque de no mínimo 44x44
- foco visível com `:focus-visible`
- rótulos explícitos para campos
- estados comunicados por texto, não apenas por cor

## Governança

Antes de abrir PR de front-end:
1. validar consistência com os componentes canônicos
2. validar contraste e foco visível
3. validar navegação por teclado e leitor de tela para fluxos críticos
4. validar em desktop e mobile
