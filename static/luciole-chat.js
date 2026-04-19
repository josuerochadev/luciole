/* ============================================================
   luciole_ — Chat Logic + Conversation History
   ============================================================ */

(function () {
  'use strict';

  const form = document.getElementById('chat-form');
  const input = document.getElementById('chat-input');
  const formSticky = document.getElementById('chat-form-sticky');
  const inputSticky = document.getElementById('chat-input-sticky');
  const chatZone = document.getElementById('chat-zone');
  const chatMessages = document.getElementById('chat-messages');
  const chatBottom = document.getElementById('chat-bottom');
  const headlinesSection = document.getElementById('headlines-section');
  const newChatBtn = document.getElementById('new-chat-btn');

  // Sidebar elements
  const sidebar = document.getElementById('sidebar');
  const sidebarList = document.getElementById('sidebar-list');
  const sidebarNewBtn = document.getElementById('sidebar-new-btn');
  const sidebarToggle = document.getElementById('sidebar-toggle');
  const sidebarOverlay = document.getElementById('sidebar-overlay');

  // State
  let currentConversationId = null;

  // Show the sidebar toggle (hidden by default in base.html, only shown on chat page)
  if (sidebarToggle) sidebarToggle.style.display = '';

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

  function relativeDate(isoString) {
    if (!isoString) return '';
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now - date;
    const diffMin = Math.floor(diffMs / 60000);
    const diffH = Math.floor(diffMs / 3600000);
    const diffD = Math.floor(diffMs / 86400000);

    if (diffMin < 1) return "à l'instant";
    if (diffMin < 60) return diffMin + ' min';
    if (diffH < 24) return diffH + 'h';
    if (diffD < 7) return diffD + 'j';
    return date.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' });
  }

  // ── Sidebar toggle ────────────────────────────────────────
  function openSidebar() {
    sidebar.classList.add('open');
    sidebarOverlay.classList.add('visible');
    document.body.classList.add('sidebar-open');
  }

  function closeSidebar() {
    sidebar.classList.remove('open');
    sidebarOverlay.classList.remove('visible');
    document.body.classList.remove('sidebar-open');
  }

  function toggleSidebar() {
    if (sidebar.classList.contains('open')) {
      closeSidebar();
    } else {
      openSidebar();
    }
  }

  sidebarToggle.addEventListener('click', toggleSidebar);
  sidebarOverlay.addEventListener('click', closeSidebar);

  // ── Sidebar — Load conversations ──────────────────────────
  async function loadConversations() {
    try {
      const res = await fetch('/conversations');
      if (res.status === 401) { window.location.href = '/login'; return; }
      if (!res.ok) return;
      const conversations = await res.json();
      renderSidebarList(conversations);
    } catch {
      // silent
    }
  }

  function renderSidebarList(conversations) {
    if (!conversations.length) {
      sidebarList.innerHTML = '<div class="luciole-sidebar-empty">Aucune conversation</div>';
      return;
    }

    sidebarList.innerHTML = conversations.map(function (conv) {
      const isActive = conv.id === currentConversationId;
      const title = conv.title || 'Sans titre';
      const date = relativeDate(conv.updated_at);
      return (
        '<button class="luciole-sidebar-item' + (isActive ? ' active' : '') + '" data-id="' + conv.id + '">' +
          '<div class="luciole-sidebar-item-content">' +
            '<span class="luciole-sidebar-item-title">' + escapeHtml(title) + '</span>' +
            '<span class="luciole-sidebar-item-date">' + date + '</span>' +
          '</div>' +
          '<span class="luciole-sidebar-delete" data-id="' + conv.id + '" title="Supprimer">&times;</span>' +
        '</button>'
      );
    }).join('');

    // Click handlers
    sidebarList.querySelectorAll('.luciole-sidebar-item').forEach(function (item) {
      item.addEventListener('click', function (e) {
        // Don't load conversation if clicking delete button
        if (e.target.classList.contains('luciole-sidebar-delete')) return;
        loadConversation(item.getAttribute('data-id'));
        // Close sidebar on mobile
        if (window.innerWidth <= 768) closeSidebar();
      });
    });

    sidebarList.querySelectorAll('.luciole-sidebar-delete').forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        e.stopPropagation();
        deleteConversation(btn.getAttribute('data-id'));
      });
    });
  }

  // ── Load a conversation ───────────────────────────────────
  async function loadConversation(convId) {
    try {
      const res = await fetch('/conversations/' + convId + '/messages');
      if (!res.ok) return;
      const messages = await res.json();

      currentConversationId = convId;
      chatMessages.innerHTML = '';
      enterChatMode();

      messages.forEach(function (msg) {
        const role = msg.role === 'user' ? 'user' : 'agent';
        const time = new Date(msg.created_at).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
        appendMessage({ role: role, content: msg.content, meta: time });
      });

      // Mark active in sidebar
      sidebarList.querySelectorAll('.luciole-sidebar-item').forEach(function (item) {
        item.classList.toggle('active', item.getAttribute('data-id') === convId);
      });
    } catch {
      // silent
    }
  }

  // ── Delete a conversation ─────────────────────────────────
  async function deleteConversation(convId) {
    if (!confirm('Supprimer cette conversation ?')) return;
    try {
      const res = await fetch('/conversations/' + convId, { method: 'DELETE' });
      if (!res.ok) return;

      // If we deleted the active conversation, reset
      if (convId === currentConversationId) {
        resetChat();
      }
      loadConversations();
    } catch {
      // silent
    }
  }

  // ── Activate chat mode ────────────────────────────────────
  function enterChatMode() {
    document.body.classList.add('chat-active');
    chatZone.hidden = false;
    inputSticky.focus();
  }

  // ── Reset chat ─────────────────────────────────────────────
  function resetChat() {
    currentConversationId = null;
    chatMessages.innerHTML = '';
    chatZone.hidden = true;
    document.body.classList.remove('chat-active');
    input.value = '';
    inputSticky.value = '';
    input.focus();

    // Clear active state in sidebar
    sidebarList.querySelectorAll('.luciole-sidebar-item').forEach(function (item) {
      item.classList.remove('active');
    });
  }

  // ── Create message DOM ──────────────────────────────────────
  function appendMessage({ role, content, meta }) {
    const article = document.createElement('article');
    article.className = 'luciole-message luciole-message--' + role;

    const isAgent = role === 'agent';
    const avatarClass = isAgent ? 'luciole-message-avatar luciole-message-avatar--agent' : 'luciole-message-avatar';
    const avatarContent = isAgent ? 'l<span style="color:var(--luciole-accent)">_</span>' : 'U';
    const labelClass = isAgent ? 't-eyebrow-accent' : 't-eyebrow';
    const label = isAgent ? 'luciole_' : 'Vous';

    const rendered = isAgent ? marked.parse(content) : escapeHtml(content);

    article.innerHTML =
      '<div class="' + avatarClass + '" aria-hidden="true">' + avatarContent + '</div>' +
      '<div class="luciole-message-body">' +
        '<div class="luciole-message-meta">' +
          '<span class="' + labelClass + '">' + label + '</span>' +
          '<span class="t-meta">' + meta + '</span>' +
        '</div>' +
        '<div class="luciole-message-content t-body">' + rendered + '</div>' +
      '</div>';

    chatMessages.appendChild(article);
    chatBottom.scrollIntoView({ behavior: 'smooth' });
  }

  // ── Typing indicator ───────────────────────────────────────
  function showTyping() {
    const el = document.createElement('article');
    el.className = 'luciole-message luciole-message--agent';
    el.id = 'typing-indicator';
    el.setAttribute('aria-label', 'luciole_ réfléchit');
    el.innerHTML =
      '<div class="luciole-message-avatar luciole-message-avatar--agent" aria-hidden="true">l<span style="color:var(--luciole-accent)">_</span></div>' +
      '<div class="luciole-message-body">' +
        '<div class="luciole-message-meta">' +
          '<span class="t-eyebrow-accent">luciole_</span>' +
          '<span class="t-meta">réflexion…</span>' +
        '</div>' +
        '<div class="luciole-typing" aria-hidden="true">' +
          '<span class="luciole-typing-dot"></span>' +
          '<span class="luciole-typing-dot"></span>' +
          '<span class="luciole-typing-dot"></span>' +
        '</div>' +
      '</div>';
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

    // Enter chat mode (collapse hero, show sticky input)
    enterChatMode();

    // Add user message
    appendMessage({ role: 'user', content: query, meta: timeNow() + ' · Requête' });

    // Typing indicator
    showTyping();
    const t0 = performance.now();

    try {
      const body = { question: query };
      if (currentConversationId) {
        body.conversation_id = currentConversationId;
      }

      const res = await fetch('/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      hideTyping();
      const elapsed = ((performance.now() - t0) / 1000).toFixed(1);

      if (res.status === 401) {
        window.location.href = '/login';
        return;
      }

      if (!res.ok) {
        appendMessage({
          role: 'agent',
          content: 'Erreur serveur — réessayez.',
          meta: timeNow() + ' · ' + elapsed + 's · erreur',
        });
        return;
      }

      const data = await res.json();

      // Track conversation ID
      if (data.conversation_id) {
        currentConversationId = data.conversation_id;
      }

      appendMessage({
        role: 'agent',
        content: data.reponse,
        meta: timeNow() + ' · ' + elapsed + 's',
      });

      // Refresh sidebar
      loadConversations();

      // Refresh KPIs
      loadMetrics();
    } catch {
      hideTyping();
      appendMessage({
        role: 'agent',
        content: 'Impossible de joindre le serveur. Vérifiez que l\'API tourne sur le port 8000.',
        meta: timeNow() + ' · hors ligne',
      });
    }
  }

  // ── Form submit (hero input) ──────────────────────────────
  form.addEventListener('submit', function (e) {
    e.preventDefault();
    const query = input.value.trim();
    if (!query) return;
    input.value = '';
    submitQuery(query);
  });

  // ── Form submit (sticky input) ────────────────────────────
  formSticky.addEventListener('submit', function (e) {
    e.preventDefault();
    const query = inputSticky.value.trim();
    if (!query) return;
    inputSticky.value = '';
    submitQuery(query);
  });

  // ── New chat buttons ───────────────────────────────────────
  newChatBtn.addEventListener('click', function () {
    resetChat();
  });

  sidebarNewBtn.addEventListener('click', function () {
    resetChat();
    if (window.innerWidth <= 768) closeSidebar();
  });

  // ── Headline card clicks ────────────────────────────────────
  document.querySelectorAll('.luciole-headline-card').forEach(function (card) {
    card.addEventListener('click', function () {
      const prompt = card.getAttribute('data-prompt');
      if (prompt) {
        input.value = prompt;
        submitQuery(prompt);
        input.value = '';
      }
    });
  });

  // ── Init: load conversations ──────────────────────────────
  loadConversations();
})();
