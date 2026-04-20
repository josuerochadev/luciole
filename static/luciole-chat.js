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

  // Auth state (set by template)
  const isLoggedIn = window.__lucioleUser === true;

  // Sidebar elements (only exist if logged in)
  const sidebar = document.getElementById('sidebar');
  const sidebarList = document.getElementById('sidebar-list');
  const sidebarNewBtn = document.getElementById('sidebar-new-btn');
  const sidebarToggle = document.getElementById('sidebar-toggle');
  const sidebarOverlay = document.getElementById('sidebar-overlay');

  // File upload elements
  const attachBtn = document.getElementById('attach-btn');
  const fileInput = document.getElementById('file-input');
  const filePreview = document.getElementById('file-preview');
  const attachBtnSticky = document.getElementById('attach-btn-sticky');
  const fileInputSticky = document.getElementById('file-input-sticky');
  const filePreviewSticky = document.getElementById('file-preview-sticky');

  // State
  let currentConversationId = null;
  let pendingFile = null; // { file: File, previewEl: HTMLElement }

  // Allowed MIME types (client-side filter)
  var ALLOWED_TYPES = new Set([
    'image/png', 'image/jpeg', 'image/webp',
    'audio/mpeg', 'audio/mp4', 'audio/wav',
    'application/pdf',
  ]);
  var MAX_FILE_SIZE = 10 * 1024 * 1024; // 10 MB

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

  if (sidebarToggle) sidebarToggle.addEventListener('click', toggleSidebar);
  if (sidebarOverlay) sidebarOverlay.addEventListener('click', closeSidebar);

  // ── Sidebar — Load conversations ──────────────────────────
  async function loadConversations() {
    try {
      const res = await fetch('/conversations');
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
    clearPendingFile();
    input.focus();

    // Clear active state in sidebar
    sidebarList.querySelectorAll('.luciole-sidebar-item').forEach(function (item) {
      item.classList.remove('active');
    });
  }

  // ── Create message DOM ──────────────────────────────────────
  function appendMessage({ role, content, meta, attachment }) {
    const article = document.createElement('article');
    article.className = 'luciole-message luciole-message--' + role;

    const isAgent = role === 'agent';
    const avatarClass = isAgent ? 'luciole-message-avatar luciole-message-avatar--agent' : 'luciole-message-avatar';
    const avatarContent = isAgent ? 'l<span style="color:var(--luciole-accent)">_</span>' : 'U';
    const labelClass = isAgent ? 't-eyebrow-accent' : 't-eyebrow';
    const label = isAgent ? 'luciole_' : 'Vous';

    const rendered = isAgent ? marked.parse(content) : escapeHtml(content);

    // Build attachment HTML for user messages
    var attachHtml = '';
    if (attachment && attachment instanceof File) {
      if (attachment.type.startsWith('image/')) {
        var imgUrl = URL.createObjectURL(attachment);
        attachHtml = '<div class="luciole-msg-attachment"><img src="' + imgUrl + '" class="luciole-msg-image" alt="Image jointe"></div>';
      } else if (attachment.type.startsWith('audio/')) {
        var audioUrl = URL.createObjectURL(attachment);
        attachHtml = '<div class="luciole-msg-attachment"><audio controls src="' + audioUrl + '" class="luciole-msg-audio"></audio><span class="t-meta">' + escapeHtml(attachment.name) + '</span></div>';
      } else {
        attachHtml = '<div class="luciole-msg-attachment"><span class="luciole-file-icon">&#128196;</span> <span class="t-meta">' + escapeHtml(attachment.name) + '</span></div>';
      }
    }

    article.innerHTML =
      '<div class="' + avatarClass + '" aria-hidden="true">' + avatarContent + '</div>' +
      '<div class="luciole-message-body">' +
        '<div class="luciole-message-meta">' +
          '<span class="' + labelClass + '">' + label + '</span>' +
          '<span class="t-meta">' + meta + '</span>' +
        '</div>' +
        attachHtml +
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

  // ── File upload helpers ──────────────────────────────────────

  function selectFile(file, previewEl) {
    if (!file) return;

    if (!ALLOWED_TYPES.has(file.type)) {
      alert('Type de fichier non supporté.\nTypes acceptés : PNG, JPEG, WebP, MP3, M4A, WAV, PDF');
      return;
    }
    if (file.size > MAX_FILE_SIZE) {
      alert('Fichier trop volumineux (max 10 MB).');
      return;
    }

    pendingFile = { file: file, previewEl: previewEl };
    renderFilePreview(file, previewEl);
  }

  function renderFilePreview(file, previewEl) {
    previewEl.hidden = false;
    var isImage = file.type.startsWith('image/');
    var isAudio = file.type.startsWith('audio/');
    var sizeMB = (file.size / (1024 * 1024)).toFixed(1);

    var html = '<div class="luciole-file-preview-content">';
    if (isImage) {
      var url = URL.createObjectURL(file);
      html += '<img src="' + url + '" class="luciole-file-thumb" alt="Aperçu">';
    } else if (isAudio) {
      html += '<span class="luciole-file-icon">&#9835;</span>';
    } else {
      html += '<span class="luciole-file-icon">&#128196;</span>';
    }
    html += '<span class="luciole-file-info">' + escapeHtml(file.name) + ' <span class="t-meta">(' + sizeMB + ' MB)</span></span>';
    html += '<button type="button" class="luciole-file-remove" aria-label="Retirer le fichier">&times;</button>';
    html += '</div>';
    previewEl.innerHTML = html;

    previewEl.querySelector('.luciole-file-remove').addEventListener('click', function () {
      clearPendingFile();
    });
  }

  function clearPendingFile() {
    if (pendingFile && pendingFile.previewEl) {
      pendingFile.previewEl.innerHTML = '';
      pendingFile.previewEl.hidden = true;
    }
    pendingFile = null;
    fileInput.value = '';
    fileInputSticky.value = '';
  }

  async function uploadFile(file) {
    var formData = new FormData();
    formData.append('file', file);

    var res = await fetch('/upload', { method: 'POST', body: formData });
    if (!res.ok) {
      var err = await res.json().catch(function () { return { detail: 'Erreur upload' }; });
      throw new Error(err.detail || 'Erreur upload');
    }
    return res.json();
  }

  // ── Attach button clicks ────────────────────────────────────
  attachBtn.addEventListener('click', function () { fileInput.click(); });
  attachBtnSticky.addEventListener('click', function () { fileInputSticky.click(); });

  fileInput.addEventListener('change', function () {
    if (fileInput.files[0]) selectFile(fileInput.files[0], filePreview);
  });
  fileInputSticky.addEventListener('change', function () {
    if (fileInputSticky.files[0]) selectFile(fileInputSticky.files[0], filePreviewSticky);
  });

  // ── Drag & drop on chat zone ──────────────────────────────
  var dropTarget = chatZone.parentElement || document.body;

  dropTarget.addEventListener('dragover', function (e) {
    e.preventDefault();
    dropTarget.classList.add('luciole-dragover');
  });
  dropTarget.addEventListener('dragleave', function (e) {
    if (!dropTarget.contains(e.relatedTarget)) {
      dropTarget.classList.remove('luciole-dragover');
    }
  });
  dropTarget.addEventListener('drop', function (e) {
    e.preventDefault();
    dropTarget.classList.remove('luciole-dragover');
    if (e.dataTransfer.files.length) {
      var activePreview = chatZone.hidden ? filePreview : filePreviewSticky;
      selectFile(e.dataTransfer.files[0], activePreview);
    }
  });

  // ── Submit handler (SSE streaming) ─────────────────────────
  async function submitQuery(query, fileOverride) {
    if (!query.trim() && !pendingFile && !fileOverride) return;

    // Capture the pending file before clearing
    var fileToSend = fileOverride || (pendingFile ? pendingFile.file : null);
    var fileInfo = null;

    // Enter chat mode (collapse hero, show sticky input)
    enterChatMode();

    // Build user message content with file preview
    var userContent = query;
    var userMeta = timeNow() + ' · Requête';
    var userAttachment = null;

    if (fileToSend) {
      userAttachment = fileToSend;
      if (!query.trim()) {
        query = 'Analyse ce fichier';
        userContent = query;
      }
    }

    // Add user message
    appendMessage({ role: 'user', content: userContent, meta: userMeta, attachment: userAttachment });

    // Clear pending file
    clearPendingFile();

    // Show typing indicator while waiting for first event
    showTyping();
    const t0 = performance.now();

    try {
      // Upload file first if present
      var fileId = null;
      if (fileToSend) {
        try {
          fileInfo = await uploadFile(fileToSend);
          fileId = fileInfo.file_id;
        } catch (uploadErr) {
          hideTyping();
          appendMessage({
            role: 'agent',
            content: 'Erreur lors de l\'upload : ' + uploadErr.message,
            meta: timeNow() + ' · erreur',
          });
          return;
        }
      }

      const body = { question: query };
      if (currentConversationId) {
        body.conversation_id = currentConversationId;
      }
      if (fileId) {
        body.file_id = fileId;
      }

      const res = await fetch('/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

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
        if (isLoggedIn) loadConversations();
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
      if (isLoggedIn) loadConversations();
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

  if (sidebarNewBtn) {
    sidebarNewBtn.addEventListener('click', function () {
      resetChat();
      if (window.innerWidth <= 768) closeSidebar();
    });
  }

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

  // ── Init: load conversations (connectés uniquement) ───────
  if (isLoggedIn) loadConversations();
})();
