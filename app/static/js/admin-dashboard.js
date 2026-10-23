(function () {
  'use strict';

  var dataNode = document.getElementById('analytics-data');
  if (!dataNode) return;

  var raw = dataNode.textContent || '{}';
  var analytics = {};
  try {
    analytics = JSON.parse(raw);
  } catch (error) {
    window.A11y && window.A11y.announce('Falha ao ler dados analiticos do dashboard.', true);
    return;
  }

  function createChart(targetId, config) {
    var canvas = document.getElementById(targetId);
    if (!canvas || !window.Chart) return;
    return new window.Chart(canvas, config);
  }

  createChart('statusChart', {
    type: 'doughnut',
    data: {
      labels: analytics.status_distribution.labels,
      datasets: [{
        data: analytics.status_distribution.values,
        backgroundColor: ['#0f766e', '#f59e0b', '#94a3b8'],
        borderWidth: 1,
      }],
    },
    options: {
      plugins: { legend: { position: 'bottom' } },
      maintainAspectRatio: false,
    },
  });

  createChart('tipoChart', {
    type: 'bar',
    data: {
      labels: analytics.trilhas_por_tipo.labels,
      datasets: [{
        label: 'Quantidade',
        data: analytics.trilhas_por_tipo.values,
        backgroundColor: '#0f766e',
      }],
    },
    options: {
      indexAxis: 'y',
      plugins: { legend: { display: false } },
      maintainAspectRatio: false,
      scales: { x: { beginAtZero: true } },
    },
  });

  createChart('feedbackChart', {
    type: 'line',
    data: {
      labels: analytics.feedback_timeline.labels,
      datasets: [{
        label: 'Feedbacks por mes',
        data: analytics.feedback_timeline.values,
        borderColor: '#b45309',
        backgroundColor: 'rgba(180, 83, 9, 0.15)',
        fill: true,
        tension: 0.2,
      }],
    },
    options: {
      plugins: { legend: { display: true } },
      maintainAspectRatio: false,
      scales: { y: { beginAtZero: true } },
    },
  });

  createChart('completionChart', {
    type: 'bar',
    data: {
      labels: analytics.completion_by_trilha.labels,
      datasets: [{
        label: 'Conclusao media (%)',
        data: analytics.completion_by_trilha.values,
        backgroundColor: '#0f766e',
      }],
    },
    options: {
      plugins: { legend: { display: false } },
      maintainAspectRatio: false,
      scales: { y: { beginAtZero: true, max: 100 } },
    },
  });

  var insightList = document.getElementById('insight-list');
  if (insightList && Array.isArray(analytics.insights)) {
    insightList.innerHTML = '';
    analytics.insights.forEach(function (insight) {
      var li = document.createElement('li');
      li.textContent = insight;
      insightList.appendChild(li);
    });
  }
})();
