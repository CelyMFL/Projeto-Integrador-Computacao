/**
 * accessibility.js
 * Módulo central de acessibilidade do Sistema de Onboarding Docente.
 * Implementa recursos alinhados às diretrizes WCAG 2.2, com foco em critérios
 * de nível AAA que podem ser resolvidos via JavaScript/CSS em tempo de execução:
 *
 *  - 1.4.6  Contraste (Aprimorado)      -> alternância de alto contraste
 *  - 1.4.8  Apresentação Visual         -> controle de fonte, espaçamento, largura
 *  - 1.4.9  Imagens de texto            -> N/A (não há imagens de texto no sistema)
 *  - 2.1.3  Teclado (sem exceções)      -> toda a toolbar e painéis são 100% navegáveis por teclado
 *  - 2.2.3  Sem tempo limite            -> nenhum recurso de temporização foi introduzido
 *  - 2.3.3  Animação por interação      -> alternância "reduzir animações"
 *  - 2.4.1  Ignorar blocos              -> link "Pular para o conteúdo principal"
 *  - 2.4.8  Localização                 -> aria-current="page" no item de navegação ativo
 *  - 2.4.9  Propósito do link (link)    -> rótulos acessíveis (aria-label) contextuais
 *  - 2.4.13 Aparência do foco           -> foco visível reforçado
 *  - 2.5.5  Tamanho do alvo (Aprim.)    -> alvos de toque/clique com no mínimo 44x44px
 *  - 3.3.6  Prevenção de erros (todos)  -> confirmação antes do envio de formulários críticos
 *  - 4.1.3  Mensagens de status         -> região viva (aria-live) + toast visível
 *
 * Este arquivo é carregado com "defer" em todas as páginas do sistema.
 */
(function () {
  'use strict';

  var STORAGE_KEY = 'a11yPreferences';

  var defaults = {
    fontScale: 1,          // 1 | 1.25 | 1.5 | 1.75 | 2  (até 200%, conforme 1.4.4)
    contrast: 'default',   // 'default' | 'high'
    spacing: 'default',    // 'default' | 'wide'
    underlineLinks: false,
    dyslexiaFont: false,
    reduceMotion: false
  };

  var SCALES = [1, 1.25, 1.5, 1.75, 2];

  function loadPrefs() {
    try {
      var raw = window.localStorage.getItem(STORAGE_KEY);
      return raw ? Object.assign({}, defaults, JSON.parse(raw)) : Object.assign({}, defaults);
    } catch (e) {
      return Object.assign({}, defaults);
    }
  }

  function savePrefs(p) {
    try { window.localStorage.setItem(STORAGE_KEY, JSON.stringify(p)); } catch (e) { /* modo privado: ignora */ }
  }

  var prefs = loadPrefs();

  function applyPrefs() {
    var root = document.documentElement;
    root.style.setProperty('--a11y-font-scale', String(prefs.fontScale));
    root.classList.toggle('a11y-contrast-high', prefs.contrast === 'high');
    root.classList.toggle('a11y-spacing-wide', prefs.spacing === 'wide');
    root.classList.toggle('a11y-underline-links', !!prefs.underlineLinks);
    root.classList.toggle('a11y-dyslexia-font', !!prefs.dyslexiaFont);
    root.classList.toggle('a11y-reduce-motion', !!prefs.reduceMotion);
  }

  /* ---------- Região viva + toast acessível (4.1.3 Mensagens de status) ---------- */

  function getLiveRegion() {
    var region = document.getElementById('a11y-live-region');
    if (!region) {
      region = document.createElement('div');
      region.id = 'a11y-live-region';
      region.setAttribute('aria-live', 'polite');
      region.setAttribute('aria-atomic', 'true');
      region.className = 'a11y-visually-hidden';
      document.body.appendChild(region);
    }
    return region;
  }

  var toastTimer = null;
  function showToast(message, isError) {
    var toast = document.getElementById('a11y-toast');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'a11y-toast';
      toast.setAttribute('role', 'alert');
      toast.tabIndex = -1;
      document.body.appendChild(toast);
    }
    toast.className = 'a11y-toast a11y-toast-visible' + (isError ? ' a11y-toast-error' : ' a11y-toast-success');
    toast.textContent = message;
    window.clearTimeout(toastTimer);
    toastTimer = window.setTimeout(function () {
      toast.classList.remove('a11y-toast-visible');
    }, 7000);
  }

  /**
   * Anuncia uma mensagem para leitores de tela (aria-live) e a exibe visualmente
   * em um toast. Deve ser usada no lugar de alert() para não interromper o fluxo
   * de foco de forma abrupta e para garantir que a mensagem seja lida por leitores
   * de tela mesmo quando o usuário não está com foco próximo ao elemento alterado.
   */
  function announce(message, assertive) {
    var region = getLiveRegion();
    region.setAttribute('aria-live', assertive ? 'assertive' : 'polite');
    region.textContent = '';
    window.setTimeout(function () { region.textContent = message; }, 50);
    showToast(message, !!assertive);
  }

  /**
   * Confirmação acessível para prevenção de erros (3.3.6). Usa o diálogo nativo
   * do navegador, que já é totalmente acessível por teclado e leitor de tela,
   * gerencia foco automaticamente e não exige JavaScript adicional para ser operado.
   */
  function confirmAction(message) {
    return window.confirm(message);
  }

  window.A11y = { announce: announce, confirmAction: confirmAction };

  /* ---------- Link "Pular para o conteúdo principal" (2.4.1) ---------- */

  function ensureSkipLink() {
    if (document.querySelector('.a11y-skip-link')) return;
    var target = document.querySelector('main');
    if (!target) return;
    if (!target.id) target.id = 'main-content';
    if (!target.hasAttribute('tabindex')) target.setAttribute('tabindex', '-1');

    var link = document.createElement('a');
    link.href = '#' + target.id;
    link.className = 'a11y-skip-link';
    link.textContent = 'Pular para o conteúdo principal';
    document.body.insertBefore(link, document.body.firstChild);
  }

  /* ---------- Localização / item de navegação atual (2.4.8) ---------- */

  function markCurrentPage() {
    document.querySelectorAll('nav a.active').forEach(function (a) {
      if (!a.hasAttribute('aria-current')) a.setAttribute('aria-current', 'page');
    });
  }

  /* ---------- Nomes acessíveis para landmarks repetidas ---------- */

  function labelLandmarks() {
    document.querySelectorAll('nav.topnav').forEach(function (nav) {
      if (!nav.hasAttribute('aria-label')) nav.setAttribute('aria-label', 'Navegação principal');
    });
    document.querySelectorAll('nav').forEach(function (nav) {
      if (!nav.hasAttribute('aria-label') && !nav.hasAttribute('aria-labelledby')) {
        nav.setAttribute('aria-label', 'Navegação');
      }
    });
  }

  /* ---------- Sincroniza aria-expanded em botões que abrem/fecham painéis ---------- */

  function syncDisclosureState() {
    document.querySelectorAll('[aria-controls]').forEach(function (trigger) {
      var panel = document.getElementById(trigger.getAttribute('aria-controls'));
      if (!panel) return;
      var isOpen = panel.style.display !== 'none' && !panel.hidden;
      trigger.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    });
  }

  function watchDisclosureButtons() {
    document.body.addEventListener('click', function (evt) {
      var btn = evt.target.closest('button');
      if (!btn) return;
      // Dá tempo para o onclick original (inline) alterar o display do painel.
      window.setTimeout(syncDisclosureState, 0);
    });
  }

  /* ---------- Indicação de foco reforçada + detecção de uso de teclado ---------- */

  function enhanceFocus() {
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Tab') document.documentElement.classList.add('a11y-kbd-user');
    });
    document.addEventListener('mousedown', function () {
      document.documentElement.classList.remove('a11y-kbd-user');
    });
  }

  /* ---------- Prevenção de erros (3.3.6) para formulários marcados ---------- */

  function watchConfirmForms() {
    document.querySelectorAll('form[data-a11y-confirm]').forEach(function (form) {
      form.addEventListener('submit', function (evt) {
        if (form.dataset.a11yConfirmed === 'true') return; // já confirmado nesta submissão
        var msg = form.getAttribute('data-a11y-confirm') || 'Confirma o envio deste formulário?';
        if (!confirmAction(msg)) {
          evt.preventDefault();
        } else {
          form.dataset.a11yConfirmed = 'true';
        }
      });
    });
  }

  /* ---------- Toolbar de acessibilidade (100% operável por teclado) ---------- */

  function el(tag, attrs, html) {
    var e = document.createElement(tag);
    if (attrs) {
      Object.keys(attrs).forEach(function (k) { e.setAttribute(k, attrs[k]); });
    }
    if (html !== undefined) e.innerHTML = html;
    return e;
  }

  function buildToolbar() {
    if (document.getElementById('a11y-toolbar')) return;

    var toolbar = el('div', { id: 'a11y-toolbar' });

    var toggleBtn = el('button', {
      type: 'button',
      id: 'a11y-toolbar-toggle',
      'aria-expanded': 'false',
      'aria-controls': 'a11y-toolbar-panel'
    }, '<span aria-hidden="true">&#9881;&#65039;</span> Acessibilidade');

    var panel = el('div', {
      id: 'a11y-toolbar-panel',
      role: 'region',
      'aria-label': 'Opções de acessibilidade'
    });
    panel.hidden = true;

    panel.innerHTML =
      '<h2 class="a11y-toolbar-title">Preferências de acessibilidade</h2>' +
      '<div class="a11y-control-group">' +
        '<span class="a11y-control-label" id="a11y-font-label">Tamanho do texto</span>' +
        '<div class="a11y-btn-row" role="group" aria-labelledby="a11y-font-label">' +
          '<button type="button" id="a11y-font-dec" aria-label="Diminuir tamanho do texto">A&#8595;</button>' +
          '<button type="button" id="a11y-font-reset" aria-label="Restaurar tamanho padrão do texto">A</button>' +
          '<button type="button" id="a11y-font-inc" aria-label="Aumentar tamanho do texto">A&#8593;</button>' +
        '</div>' +
      '</div>' +
      toggleRow('a11y-toggle-contrast', 'Alto contraste (7:1)') +
      toggleRow('a11y-toggle-spacing', 'Espaçamento ampliado de texto') +
      toggleRow('a11y-toggle-underline', 'Sublinhar todos os links') +
      toggleRow('a11y-toggle-dyslexia', 'Fonte facilitada de leitura') +
      toggleRow('a11y-toggle-motion', 'Reduzir animações') +
      '<button type="button" id="a11y-reset" class="a11y-reset-btn">Restaurar padrões</button>';

    toolbar.appendChild(toggleBtn);
    toolbar.appendChild(panel);
    document.body.appendChild(toolbar);

    toggleBtn.addEventListener('click', function () {
      var willOpen = panel.hidden;
      panel.hidden = !willOpen;
      toggleBtn.setAttribute('aria-expanded', String(willOpen));
      if (willOpen) {
        var first = panel.querySelector('button, input');
        if (first) first.focus();
      }
    });

    panel.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') {
        panel.hidden = true;
        toggleBtn.setAttribute('aria-expanded', 'false');
        toggleBtn.focus();
      }
    });

    wireToolbar(panel);
  }

  function toggleRow(id, label) {
    return '<label class="a11y-toggle-row" for="' + id + '"><input type="checkbox" id="' + id + '"> <span>' + label + '</span></label>';
  }

  function wireToolbar(panel) {
    var fontDec = panel.querySelector('#a11y-font-dec');
    var fontInc = panel.querySelector('#a11y-font-inc');
    var fontReset = panel.querySelector('#a11y-font-reset');

    function setScale(newScale) {
      prefs.fontScale = newScale;
      applyPrefs(); savePrefs(prefs);
      announce('Tamanho do texto ajustado para ' + Math.round(newScale * 100) + '%.');
    }
    fontInc.addEventListener('click', function () {
      var idx = SCALES.indexOf(prefs.fontScale);
      idx = Math.min((idx === -1 ? 0 : idx) + 1, SCALES.length - 1);
      setScale(SCALES[idx]);
    });
    fontDec.addEventListener('click', function () {
      var idx = SCALES.indexOf(prefs.fontScale);
      idx = Math.max((idx === -1 ? 0 : idx) - 1, 0);
      setScale(SCALES[idx]);
    });
    fontReset.addEventListener('click', function () { setScale(1); });

    bindMappedToggle(panel, '#a11y-toggle-contrast', 'contrast', 'high', 'default',
      'Alto contraste ativado.', 'Alto contraste desativado.');
    bindMappedToggle(panel, '#a11y-toggle-spacing', 'spacing', 'wide', 'default',
      'Espaçamento ampliado ativado.', 'Espaçamento ampliado desativado.');
    bindBoolToggle(panel, '#a11y-toggle-underline', 'underlineLinks',
      'Links sublinhados ativados.', 'Links sublinhados desativados.');
    bindBoolToggle(panel, '#a11y-toggle-dyslexia', 'dyslexiaFont',
      'Fonte facilitada de leitura ativada.', 'Fonte facilitada de leitura desativada.');
    bindBoolToggle(panel, '#a11y-toggle-motion', 'reduceMotion',
      'Redução de animações ativada.', 'Redução de animações desativada.');

    // Reflete o estado salvo nos controles ao abrir a toolbar.
    setChecked(panel, '#a11y-toggle-contrast', prefs.contrast === 'high');
    setChecked(panel, '#a11y-toggle-spacing', prefs.spacing === 'wide');
    setChecked(panel, '#a11y-toggle-underline', !!prefs.underlineLinks);
    setChecked(panel, '#a11y-toggle-dyslexia', !!prefs.dyslexiaFont);
    setChecked(panel, '#a11y-toggle-motion', !!prefs.reduceMotion);

    panel.querySelector('#a11y-reset').addEventListener('click', function () {
      prefs = Object.assign({}, defaults);
      applyPrefs(); savePrefs(prefs);
      panel.querySelectorAll('input[type=checkbox]').forEach(function (cb) { cb.checked = false; });
      announce('Preferências de acessibilidade restauradas para o padrão.');
    });
  }

  function setChecked(panel, selector, value) {
    var cb = panel.querySelector(selector);
    if (cb) cb.checked = value;
  }

  function bindMappedToggle(panel, selector, key, onVal, offVal, onMsg, offMsg) {
    var cb = panel.querySelector(selector);
    cb.addEventListener('change', function () {
      prefs[key] = cb.checked ? onVal : offVal;
      applyPrefs(); savePrefs(prefs);
      announce(cb.checked ? onMsg : offMsg);
    });
  }

  function bindBoolToggle(panel, selector, key, onMsg, offMsg) {
    var cb = panel.querySelector(selector);
    cb.addEventListener('change', function () {
      prefs[key] = cb.checked;
      applyPrefs(); savePrefs(prefs);
      announce(cb.checked ? onMsg : offMsg);
    });
  }

  /* ---------- Inicialização ---------- */

  function init() {
    ensureSkipLink();
    markCurrentPage();
    labelLandmarks();
    enhanceFocus();
    watchDisclosureButtons();
    watchConfirmForms();
    buildToolbar();
    getLiveRegion();
    applyPrefs();
    syncDisclosureState();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
