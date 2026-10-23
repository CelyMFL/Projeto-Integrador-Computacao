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

  var selector = document.getElementById('trilha-selector');
  var tasksContainer = document.getElementById('tasks-container');
  var openButtons = document.querySelectorAll('[data-open-add-task]');
  var addTaskForm = document.getElementById('add-task-form');
  var submitAddTask = document.getElementById('submit-add-task');
  var cancelAddTask = document.getElementById('cancel-add-task');

  if (selector) {
    selector.addEventListener('change', function () {
      var selectedId = selector.value;
      document.querySelectorAll('.trilha-tasks').forEach(function (node) {
        node.classList.remove('active');
      });
      if (!selectedId) return;
      var target = document.getElementById('trilha-' + selectedId);
      if (target) {
        target.classList.add('active');
        announce('Exibindo tarefas da trilha selecionada.');
      }
    });
  }

  function toggleAddTaskForm() {
    if (!addTaskForm) return;
    var isHidden = addTaskForm.style.display === 'none' || !addTaskForm.style.display;
    addTaskForm.style.display = isHidden ? 'block' : 'none';
    openButtons.forEach(function (btn) {
      btn.setAttribute('aria-expanded', isHidden ? 'true' : 'false');
    });
    if (isHidden) {
      var first = document.getElementById('task-descricao');
      if (first) first.focus();
    }
  }

  openButtons.forEach(function (button) {
    button.addEventListener('click', toggleAddTaskForm);
  });

  if (cancelAddTask) {
    cancelAddTask.addEventListener('click', toggleAddTaskForm);
  }

  function appendTaskToSelectedTrilha(task, trilhaId) {
    var panel = document.getElementById('trilha-' + trilhaId);
    if (!panel) return;

    var list = panel.querySelector('ul.task-preview-list');
    if (!list) return;

    var empty = list.querySelector('.muted');
    if (empty) empty.remove();

    var li = document.createElement('li');
    li.innerHTML =
      '<div class="task-dot done" aria-hidden="true"></div>' +
      '<div style="flex: 1;"><strong>' + task.descricao + '</strong><p>Ordem: ' + (task.ordem || '-') + '</p></div>' +
      '<div class="actions"><button class="button ghost" disabled aria-label="Edicao em breve">Editar</button></div>';

    list.appendChild(li);
  }

  if (submitAddTask) {
    submitAddTask.addEventListener('click', function () {
      if (!selector || !selector.value) {
        announce('Selecione uma trilha primeiro.', true);
        return;
      }

      var descricao = document.getElementById('task-descricao').value.trim();
      if (!descricao) {
        announce('Informe a descricao da tarefa.', true);
        return;
      }

      if (!confirmAction('Confirma a criacao desta tarefa?')) return;

      var payload = {
        descricao: descricao,
      };

      var ordem = document.getElementById('task-ordem').value;
      var material = document.getElementById('task-material').value.trim();
      var link = document.getElementById('task-link').value.trim();
      var documento = document.getElementById('task-documento').value.trim();

      if (ordem) payload.ordem = ordem;
      if (material) payload.material_apoio = material;
      if (link) payload.link_apoio = link;
      if (documento) payload.documento_apoio = documento;

      fetch('/trilhas/' + selector.value + '/tasks', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': window.__adminCsrfToken,
        },
        body: JSON.stringify(payload),
      }).then(async function (res) {
        var body = await res.json().catch(function () { return {}; });
        if (!res.ok) {
          announce('Erro ao criar tarefa: ' + (body.error || res.status), true);
          return;
        }

        appendTaskToSelectedTrilha(body, selector.value);
        announce('Tarefa criada com sucesso.');
        document.getElementById('task-descricao').value = '';
        document.getElementById('task-ordem').value = '';
        document.getElementById('task-material').value = '';
        document.getElementById('task-link').value = '';
        document.getElementById('task-documento').value = '';
      });
    });
  }
})();
