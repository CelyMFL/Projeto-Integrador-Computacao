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

  function normalize(text) {
    return (text || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();
  }

  function element(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function createProfessorCard(professor) {
    var card = element('div', 'card task-card prof-card pending');
    card.setAttribute('role', 'listitem');
    card.id = 'prof-card-' + professor.id;
    card.setAttribute('data-professor-search', (professor.nome + ' ' + professor.email).toLowerCase());
    card.setAttribute('data-status', 'nao_iniciado');

    var info = element('div', 'prof-info');
    var name = element('strong');
    var nameLink = element('a', '', professor.nome);
    nameLink.href = '/admin/professores/' + professor.id;
    name.appendChild(nameLink);
    var tag = element('a', 'tag', '0 Trilhas Atribuídas');
    tag.href = '/admin/professores/' + professor.id + '/trilhas';
    info.appendChild(name);
    info.appendChild(element('p', '', professor.email));
    info.appendChild(tag);
    info.appendChild(element('span', 'tag', 'Não iniciado'));

    var box = element('div', 'user-box');
    box.appendChild(element('span', '', 'Andamento Geral'));
    box.appendChild(element('strong', '', '0%'));

    var actions = element('div', 'prof-actions');
    var edit = element('a', 'button ghost', 'Editar');
    edit.href = '/admin/professores/' + professor.id + '/editar';
    edit.setAttribute('aria-label', 'Editar professor ' + professor.nome);
    var trilhas = element('a', 'button ghost', 'Trilhas');
    trilhas.href = '/admin/professores/' + professor.id + '/trilhas';
    trilhas.setAttribute('aria-label', 'Atribuir trilhas a ' + professor.nome);
    actions.appendChild(edit);
    actions.appendChild(trilhas);

    card.appendChild(info);
    card.appendChild(box);
    card.appendChild(actions);
    return card;
  }

  // Busca por trecho do nome/e-mail (ignora acentos e maiúsculas, exige todas as palavras) combinada com o filtro de status.
  var searchInput = document.getElementById('prof-search');
  var statusFilter = document.getElementById('prof-status-filter');
  var noResults = document.getElementById('prof-no-results');
  var searchTimer = null;

  function filterProfessors(shouldAnnounce) {
    var terms = normalize(searchInput ? searchInput.value : '').split(/\s+/).filter(Boolean);
    var status = statusFilter ? statusFilter.value : '';
    var visibleCount = 0;

    document.querySelectorAll('[data-professor-search]').forEach(function (card) {
      var haystack = normalize(card.getAttribute('data-professor-search'));
      var matchesText = terms.every(function (term) { return haystack.indexOf(term) !== -1; });
      var matchesStatus = !status || card.getAttribute('data-status') === status;
      var visible = matchesText && matchesStatus;
      card.style.display = visible ? '' : 'none';
      if (visible) visibleCount += 1;
    });

    var filtering = terms.length > 0 || status !== '';
    if (noResults) noResults.hidden = visibleCount > 0 || !filtering;
    if (shouldAnnounce && filtering) {
      announce(visibleCount + (visibleCount === 1 ? ' professor encontrado.' : ' professores encontrados.'));
    }
  }

  if (searchInput) {
    searchInput.addEventListener('input', function () {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(function () { filterProfessors(true); }, 200);
    });
  }

  if (statusFilter) {
    statusFilter.addEventListener('change', function () { filterProfessors(true); });
    if (statusFilter.value) filterProfessors(false);
  }

  var form = document.getElementById('create-professor-form');
  if (!form) return;

  form.addEventListener('submit', function (event) {
    event.preventDefault();

    if (!confirmAction('Confirma a criacao deste novo professor?')) return;

    var formData = new FormData(form);

    fetch(form.action, {
      method: 'POST',
      headers: {
        'Accept': 'application/json',
        'X-CSRFToken': window.__adminCsrfToken,
      },
      body: formData,
    }).then(async function (res) {
      var body = await res.json().catch(function () { return {}; });
      if (!res.ok) {
        announce('Erro ao criar professor: ' + (body.error || res.status), true);
        return;
      }

      var list = document.getElementById('professores-list');
      if (list) {
        list.prepend(createProfessorCard(body));
      }
      form.reset();
      announce('Professor criado com sucesso.');
    });
  });
})();
