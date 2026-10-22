/*
 * Integração com a YouTube IFrame Player API.
 *
 * Fluxo:
 *  1. Carrega o script oficial do YouTube (https://www.youtube.com/iframe_api).
 *  2. Quando o script termina de carregar, o YouTube chama a função
 *     window.onYouTubeIframeAPIReady (nome fixo, definido pela API).
 *  3. Nessa função "conectamos" o iframe que já está na página a um objeto YT.Player.
 *  4. O player avisa a gente toda vez que o estado muda (tocando, pausado, terminou...).
 *  5. Quando o estado for "terminou" (ENDED), pedimos ao nosso servidor Flask para
 *     marcar a tarefa como concluída (POST /tasks/<id>/complete).
 */
(function () {
  'use strict';

  var wrapper = document.getElementById('video-wrapper');
  var iframe = document.getElementById('video-player');
  if (!wrapper || !iframe) { return; }  // página sem vídeo: não faz nada

  var completeUrl = wrapper.dataset.completeUrl;
  var jaConcluida = wrapper.dataset.concluida === 'true';
  var enviado = false;  // evita enviar o pedido duas vezes

  var mensagem = document.getElementById('video-status');
  var pill = document.getElementById('task-status-pill');
  var form = document.getElementById('task-status-form');

  function mostrarMensagem(texto) {
    if (mensagem) { mensagem.textContent = texto; }
  }

  // Atualiza a página sem recarregar, para refletir que a tarefa foi concluída.
  function atualizarInterface() {
    if (pill) {
      pill.textContent = 'Concluída';
      pill.classList.remove('warning');
      pill.classList.add('success');
    }
    if (form) {
      var botao = form.querySelector('button');
      form.action = form.dataset.incompleteUrl || form.action;
      if (botao) {
        botao.textContent = 'Marcar como pendente';
        botao.classList.add('danger');
        botao.setAttribute('aria-label', 'Marcar tarefa como pendente');
      }
    }
  }

  function marcarComoConcluida() {
    if (jaConcluida || enviado || !completeUrl) { return; }
    enviado = true;

    fetch(completeUrl, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'   // faz o Flask responder em JSON
      },
      body: JSON.stringify({})
    })
      .then(function (resposta) {
        if (!resposta.ok) { throw new Error('HTTP ' + resposta.status); }
        return resposta.json();
      })
      .then(function (dados) {
        if (dados.concluido) {
          jaConcluida = true;
          atualizarInterface();
          mostrarMensagem('Você terminou o vídeo e a tarefa foi marcada como concluída.');
        }
      })
      .catch(function () {
        enviado = false;  // permite tentar de novo se o vídeo for assistido outra vez
        mostrarMensagem('Não foi possível registrar a conclusão. Use o botão "Marcar como concluída".');
      });
  }

  function aoMudarEstado(evento) {
    // YT.PlayerState.ENDED vale 0
    if (evento.data === YT.PlayerState.ENDED) {
      marcarComoConcluida();
    }
  }

  // O YouTube procura essa função pelo nome exato quando o script dele carrega.
  window.onYouTubeIframeAPIReady = function () {
    new YT.Player(iframe, { events: { onStateChange: aoMudarEstado } });
  };

  var script = document.createElement('script');
  script.src = 'https://www.youtube.com/iframe_api';
  document.head.appendChild(script);
})();
