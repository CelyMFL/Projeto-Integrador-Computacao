(function () {
  'use strict';

  function announce(msg, isError) {
    if (window.A11y && window.A11y.announce) {
      window.A11y.announce(msg, !!isError);
    }
  }

  function confirmAction(msg) {
    if (window.A11y && window.A11y.confirmAction) {
      return window.A11y.confirmAction(msg);
    }
    return window.confirm(msg);
  }

  var createToggle = document.getElementById('create-trilha-toggle');
  var createFormPanel = document.getElementById('create-trilha-form');
  var createForm = document.getElementById('form-create-trilha');
  var cardsGrid = document.getElementById('trilhas-grid');

  function setCreateForm(open) {
    if (!createFormPanel || !createToggle) return;
    createFormPanel.style.display = open ? 'block' : 'none';
    createToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    if (open) {
      var nome = document.getElementById('trilha_nome');
      if (nome) nome.focus();
    }
  }

  if (createToggle) {
    createToggle.addEventListener('click', function () {
      var isHidden = createFormPanel.style.display === 'none' || !createFormPanel.style.display;
      setCreateForm(isHidden);
    });
  }

  // Filtro: mostra só trilhas que têm professores no status escolhido.
  var statusFilter = document.getElementById('trilha-status-filter');
  var noResults = document.getElementById('trilha-no-results');

  function filterTrilhas(shouldAnnounce) {
    var status = statusFilter.value;
    var visible = 0;
    document.querySelectorAll('#trilhas-grid .trail-card').forEach(function (card) {
      var show = !status || parseInt(card.getAttribute('data-count-' + status), 10) > 0;
      card.style.display = show ? '' : 'none';
      if (show) visible += 1;
    });
    if (noResults) noResults.hidden = visible > 0 || !status;
    if (shouldAnnounce && status) {
      announce(visible + (visible === 1 ? ' trilha encontrada.' : ' trilhas encontradas.'));
    }
  }

  if (statusFilter) {
    statusFilter.addEventListener('change', function () { filterTrilhas(true); });
    if (statusFilter.value) filterTrilhas(false);
  }

  var cancel = document.getElementById('create-trilha-cancel');
  if (cancel) {
    cancel.addEventListener('click', function () {
      setCreateForm(false);
    });
  }

  function element(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function buildCard(trilha) {
    var card = element('article', 'card trail-card');
    card.id = 'trilha-card-' + trilha.id;
    card.setAttribute('role', 'listitem');
    ['nao_iniciado', 'em_andamento', 'concluido'].forEach(function (status) {
      card.setAttribute('data-count-' + status, '0');
    });

    var header = element('div', 'card-header');
    header.appendChild(trilha.obrigatoria
      ? element('span', 'required', 'Obrigatória')
      : element('span', 'optional', 'Opcional'));
    if (trilha.tipo) header.appendChild(element('span', 'tag', trilha.tipo));

    var title = element('h3', '', trilha.nome);
    title.id = 'trilha-nome-' + trilha.id;
    var desc = element('p', '', trilha.descricao || '');
    desc.id = 'trilha-desc-' + trilha.id;

    var footer = element('div', 'card-footer');
    footer.appendChild(element('span', '', (trilha.tasks ? trilha.tasks.length : 0) + ' Tarefas'));
    var actions = element('div', 'actions');

    var content = element('a', 'button ghost', 'Conteúdo');
    content.href = '/admin/trilhas/' + trilha.id + '/conteudo';
    content.setAttribute('aria-label', 'Conteúdo da trilha ' + trilha.nome);
    var professors = element('a', 'button ghost', 'Professores');
    professors.href = '/admin/trilhas/' + trilha.id + '/professores';
    professors.setAttribute('aria-label', 'Professores da trilha ' + trilha.nome);
    var edit = element('a', 'button ghost', 'Editar');
    edit.href = '/admin/trilhas/' + trilha.id + '/editar';
    edit.setAttribute('aria-label', 'Editar trilha ' + trilha.nome);
    var del = element('button', 'button ghost', 'Excluir');
    del.type = 'button';
    del.setAttribute('aria-label', 'Excluir trilha ' + trilha.nome);
    del.addEventListener('click', function () { window.deleteTrilha(trilha.id); });

    actions.appendChild(content);
    actions.appendChild(professors);
    actions.appendChild(edit);
    actions.appendChild(del);
    footer.appendChild(actions);

    card.appendChild(header);
    card.appendChild(title);
    card.appendChild(desc);
    card.appendChild(footer);
    return card;
  }

  if (createForm) {
    createForm.addEventListener('submit', function (event) {
      event.preventDefault();

      if (!confirmAction('Confirma a criacao desta nova trilha?')) return;

      var data = new FormData(createForm);
      if (document.getElementById('trilha_obrigatoria').checked) {
        data.set('obrigatoria', 'true');
      }

      fetch('/trilhas/', {
        method: 'POST',
        headers: {
          'Accept': 'application/json',
          'X-CSRFToken': window.__adminCsrfToken,
        },
        body: data,
      }).then(async function (res) {
        var body = await res.json().catch(function () { return {}; });
        if (!res.ok) {
          announce('Erro ao criar trilha: ' + (body.error || res.status), true);
          return;
        }

        if (cardsGrid) cardsGrid.prepend(buildCard(body));
        createForm.reset();
        setCreateForm(false);
        announce('Trilha criada com sucesso.');
      });
    });
  }

  window.deleteTrilha = function (id) {
    if (!confirmAction('Tem certeza que deseja excluir esta trilha?')) return;

    fetch('/trilhas/' + id, {
      method: 'DELETE',
      headers: { 'X-CSRFToken': window.__adminCsrfToken },
    }).then(async function (res) {
      if (!res.ok) {
        var body = await res.json().catch(function () { return {}; });
        announce('Erro ao excluir trilha: ' + (body.error || res.status), true);
        return;
      }

      var card = document.getElementById('trilha-card-' + id);
      if (card) card.remove();
      announce('Trilha excluida com sucesso.');
    });
  };
})();
