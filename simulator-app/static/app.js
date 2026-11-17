// static/app.js - Logique asynchrone pour W3.CSS

async function loadStats() {
  try {
    const res = await fetch('/api/stats');
    if (!res.ok) return;
    const data = await res.json();

    // Statut ES
    const elEs = document.getElementById('stat-es-status');
    elEs.innerText = data.es_status.toUpperCase();
    if (data.es_status === 'green') elEs.className = 'w3-xlarge w3-text-green w3-bold';
    else if (data.es_status === 'yellow') elEs.className = 'w3-xlarge w3-text-yellow w3-bold';
    else elEs.className = 'w3-xlarge w3-text-red w3-bold';

    // Documents indexés
    document.getElementById('stat-docs-count').innerText = Number(data.indexed_docs).toLocaleString();

    // ML Job Status
    document.getElementById('stat-ml-status').innerText = data.ml_status.toUpperCase();
    document.getElementById('stat-ml-id').innerText = data.ml_job_id;

    // Mise à jour du flux d'événements
    renderLiveEvents(data.live_events);

  } catch (err) {
    console.error("Erreur stats:", err);
  }
}

async function loadAlerts() {
  try {
    const res = await fetch('/api/alerts');
    if (!res.ok) return;
    const data = await res.json();

    document.getElementById('stat-alerts-count').innerText = data.count;

    const tbody = document.getElementById('alerts-table-body');
    if (!data.alerts || data.alerts.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" class="w3-center w3-text-grey w3-padding-16">Aucune anomalie détectée pour le moment.</td></tr>`;
      return;
    }

    let rowsHtml = '';
    data.alerts.forEach(a => {
      let tagClass = 'w3-tag w3-round w3-small ';
      if (a.severity === 'critical') tagClass += 'w3-red';
      else if (a.severity === 'major') tagClass += 'w3-amber';
      else if (a.severity === 'moderate') tagClass += 'w3-yellow';
      else tagClass += 'w3-dark-grey';

      const infs = a.influencers.map(i => `<span class="w3-tag w3-round w3-tiny w3-dark-grey" style="margin:2px;">${i}</span>`).join(' ');

      rowsHtml += `
        <tr>
          <td><code>${a.timestamp}</code></td>
          <td><span class="${tagClass}">Score ${a.score} (${a.severity.toUpperCase()})</span></td>
          <td><code>${a.detector}</code></td>
          <td class="w3-text-red"><b>${a.actual} requêtes</b></td>
          <td class="w3-text-grey">${a.typical} requêtes</td>
          <td>${infs || '-'}</td>
        </tr>
      `;
    });
    tbody.innerHTML = rowsHtml;

  } catch (err) {
    console.error("Erreur alerts:", err);
  }
}

function renderLiveEvents(events) {
  const container = document.getElementById('events-stream');
  if (!events || events.length === 0) return;

  container.innerHTML = events.map(evt => {
    let evtClass = 'event-normal';
    let tagColor = 'w3-green';
    if (evt.type.includes('Nmap') || evt.type.includes('Scan')) { evtClass = 'event-nmap'; tagColor = 'w3-red'; }
    else if (evt.type.includes('Brute')) { evtClass = 'event-brute'; tagColor = 'w3-amber'; }
    else if (evt.type.includes('SQL')) { evtClass = 'event-sqli'; tagColor = 'w3-purple'; }
    else if (evt.type.includes('XSS')) { evtClass = 'event-xss'; tagColor = 'w3-cyan'; }

    return `
      <div class="event-card ${evtClass}">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <span class="w3-tag ${tagColor} w3-round w3-tiny"><b>${evt.type}</b></span>
          <span class="w3-text-grey">${evt.timestamp}</span>
        </div>
        <div style="margin: 4px 0; color:#c9d1d9;">${evt.details}</div>
        <div style="display:flex; justify-content:space-between; color:#8b949e; font-size:11px;">
          <span>IP Source : <b>${evt.ip}</b></span>
          <span><b>${evt.status}</b></span>
        </div>
      </div>
    `;
  }).join('');
}

async function triggerAction(endpoint) {
  const intensity = parseInt(document.getElementById('attack-intensity').value) || 60;
  const indicator = document.getElementById('live-indicator');
  indicator.innerText = "● Injection en cours...";
  indicator.className = "w3-bar-item w3-right w3-tag w3-amber w3-round w3-tiny";

  try {
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ intensity: intensity })
    });
    await res.json();

    // Rechargement immédiat
    await loadStats();
    await loadAlerts();
  } catch (err) {
    alert("Erreur lors de l'injection: " + err);
  } finally {
    setTimeout(() => {
      indicator.innerText = "● Prêt";
      indicator.className = "w3-bar-item w3-right w3-tag w3-dark-grey w3-round w3-tiny";
    }, 1200);
  }
}

// Polling régulier toutes les 3 secondes
setInterval(() => {
  loadStats();
  loadAlerts();
}, 3000);

window.addEventListener('DOMContentLoaded', () => {
  loadStats();
  loadAlerts();
});
