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

  var list = document.getElementById('content-list');
  if (!list) return;

  var empty = document.getElementById('content-empty');

  function rows() {
    return Array.prototype.slice.call(list.querySelectorAll('.content-row'));
  }

  function renumber() {
    rows().forEach(function (row, index) {
      row.querySelector('.content-order').textContent = index + 1;
    });
  }

  function request(url, method, body) {
    var headers = { 'Accept': 'application/json', 'X-CSRFToken': window.__adminCsrfToken };
    if (body) headers['Content-Type'] = 'application/json';
    return fetch(url, { method: method, headers: headers, body: body ? JSON.stringify(body) : undefined })
      .then(async function (res) {
        var data = await res.json().catch(function () { return {}; });
        return { ok: res.ok, status: res.status, data: data };
      });
  }

  function move(row, direction) {
    var sibling = direction === 'up' ? row.previousElementSibling : row.nextElementSibling;
    if (!sibling) return;

    var previousOrder = rows();
    if (direction === 'up') {
      list.insertBefore(row, sibling);
    } else {
      list.insertBefore(sibling, row);
    }
    renumber();

    var ids = rows().map(function (item) { return parseInt(item.getAttribute('data-task-id'), 10); });
    request(list.getAttribute('data-reorder-url'), 'POST', { task_ids: ids }).then(function (res) {
      if (!res.ok) {
        // Desfaz a mudança visual se o servidor recusou.
        previousOrder.forEach(function (item) { list.appendChild(item); });
        renumber();
        announce('Erro ao reordenar: ' + (res.data.error || res.status), true);
        return;
      }
      announce('Tarefa movida para a posição ' + (ids.indexOf(parseInt(row.getAttribute('data-task-id'), 10)) + 1) + '.');
    });

    var button = row.querySelector('[data-move="' + direction + '"]');
    if (button) button.focus();
  }

  function remove(row) {
    var name = row.getAttribute('data-descricao');
    if (!confirmAction('Tem certeza que deseja excluir a tarefa "' + name + '"?')) return;

    request(row.getAttribute('data-delete-url'), 'DELETE').then(function (res) {
      if (!res.ok) {
        announce('Erro ao excluir tarefa: ' + (res.data.error || res.status), true);
        return;
      }
      row.remove();
      renumber();
      if (empty) empty.hidden = rows().length > 0;
      announce('Tarefa excluída com sucesso.');
    });
  }

  list.addEventListener('click', function (event) {
    var target = event.target.closest('button');
    if (!target) return;
    var row = target.closest('.content-row');
    if (!row) return;

    if (target.hasAttribute('data-move')) {
      move(row, target.getAttribute('data-move'));
    } else if (target.hasAttribute('data-delete')) {
      remove(row);
    }
  });
})();
