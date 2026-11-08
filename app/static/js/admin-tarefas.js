(function () {
  'use strict';

  function announce(msg, isError) {
    if (window.A11y && window.A11y.announce) {
      window.A11y.announce(msg, !!isError);
    }
  }

  var selector = document.getElementById('trilha-selector');
  if (!selector) return;

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
})();
