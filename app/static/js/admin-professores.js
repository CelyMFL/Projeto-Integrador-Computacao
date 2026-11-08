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
  var summary = document.getElementById('prof-search-summary');
  if (!searchInput) return;

  var searchTimer = null;

  // Busca por nome e e-mail, ignorando acentos e maiúsculas.
  function filterProfessors() {
    var terms = normalize(searchInput.value).split(/\s+/).filter(Boolean);
    var visibleCount = 0;

    document.querySelectorAll('[data-professor-search]').forEach(function (card) {
      var searchable = normalize(card.getAttribute('data-professor-search'));
      var visible = terms.every(function (term) {
        return searchable.indexOf(term) !== -1;
      });
      card.style.display = visible ? '' : 'none';
      if (visible) visibleCount += 1;
    });

    if (noResults) noResults.hidden = visibleCount > 0 || terms.length === 0;
    if (summary) {
      summary.textContent = terms.length
        ? (visibleCount + (visibleCount === 1 ? ' professor encontrado.' : ' professores encontrados.'))
        : 'Digite para filtrar a lista.';
    }
    if (terms.length) {
      announce(visibleCount + (visibleCount === 1 ? ' professor encontrado.' : ' professores encontrados.'));
    }
  }

  searchInput.addEventListener('input', function () {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(filterProfessors, 200);
  });
})();
