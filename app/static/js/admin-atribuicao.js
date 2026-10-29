(function () {
  'use strict';

  var STATUS_LABELS = {
    nao_iniciado: 'Não iniciado',
    em_andamento: 'Em andamento',
    concluido: 'Concluído',
  };

  function announce(msg, isError) {
    if (window.A11y && window.A11y.announce) {
      window.A11y.announce(msg, !!isError);
    }
  }

  function normalize(text) {
    return (text || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim();
  }

  var form = document.getElementById('assign-form');
  if (!form) return;

  var steps = form.querySelectorAll('[data-step]');
  var pills = document.querySelectorAll('[data-step-pill]');
  var rowNodes = Array.prototype.slice.call(form.querySelectorAll('.assign-row'));
  var reviewList = document.getElementById('review-changes');
  var reviewEmpty = document.getElementById('review-empty');
  var saveButton = document.getElementById('assign-save');
  var statusNode = document.getElementById('form-status');
  var searchInput = document.getElementById('assign-search');
  var noResults = document.getElementById('assign-no-results');
  var key = form.getAttribute('data-key');

  function showStep(number) {
    steps.forEach(function (step) {
      step.hidden = step.getAttribute('data-step') !== String(number);
    });
    pills.forEach(function (pill) {
      var active = pill.getAttribute('data-step-pill') === String(number);
      pill.classList.toggle('current', active);
      if (active) {
        pill.setAttribute('aria-current', 'step');
      } else {
        pill.removeAttribute('aria-current');
      }
    });
    statusNode.textContent = '';
    var title = document.getElementById('step-' + number + '-title');
    if (title) title.focus();
  }

  function state(row) {
    var check = row.querySelector('.assign-check');
    var select = row.querySelector('.assign-status-select');
    return {
      id: parseInt(row.getAttribute('data-id'), 10),
      label: row.getAttribute('data-label'),
      checked: check.checked,
      status: select.value,
      initialChecked: row.getAttribute('data-initial-checked') === 'true',
      initialStatus: row.getAttribute('data-initial-status'),
      concluidas: parseInt(row.getAttribute('data-concluidas'), 10) || 0,
    };
  }

  rowNodes.forEach(function (row) {
    var check = row.querySelector('.assign-check');
    var select = row.querySelector('.assign-status-select');
    check.addEventListener('change', function () {
      select.disabled = !check.checked;
    });
  });

  // Busca por trecho do nome: ignora acentos e maiúsculas e exige todas as palavras.
  var searchTimer = null;
  function filterRows() {
    var terms = normalize(searchInput.value).split(/\s+/).filter(Boolean);
    var visible = 0;
    rowNodes.forEach(function (row) {
      var haystack = normalize(row.getAttribute('data-search'));
      var match = terms.every(function (term) { return haystack.indexOf(term) !== -1; });
      row.style.display = match ? '' : 'none';
      if (match) visible += 1;
    });
    noResults.hidden = visible > 0;
    if (terms.length) {
      announce(visible + (visible === 1 ? ' resultado.' : ' resultados.'));
    }
  }
  if (searchInput) {
    searchInput.addEventListener('input', function () {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(filterRows, 200);
    });
  }

  function plural(count, one, many) {
    return count + ' ' + (count === 1 ? one : many);
  }

  // Monta as mudanças e os problemas que impedem salvar.
  function collectChanges() {
    var changes = [];
    var problems = [];

    rowNodes.map(state).forEach(function (item) {
      if (item.checked && !item.initialChecked) {
        changes.push({ kind: 'add', text: 'Adicionar "' + item.label + '" como ' + STATUS_LABELS[item.status] + '.' });
      } else if (!item.checked && item.initialChecked) {
        var text = 'Remover "' + item.label + '".';
        var warn = item.concluidas > 0
          ? ' Atenção: ' + plural(item.concluidas, 'tarefa concluída será apagada', 'tarefas concluídas serão apagadas') + '.'
          : '';
        changes.push({ kind: 'remove', text: text + warn, warning: item.concluidas > 0 });
      } else if (item.checked && item.status !== item.initialStatus) {
        if (item.status === 'nao_iniciado' && item.concluidas > 0) {
          problems.push('"' + item.label + '" já tem ' + plural(item.concluidas, 'tarefa concluída', 'tarefas concluídas') +
            ' e não pode voltar para Não iniciado.');
          return;
        }
        var extra = item.initialStatus === 'concluido' ? ' (a trilha será reaberta)' : '';
        changes.push({
          kind: 'update',
          text: 'Alterar o status de "' + item.label + '": ' + STATUS_LABELS[item.initialStatus] + ' → ' +
            STATUS_LABELS[item.status] + extra + '.',
        });
      }
    });

    return { changes: changes, problems: problems };
  }

  function buildReview() {
    var result = collectChanges();
    reviewList.textContent = '';

    result.problems.forEach(function (problem) {
      var li = document.createElement('li');
      li.className = 'review-problem';
      li.textContent = 'Corrija antes de salvar: ' + problem;
      reviewList.appendChild(li);
    });

    result.changes.forEach(function (change) {
      var li = document.createElement('li');
      li.className = 'review-' + change.kind + (change.warning ? ' review-warning' : '');
      li.textContent = change.text;
      reviewList.appendChild(li);
    });

    var nothing = result.changes.length === 0 && result.problems.length === 0;
    reviewEmpty.hidden = !nothing;
    saveButton.disabled = nothing || result.problems.length > 0;
  }

  form.querySelector('[data-next]').addEventListener('click', function () {
    buildReview();
    showStep(2);
  });

  form.querySelector('[data-back]').addEventListener('click', function () {
    showStep(1);
  });

  form.addEventListener('submit', function (event) {
    event.preventDefault();
    statusNode.textContent = '';

    var items = rowNodes.map(state).filter(function (item) { return item.checked; }).map(function (item) {
      var entry = { status: item.status };
      entry[key] = item.id;
      return entry;
    });

    saveButton.disabled = true;
    fetch(form.getAttribute('data-endpoint'), {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'X-CSRFToken': window.__adminCsrfToken,
      },
      body: JSON.stringify({ atribuicoes: items }),
    }).then(async function (res) {
      var body = await res.json().catch(function () { return {}; });
      if (!res.ok) {
        var message = 'Erro ao salvar: ' + (body.error || res.status);
        statusNode.textContent = message;
        announce(message, true);
        saveButton.disabled = false;
        return;
      }

      announce('Atribuições salvas com sucesso. Voltando.');
      window.location.href = form.getAttribute('data-return-url');
    }).catch(function () {
      statusNode.textContent = 'Erro de conexão ao salvar. Tente novamente.';
      announce('Erro de conexão ao salvar.', true);
      saveButton.disabled = false;
    });
  });
})();
