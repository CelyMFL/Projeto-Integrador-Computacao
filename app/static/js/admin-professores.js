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

  function createProfessorCard(professor) {
    var card = document.createElement('div');
    card.className = 'card task-card pending';
    card.setAttribute('role', 'listitem');
    card.setAttribute('id', 'prof-card-' + professor.id);
    card.innerHTML =
      '<div><strong>' + professor.nome + '</strong><p>' + professor.email + '</p><span class="tag">0 Trilhas Atribuidas</span></div>' +
      '<div class="user-box"><span>Andamento Geral</span><strong>0%</strong></div>' +
      '<button type="button" class="button ghost" aria-expanded="false" aria-controls="prof-edit-' + professor.id + '" onclick="toggleProfessorEdit(' + professor.id + ')">Editar</button>';
    return card;
  }

  window.toggleProfessorEdit = function (id) {
    var box = document.getElementById('prof-edit-' + id);
    if (!box) return;
    var isHidden = box.style.display === 'none' || !box.style.display;
    box.style.display = isHidden ? 'block' : 'none';
    if (isHidden) {
      var first = box.querySelector('input');
      if (first) first.focus();
    }
  };

  window.submitProfessorEdit = function (id) {
    var nomeNode = document.getElementById('prof-nome-' + id);
    var emailNode = document.getElementById('prof-email-' + id);
    var senhaNode = document.getElementById('prof-senha-' + id);

    if (!nomeNode || !emailNode) return;

    var payload = {
      nome: nomeNode.value.trim(),
      email: emailNode.value.trim(),
    };

    if (senhaNode && senhaNode.value) {
      payload.senha = senhaNode.value;
    }

    if (!confirmAction('Confirma salvar as alteracoes deste professor?')) return;

    fetch('/admin/professores/' + id, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': window.__adminCsrfToken,
      },
      body: JSON.stringify(payload),
    }).then(async function (res) {
      if (!res.ok) {
        var bodyErr = await res.json().catch(function () { return {}; });
        announce('Erro ao atualizar professor: ' + (bodyErr.error || res.status), true);
        return;
      }

      var card = document.getElementById('prof-card-' + id);
      if (card) {
        var title = card.querySelector('strong');
        var email = card.querySelector('p');
        if (title) title.textContent = payload.nome;
        if (email) email.textContent = payload.email;
      }

      announce('Professor atualizado com sucesso.');
      window.toggleProfessorEdit(id);
    });
  };

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
