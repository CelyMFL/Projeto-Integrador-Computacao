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

  var cancel = document.getElementById('create-trilha-cancel');
  if (cancel) {
    cancel.addEventListener('click', function () {
      setCreateForm(false);
    });
  }

  function buildCard(trilha) {
    var card = document.createElement('article');
    card.className = 'card trail-card';
    card.id = 'trilha-card-' + trilha.id;
    card.setAttribute('role', 'listitem');

    var badge = trilha.obrigatoria
      ? '<span class="required">Obrigatoria</span>'
      : '<span class="optional">Opcional</span>';

    var tipo = trilha.tipo ? '<span class="tag">' + trilha.tipo + '</span>' : '';

    card.innerHTML =
      '<div class="card-header">' + badge + tipo + '</div>' +
      '<h3 id="trilha-nome-' + trilha.id + '">' + trilha.nome + '</h3>' +
      '<p id="trilha-desc-' + trilha.id + '">' + (trilha.descricao || '') + '</p>' +
      '<div class="card-footer"><span>' + (trilha.tasks ? trilha.tasks.length : 0) + ' Tarefas</span>' +
      '<div class="actions">' +
      '<button onclick="openEditTrilha(' + trilha.id + ')" class="button ghost" aria-expanded="false" aria-controls="edit-trilha-' + trilha.id + '">Editar</button>' +
      '<button onclick="deleteTrilha(' + trilha.id + ')" class="button ghost" aria-label="Excluir trilha">Excluir</button>' +
      '</div></div>' +
      '<div id="edit-trilha-' + trilha.id + '" class="card" style="display:none; margin-top:10px;" role="group" aria-label="Editar trilha">' +
      '<div class="form-group"><label for="edit-nome-' + trilha.id + '">Nome</label><input type="text" id="edit-nome-' + trilha.id + '" value="' + trilha.nome + '" /></div>' +
      '<div class="form-group"><label for="edit-desc-' + trilha.id + '">Descricao</label><input type="text" id="edit-desc-' + trilha.id + '" value="' + (trilha.descricao || '') + '" /></div>' +
      '<div class="actions"><button type="button" class="button" onclick="submitEditTrilha(' + trilha.id + ')">Salvar</button><button type="button" class="button secondary" onclick="closeEditTrilha(' + trilha.id + ')">Cancelar</button></div>' +
      '</div>';

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

  window.openEditTrilha = function (id) {
    var panel = document.getElementById('edit-trilha-' + id);
    if (!panel) return;
    panel.style.display = 'block';
    var first = panel.querySelector('input');
    if (first) first.focus();
  };

  window.closeEditTrilha = function (id) {
    var panel = document.getElementById('edit-trilha-' + id);
    if (panel) panel.style.display = 'none';
  };

  window.submitEditTrilha = function (id) {
    var nome = document.getElementById('edit-nome-' + id).value;
    var descricao = document.getElementById('edit-desc-' + id).value;

    if (!confirmAction('Confirma salvar as alteracoes desta trilha?')) return;

    fetch('/trilhas/' + id, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': window.__adminCsrfToken,
      },
      body: JSON.stringify({ nome: nome, descricao: descricao }),
    }).then(async function (res) {
      var body = await res.json().catch(function () { return {}; });
      if (!res.ok) {
        announce('Erro ao atualizar trilha: ' + (body.error || res.status), true);
        return;
      }

      var nomeNode = document.getElementById('trilha-nome-' + id);
      var descNode = document.getElementById('trilha-desc-' + id);
      if (nomeNode) nomeNode.textContent = body.nome;
      if (descNode) descNode.textContent = body.descricao || '';

      announce('Trilha atualizada com sucesso.');
      window.closeEditTrilha(id);
    });
  };

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
