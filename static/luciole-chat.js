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

  // ── Create streaming agent message DOM ─────────────────────
  function createAgentBubble() {
    const article = document.createElement('article');
    article.className = 'luciole-message luciole-message--agent';

    article.innerHTML =
      '<div class="luciole-message-avatar luciole-message-avatar--agent" aria-hidden="true">l<span style="color:var(--luciole-accent)">_</span></div>' +
      '<div class="luciole-message-body">' +
        '<div class="luciole-message-meta">' +
          '<span class="t-eyebrow-accent">luciole_</span>' +
          '<span class="t-meta luciole-stream-meta">réflexion…</span>' +
        '</div>' +
        '<div class="luciole-stream-steps"></div>' +
        '<div class="luciole-message-content t-body"></div>' +
      '</div>';

    chatMessages.appendChild(article);
    chatBottom.scrollIntoView({ behavior: 'smooth' });
    return article;
  }

  // ── Submit handler (SSE streaming) ─────────────────────────
  async function submitQuery(query) {
    if (!query.trim()) return;

    // Enter chat mode (collapse hero, show sticky input)
    enterChatMode();

    // Add user message
    appendMessage({ role: 'user', content: query, meta: timeNow() + ' · Requête' });

    // Show typing indicator while waiting for first event
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

      if (res.status === 401) {
        hideTyping();
        window.location.href = '/login';
        return;
      }

      if (!res.ok) {
        hideTyping();
        const elapsed = ((performance.now() - t0) / 1000).toFixed(1);
        appendMessage({
          role: 'agent',
          content: 'Erreur serveur — réessayez.',
          meta: timeNow() + ' · ' + elapsed + 's · erreur',
        });
        return;
      }

      // Check if response is SSE stream
      const contentType = res.headers.get('content-type') || '';
      if (!contentType.includes('text/event-stream')) {
        // Fallback: JSON response (non-streaming)
        hideTyping();
        const data = await res.json();
        if (data.conversation_id) currentConversationId = data.conversation_id;
        const elapsed = ((performance.now() - t0) / 1000).toFixed(1);
        appendMessage({ role: 'agent', content: data.reponse, meta: timeNow() + ' · ' + elapsed + 's' });
        loadConversations();
        loadMetrics();
        return;
      }

      // SSE streaming via ReadableStream
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let agentBubble = null;
      let contentEl = null;
      let stepsEl = null;
      let metaEl = null;
      let fullText = '';
      let firstChunk = true;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop(); // keep incomplete line in buffer

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const jsonStr = line.slice(6).trim();
          if (!jsonStr) continue;

          let event;
          try {
            event = JSON.parse(jsonStr);
          } catch {
            continue;
          }

          // Handle event types
          if (event.type === 'start') {
            if (event.conversation_id) {
              currentConversationId = event.conversation_id;
            }
            continue;
          }

          if (event.type === 'thinking') {
            // Replace typing indicator with agent bubble on first thinking event
            if (!agentBubble) {
              hideTyping();
              agentBubble = createAgentBubble();
              contentEl = agentBubble.querySelector('.luciole-message-content');
              stepsEl = agentBubble.querySelector('.luciole-stream-steps');
              metaEl = agentBubble.querySelector('.luciole-stream-meta');
            }
            // Add a step badge
            var badge = document.createElement('div');
            badge.className = 'luciole-step-badge';
            badge.innerHTML = '<span class="luciole-step-badge-dot"></span>' + escapeHtml(event.label || event.tool);
            stepsEl.appendChild(badge);
            chatBottom.scrollIntoView({ behavior: 'smooth' });
            continue;
          }

          if (event.type === 'tool_result') {
            // Mark the last step badge as done
            var badges = stepsEl ? stepsEl.querySelectorAll('.luciole-step-badge') : [];
            if (badges.length) {
              var last = badges[badges.length - 1];
              last.classList.add('luciole-step-badge--done');
            }
            continue;
          }

          if (event.type === 'chunk') {
            if (!agentBubble) {
              hideTyping();
              agentBubble = createAgentBubble();
              contentEl = agentBubble.querySelector('.luciole-message-content');
              stepsEl = agentBubble.querySelector('.luciole-stream-steps');
              metaEl = agentBubble.querySelector('.luciole-stream-meta');
            }
            if (firstChunk && metaEl) {
              metaEl.textContent = 'rédaction…';
              firstChunk = false;
            }
            fullText += event.content;
            // Render markdown incrementally
            contentEl.innerHTML = marked.parse(fullText);
            chatBottom.scrollIntoView({ behavior: 'smooth' });
            continue;
          }

          if (event.type === 'done') {
            var elapsed = ((performance.now() - t0) / 1000).toFixed(1);
            var latency = event.latency_ms ? (event.latency_ms / 1000).toFixed(1) + 's' : elapsed + 's';
            if (metaEl) {
              metaEl.textContent = timeNow() + ' · ' + latency;
            }
            // Final markdown render with full response
            if (contentEl && event.full_response) {
              contentEl.innerHTML = marked.parse(event.full_response);
            }
            continue;
          }

          if (event.type === 'error') {
            hideTyping();
            if (!agentBubble) {
              appendMessage({
                role: 'agent',
                content: 'Erreur : ' + (event.message || 'inconnue'),
                meta: timeNow() + ' · erreur',
              });
            } else if (contentEl) {
              contentEl.innerHTML = '<em>Erreur : ' + escapeHtml(event.message || 'inconnue') + '</em>';
            }
            continue;
          }
        }
      }

      // If we never got any content (edge case)
      if (!agentBubble) {
        hideTyping();
        appendMessage({
          role: 'agent',
          content: fullText || 'Aucune réponse reçue.',
          meta: timeNow(),
        });
      }

      // Refresh sidebar & KPIs
      loadConversations();
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
