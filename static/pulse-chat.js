/* ============================================================
   pulse_ — Chat Logic
   ============================================================ */

(function () {
  'use strict';

  const form = document.getElementById('chat-form');
  const input = document.getElementById('chat-input');
  const chatZone = document.getElementById('chat-zone');
  const chatMessages = document.getElementById('chat-messages');
  const chatBottom = document.getElementById('chat-bottom');
  const headlinesSection = document.getElementById('headlines-section');

  // ── Fetch KPIs on load ──────────────────────────────────────
  async function loadMetrics() {
    try {
      const res = await fetch('/metrics');
      if (!res.ok) return;
      const data = await res.json();

      const qEl = document.getElementById('kpi-queries');
      const lEl = document.getElementById('kpi-latency');
      const eEl = document.getElementById('kpi-errors');

      if (qEl) qEl.textContent = (data.total_requests ?? 0).toLocaleString();
      if (lEl) lEl.textContent = Math.round(data.avg_duration_ms ?? 0).toLocaleString() + 'ms';
      if (eEl) eEl.textContent = ((data.error_rate ?? 0) * 100).toFixed(1) + '%';
    } catch {
      // API offline — leave dashes
    }
  }
  loadMetrics();

  // ── Time formatting ─────────────────────────────────────────
  function timeNow() {
    return new Date().toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
  }

  // ── Create message DOM ──────────────────────────────────────
  function appendMessage({ role, content, meta }) {
    const article = document.createElement('article');
    article.className = 'pulse-message pulse-message--' + role;

    const isAgent = role === 'agent';
    const avatarClass = isAgent ? 'pulse-message-avatar pulse-message-avatar--agent' : 'pulse-message-avatar';
    const avatarContent = isAgent ? 'p<span style="color:var(--pulse-accent)">_</span>' : 'U';
    const labelClass = isAgent ? 't-eyebrow-accent' : 't-eyebrow';
    const label = isAgent ? 'pulse_' : 'You';

    const rendered = isAgent ? marked.parse(content) : escapeHtml(content);

    article.innerHTML = `
      <div class="${avatarClass}">${avatarContent}</div>
      <div class="pulse-message-body">
        <div class="pulse-message-meta">
          <span class="${labelClass}">${label}</span>
          <span class="t-meta">${meta}</span>
        </div>
        <div class="pulse-message-content t-body">${rendered}</div>
      </div>
    `;

    chatMessages.appendChild(article);
    chatBottom.scrollIntoView({ behavior: 'smooth' });
  }

  // ── Typing indicator ───────────────────────────────────────
  function showTyping() {
    const el = document.createElement('article');
    el.className = 'pulse-message pulse-message--agent';
    el.id = 'typing-indicator';
    el.innerHTML = `
      <div class="pulse-message-avatar pulse-message-avatar--agent">p<span style="color:var(--pulse-accent)">_</span></div>
      <div class="pulse-message-body">
        <div class="pulse-message-meta">
          <span class="t-eyebrow-accent">pulse_</span>
          <span class="t-meta">thinking…</span>
        </div>
        <div class="pulse-typing">
          <span class="pulse-typing-dot"></span>
          <span class="pulse-typing-dot"></span>
          <span class="pulse-typing-dot"></span>
        </div>
      </div>
    `;
    chatMessages.appendChild(el);
    chatBottom.scrollIntoView({ behavior: 'smooth' });
  }

  function hideTyping() {
    const el = document.getElementById('typing-indicator');
    if (el) el.remove();
  }

  // ── HTML escape ─────────────────────────────────────────────
  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  // ── Submit handler ──────────────────────────────────────────
  async function submitQuery(query) {
    if (!query.trim()) return;

    // Show chat zone, hide headlines
    chatZone.hidden = false;

    // Add user message
    appendMessage({ role: 'user', content: query, meta: timeNow() + ' · Query' });

    // Typing indicator
    showTyping();
    const t0 = performance.now();

    try {
      const res = await fetch('/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: query }),
      });

      hideTyping();
      const elapsed = ((performance.now() - t0) / 1000).toFixed(1);

      if (!res.ok) {
        appendMessage({
          role: 'agent',
          content: 'Erreur serveur — réessayez.',
          meta: timeNow() + ' · ' + elapsed + 's · error',
        });
        return;
      }

      const data = await res.json();
      appendMessage({
        role: 'agent',
        content: data.reponse,
        meta: timeNow() + ' · ' + elapsed + 's',
      });

      // Refresh KPIs
      loadMetrics();
    } catch {
      hideTyping();
      appendMessage({
        role: 'agent',
        content: 'Impossible de joindre le serveur. Vérifiez que l\'API tourne sur le port 8000.',
        meta: timeNow() + ' · offline',
      });
    }
  }

  // ── Form submit ─────────────────────────────────────────────
  form.addEventListener('submit', function (e) {
    e.preventDefault();
    const query = input.value.trim();
    if (!query) return;
    input.value = '';
    submitQuery(query);
  });

  // ── Headline card clicks ────────────────────────────────────
  document.querySelectorAll('.pulse-headline-card').forEach(function (card) {
    card.addEventListener('click', function () {
      const prompt = card.getAttribute('data-prompt');
      if (prompt) {
        input.value = prompt;
        submitQuery(prompt);
        input.value = '';
      }
    });
  });
})();
