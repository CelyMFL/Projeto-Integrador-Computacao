(function () {
  'use strict';

  function announce(msg, isError) {
    if (window.A11y && window.A11y.announce) {
      window.A11y.announce(msg, !!isError);
    }
  }

  var form = document.getElementById('edit-form');
  if (!form) return;

  var steps = form.querySelectorAll('[data-step]');
  var pills = document.querySelectorAll('[data-step-pill]');
  var reviewList = document.getElementById('review-list');
  var statusNode = document.getElementById('form-status');
  var fields = form.querySelectorAll('[data-review-label]');

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

  function displayValue(field) {
    if (field.type === 'checkbox') return field.checked ? 'Sim' : 'Não';
    if (field.hasAttribute('data-review-secret')) return field.value ? 'Será alterada' : 'Mantida';
    return field.value.trim() || '—';
  }

  function buildReview() {
    reviewList.textContent = '';
    fields.forEach(function (field) {
      var term = document.createElement('dt');
      term.textContent = field.getAttribute('data-review-label');
      var detail = document.createElement('dd');
      detail.textContent = displayValue(field);
      reviewList.appendChild(term);
      reviewList.appendChild(detail);
    });
  }

  function buildPayload() {
    var payload = {};
    fields.forEach(function (field) {
      if (field.type === 'checkbox') {
        payload[field.name] = field.checked;
      } else if (field.hasAttribute('data-review-secret')) {
        if (field.value) payload[field.name] = field.value;
      } else if (field.getAttribute('data-type') === 'int') {
        if (field.value) payload[field.name] = parseInt(field.value, 10);
      } else {
        payload[field.name] = field.value.trim();
      }
    });
    return payload;
  }

  form.querySelector('[data-next]').addEventListener('click', function () {
    if (!form.reportValidity()) {
      announce('Corrija os campos destacados antes de continuar.', true);
      return;
    }
    buildReview();
    showStep(2);
  });

  form.querySelector('[data-back]').addEventListener('click', function () {
    showStep(1);
  });

  form.addEventListener('submit', function (event) {
    event.preventDefault();
    statusNode.textContent = '';

    fetch(form.getAttribute('data-endpoint'), {
      method: form.getAttribute('data-method'),
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'X-CSRFToken': window.__adminCsrfToken,
      },
      body: JSON.stringify(buildPayload()),
    }).then(async function (res) {
      var body = await res.json().catch(function () { return {}; });
      if (!res.ok) {
        var message = 'Erro ao salvar: ' + (body.error || res.status);
        statusNode.textContent = message;
        announce(message, true);
        return;
      }

      announce('Alterações salvas com sucesso. Voltando para a lista.');
      window.location.href = form.getAttribute('data-return-url');
    }).catch(function () {
      statusNode.textContent = 'Erro de conexão ao salvar. Tente novamente.';
      announce('Erro de conexão ao salvar.', true);
    });
  });
})();
