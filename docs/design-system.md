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
- Edição de registros no admin acontece em tela própria ("jornada"), nunca em painel inline: breadcrumb, indicador de passos (`journey-steps`), passo 1 "Dados", passo 2 "Revisão" e confirmação. Base em `admin/editar_base.html` e `js/admin-editar.js`
- Campos de formulário admin usam borda suave (`--admin-border`), raio de 12px, altura mínima de 44px e anel de foco `--admin-primary`
- Atribuição (professor ↔ trilha) usa a mesma jornada em 2 passos: Selecionar (checkbox + status por linha) e Revisão (lista do que será adicionado, alterado e removido, com aviso destacado quando há progresso a apagar). Base em `admin/atribuicao_base.html` e `js/admin-atribuicao.js`
- Cadastro e edição de registros ficam em páginas próprias; a lista só tem busca e o botão "+ Novo ..."
- Status pertence à atribuição professor × trilha e só aparece em telas de trilha/atribuição, nunca como status "do professor" na lista
- Status de atribuição aparece sempre como texto (Não iniciado, Em andamento, Concluído) com `status-pill`/`tag`, nunca só por cor
- Reordenar itens usa botões "mover para cima/baixo" com `aria-label` (sem arrastar e soltar), anunciando a nova posição
- Listas admin com filtro de status combinam o filtro com a busca por texto
- Buscas em listas ignoram acentos e maiúsculas e exigem todas as palavras digitadas (ex.: `admin-professores.js`)

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
