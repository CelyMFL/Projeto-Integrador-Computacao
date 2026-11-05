(function () {
  'use strict';

  function announce(msg, isError) {
    if (window.A11y && window.A11y.announce) {
      window.A11y.announce(msg, !!isError);
    }
  }

  function normalize(text) {
    return (text || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim();
  }

  var searchInput = document.getElementById('prof-search');
  var noResults = document.getElementById('prof-no-results');
  if (!searchInput) return;

  var searchTimer = null;

  // Busca por trecho do nome (ignora acentos e maiúsculas e exige todas as palavras digitadas).
  // Um termo com "@" é procurado no e-mail.
  function filterProfessors() {
    var terms = normalize(searchInput.value).split(/\s+/).filter(Boolean);
    var visibleCount = 0;

    document.querySelectorAll('[data-professor-name]').forEach(function (card) {
      var name = normalize(card.getAttribute('data-professor-name'));
      var email = normalize(card.getAttribute('data-professor-email'));
      var visible = terms.every(function (term) {
        return (term.indexOf('@') !== -1 ? email : name).indexOf(term) !== -1;
      });
      card.style.display = visible ? '' : 'none';
      if (visible) visibleCount += 1;
    });

    if (noResults) noResults.hidden = visibleCount > 0 || terms.length === 0;
    if (terms.length) {
      announce(visibleCount + (visibleCount === 1 ? ' professor encontrado.' : ' professores encontrados.'));
    }
  }

  searchInput.addEventListener('input', function () {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(filterProfessors, 200);
  });
})();
