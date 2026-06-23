/* ═══════════════════════════════════════════════════
   全局 AI 助手 — 悬浮窗 + 用户名 + 页面提示 + 工作流
   ═══════════════════════════════════════════════════ */
(function() {
  'use strict';

  // ── 页面路径 → 栏目名映射 ──
  var PAGE_MAP = {
    '/': '首页',
    '/console': '资讯站',
    '/dashboard': '资讯站',
    '/platforms': '平台',
    '/github': 'GitHub',
    '/finance': '金融',
    '/software': '软件站',
    '/agent-deploy': 'Agent部署',
    '/script-market': '脚本市场',
    '/ai-workflow': 'AI工作流',
    '/about': '开发实践',
    '/docs': '文档',
    '/demo': '演示',
    '/pricing': '定价',
  };

  // ── 工作流列表 ──
  var WORKFLOWS = [
    {id:'none',name:'不使用工作流',prompt:''},
    {id:'wf-trend',name:'📈 资讯趋势分析',prompt:'请分析当前页面的资讯趋势，总结热点话题和关键技术方向。'},
    {id:'wf-cve',name:'🛡️ CVE 漏洞监控',prompt:'请汇总最近的高危CVE漏洞，评估风险等级并给出修复建议。'},
    {id:'wf-github',name:'🔥 GitHub 热门分析',prompt:'请分析GitHub上的热门项目趋势，包括技术栈分布和增长预测。'},
    {id:'wf-finance',name:'💹 金融数据解读',prompt:'请解读当前的金融数据走势，生成投资参考和风险提示。'},
    {id:'wf-resource',name:'🔍 资源智能检索',prompt:'请根据当前页面内容，推荐相关的开发者工具、文档和API资源。'},
    {id:'wf-summary',name:'📊 页面内容总结',prompt:'请总结当前页面的重点内容，提取关键信息并结构化输出。'},
    {id:'wf-security',name:'🔐 安全威胁情报',prompt:'请汇总安全资讯和威胁数据，生成威胁情报报告。'},
  ];

  // ── 固定预设对话 ──
  var PRESET_CONVERSATIONS = [
    {icon:'📊',label:'总结页面',q:'请总结当前页面的重点内容'},
    {icon:'🛡️',label:'高危漏洞',q:'最近有哪些高危CVE漏洞？'},
    {icon:'🔥',label:'GitHub热门',q:'GitHub上有什么新的热门项目？'},
    {icon:'📰',label:'今日重点',q:'帮我分析一下今天的技术资讯重点'},
  ];

  // ── 状态 ──
  var userName = '';
  var aiName = '助手';
  var aiMessages = [];
  var aiContext = '';
  var aiContextTitle = '';
  var aiUnreadCount = 0;
  var sidebarOpen = false;
  var selectedWorkflow = 'none';

  // ── 工具函数 ──
  function esc(s) {
    var d = document.createElement('div');
    d.textContent = (s == null ? '' : s);
    return d.innerHTML;
  }

  function getPageName() {
    var path = window.location.pathname;
    if (PAGE_MAP[path]) return PAGE_MAP[path];
    for (var key in PAGE_MAP) {
      if (key !== '/' && path.indexOf(key) === 0) return PAGE_MAP[key];
    }
    return '未知页面';
  }

  // ── 用户名管理（sessionStorage：每次进站需重新输入）──
  function loadUserName() {
    try {
      userName = sessionStorage.getItem('opencrawler_username') || '';
    } catch(e) { userName = ''; }
  }

  function saveUserName(name) {
    userName = name || '用户';
    try { sessionStorage.setItem('opencrawler_username', userName); } catch(e) {}
  }

  // ── AI 名字管理（sessionStorage：仅当前会话有效）──
  function loadAIName() {
    try {
      aiName = sessionStorage.getItem('opencrawler_ainame') || '助手';
    } catch(e) { aiName = '助手'; }
  }

  function saveAIName(name) {
    aiName = (name && name.trim()) || '助手';
    try { sessionStorage.setItem('opencrawler_ainame', aiName); } catch(e) {}
    updateAIDisplayName();
  }

  function updateAIDisplayName() {
    // 更新头部标题
    var titleEl = document.querySelector('.gai-title');
    if (titleEl) {
      titleEl.innerHTML = esc(aiName) + ' · <span class="gai-user-name" id="gai-user-name">' + esc(userName) + '</span>';
    }
    // 更新所有助手消息的名称和头像
    var assistantMsgs = document.querySelectorAll('.gai-msg.assistant');
    assistantMsgs.forEach(function(msg) {
      var nameEl = msg.querySelector('.gai-msg-name');
      if (nameEl) nameEl.textContent = aiName;
      var avatarEl = msg.querySelector('.gai-msg-avatar');
      if (avatarEl) avatarEl.textContent = aiName.substring(0, 2);
    });
  }

  function showUserModal() {
    var modal = document.getElementById('gai-user-modal');
    if (!modal) return;
    modal.classList.add('show');
    setTimeout(function() {
      var input = document.getElementById('gai-user-input');
      if (input) input.focus();
    }, 300);
  }

  function hideUserModal() {
    var modal = document.getElementById('gai-user-modal');
    if (modal) modal.classList.remove('show');
  }

  function confirmUserName() {
    var input = document.getElementById('gai-user-input');
    var name = input ? input.value.trim() : '';
    saveUserName(name);
    hideUserModal();
    updateUserNameDisplay();
    updatePageIndicator();
    // 欢迎消息
    addAIMessage('assistant',
      '你好，**' + userName + '**！我是你的 **' + aiName + '**。\n\n' +
      '我可以帮你：\n- 分析当前页面的内容\n- 解答技术问题\n- 总结资讯趋势\n\n' +
      '选择下方的工作流可以让我更有针对性地为你服务。'
    );
    aiMessages.push({role:'assistant', content:'你好，' + userName + '！我是你的 ' + aiName + '。'});
    showPageToast();
  }

  function updateUserNameDisplay() {
    var el = document.getElementById('gai-user-name');
    if (el) el.textContent = userName;
    updatePageIndicator();
    var avatars = document.querySelectorAll('.gai-msg.user .gai-msg-avatar');
    avatars.forEach(function(a) { a.textContent = userName.substring(0, 2); });
    var names = document.querySelectorAll('.gai-msg.user .gai-msg-name');
    names.forEach(function(n) { n.textContent = userName; });
  }

  // ── 聊天内页面位置提示 ──
  function updatePageIndicator() {
    var el = document.getElementById('gai-pi-name');
    var pageEl = document.getElementById('gai-pi-page');
    if (el) el.textContent = userName;
    if (pageEl) pageEl.textContent = getPageName();
  }

  // ── 页面跳转提示（外部小字）──
  var toastTimer = null;
  function showPageToast() {
    var toast = document.getElementById('gai-toast');
    if (!toast) return;
    var pageName = getPageName();
    toast.innerHTML =
      '<span class="toast-name">' + esc(userName) + '</span> 正在查看 ' +
      '<span class="toast-page">' + esc(pageName) + '</span>';
    toast.classList.add('show');
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(function() {
      toast.classList.remove('show');
    }, 4000);
  }

  // ── 侧边栏开关 ──
  function toggleSidebar() {
    var sidebar = document.getElementById('gai-sidebar');
    var fab = document.getElementById('gai-fab');
    if (!sidebar || !fab) return;
    sidebarOpen = !sidebarOpen;
    if (sidebarOpen) {
      sidebar.classList.add('open');
      fab.style.display = 'none';
      aiUnreadCount = 0;
      updateFabBadge();
      updatePageIndicator();
      setTimeout(function() {
        var input = document.getElementById('gai-input');
        if (input) input.focus();
      }, 300);
    } else {
      sidebar.classList.remove('open');
      fab.style.display = 'flex';
    }
  }

  function openSidebar() { if (!sidebarOpen) toggleSidebar(); }
  function closeSidebar() { if (sidebarOpen) toggleSidebar(); }

  // ── API 设置 ──
  function toggleSettings() {
    var overlay = document.getElementById('gai-settings');
    if (!overlay) return;
    if (overlay.classList.contains('show')) {
      overlay.classList.remove('show');
    } else {
      overlay.classList.add('show');
      // 加载当前 AI 名字到输入框
      var aiNameInput = document.getElementById('gai-cfg-ainame');
      if (aiNameInput) aiNameInput.value = aiName;
      loadAIConfig();
    }
  }

  async function loadAIConfig() {
    try {
      var r = await fetch('/api/ai/config', {credentials:'same-origin'});
      if (r.status === 401) return;
      var data = await r.json();
      var elUrl = document.getElementById('gai-cfg-url');
      var elKey = document.getElementById('gai-cfg-key');
      var elModel = document.getElementById('gai-cfg-model');
      if (elUrl) elUrl.value = data.api_url || '';
      if (elKey) elKey.value = data.api_key || '';
      if (elModel) elModel.value = data.model || 'gpt-4o-mini';
      updateModelStatus(data.api_url && data.api_key ? (data.model || '就绪') : '演示模式');
    } catch(e) { console.error(e); }
  }

  async function saveAIConfig() {
    var apiUrl = document.getElementById('gai-cfg-url').value.trim();
    var apiKey = document.getElementById('gai-cfg-key').value.trim();
    var model = document.getElementById('gai-cfg-model').value.trim() || 'gpt-4o-mini';
    var statusEl = document.getElementById('gai-cfg-status');
    if (statusEl) { statusEl.textContent = '保存中...'; statusEl.className = 'cfg-status'; }
    try {
      var r = await fetch('/api/ai/config', {
        method:'POST', credentials:'same-origin',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({api_url:apiUrl, api_key:apiKey, model:model}),
      });
      var data = await r.json();
      if (data.ok) {
        if (statusEl) { statusEl.textContent = '配置已保存'; statusEl.className = 'cfg-status ok'; }
        updateModelStatus(apiUrl && apiKey ? model : '演示模式');
        setTimeout(function() { toggleSettings(); }, 800);
      } else {
        if (statusEl) { statusEl.textContent = data.error || '保存失败'; statusEl.className = 'cfg-status err'; }
      }
    } catch(e) {
      if (statusEl) { statusEl.textContent = '网络错误'; statusEl.className = 'cfg-status err'; }
    }
  }

  function updateModelStatus(text) {
    var el = document.getElementById('gai-model-status');
    if (el) el.textContent = text;
  }

  // ── 上下文管理 ──
  function setContext(title, content) {
    aiContextTitle = title;
    var temp = document.createElement('div');
    temp.innerHTML = content;
    aiContext = temp.textContent.trim().substring(0, 8000);
    var bar = document.getElementById('gai-context-bar');
    var titleEl = document.getElementById('gai-context-title');
    if (bar) bar.classList.add('show');
    if (titleEl) titleEl.textContent = title;
  }

  function clearContext() {
    aiContext = '';
    aiContextTitle = '';
    var bar = document.getElementById('gai-context-bar');
    if (bar) bar.classList.remove('show');
  }

  // ── 工作流选择 ──
  function onWorkflowChange() {
    var select = document.getElementById('gai-workflow-select');
    if (!select) return;
    selectedWorkflow = select.value;
    var wf = WORKFLOWS.find(function(w){return w.id === selectedWorkflow;});
    if (!wf || !wf.prompt) return;
    // 如果有工作流提示，自动填入输入框
    var input = document.getElementById('gai-input');
    if (input) {
      input.value = wf.prompt;
      autoResize(input);
      input.focus();
    }
  }

  // ── 聊天 ──
  function autoResize(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
  }

  function handleKeydown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  async function sendMessage() {
    var input = document.getElementById('gai-input');
    if (!input) return;
    var msg = input.value.trim();
    if (!msg) return;

    addAIMessage('user', msg);
    aiMessages.push({role:'user', content:msg});

    input.value = '';
    input.style.height = 'auto';

    var typingEl = showTyping();
    var sendBtn = document.getElementById('gai-send');
    if (sendBtn) sendBtn.disabled = true;
    updateModelStatus('思考中...');

    try {
      var systemMsg = '用户名：' + userName + '。当前页面：' + getPageName() + '。你的名字是「' + aiName + '」，请以这个名字自称。';
      if (aiContext) systemMsg += '用户正在阅读文章：' + aiContextTitle;
      // 工作流上下文
      var wf = WORKFLOWS.find(function(w){return w.id === selectedWorkflow;});
      if (wf && wf.prompt) systemMsg += ' 当前工作流模式：' + wf.name + '。指导：' + wf.prompt;
      var messagesToSend = [{role:'system', content:systemMsg}].concat(aiMessages);

      var r = await fetch('/api/ai/chat', {
        method:'POST', credentials:'same-origin',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({messages:messagesToSend, context:aiContext}),
      });

      if (r.status === 401) {
        typingEl.remove();
        addAIMessage('assistant', '当前为预览版 demo，暂不支持接入 API，敬请期待。');
        updateModelStatus('预览模式');
        if (sendBtn) sendBtn.disabled = false;
        return;
      }

      var data = await r.json();
      typingEl.remove();

      if (data.error) {
        addAIMessage('assistant', '⚠️ 错误：' + data.error);
      } else {
        var reply = data.reply || '(空回复)';
        addAIMessage('assistant', reply, data.model);
        aiMessages.push({role:'assistant', content:reply});
        if (!sidebarOpen) {
          aiUnreadCount++;
          updateFabBadge();
        }
      }
      updateModelStatus(data.model === 'demo-mode' ? '演示模式' : '就绪');
    } catch(e) {
      typingEl.remove();
      addAIMessage('assistant', '⚠️ 网络错误，请检查服务器连接。');
      updateModelStatus('离线');
    }

    if (sendBtn) sendBtn.disabled = false;
  }

  function addAIMessage(role, content, model) {
    var messages = document.getElementById('gai-messages');
    if (!messages) return;
    var msgEl = document.createElement('div');
    msgEl.className = 'gai-msg ' + role;

    var avatar, name;
    if (role === 'user') {
      avatar = userName.substring(0, 2);
      name = userName;
    } else {
      avatar = aiName.substring(0, 2);
      name = aiName;
    }
    var time = new Date().toLocaleTimeString('zh-CN', {hour:'2-digit', minute:'2-digit'});
    var formatted = formatContent(content);

    msgEl.innerHTML =
      '<div class="gai-msg-head">' +
        '<div class="gai-msg-avatar">' + esc(avatar) + '</div>' +
        '<span class="gai-msg-name">' + esc(name) + '</span>' +
        '<span class="gai-msg-time">' + time + '</span>' +
      '</div>' +
      '<div class="gai-msg-bubble">' + formatted + '</div>';
    messages.appendChild(msgEl);
    messages.scrollTop = messages.scrollHeight;
  }

  function formatContent(text) {
    var html = esc(text);
    html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^[\-\*] (.+)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>[\s\S]*?<\/li>)/g, '<ul>$1</ul>');
    html = html.replace(/\n\n/g, '</p><p>');
    html = '<p>' + html + '</p>';
    html = html.replace(/<p>\s*<\/p>/g, '');
    return html;
  }

  function showTyping() {
    var messages = document.getElementById('gai-messages');
    if (!messages) return document.createElement('div');
    var el = document.createElement('div');
    el.className = 'gai-msg assistant';
    el.innerHTML =
      '<div class="gai-msg-head">' +
        '<div class="gai-msg-avatar">' + esc(aiName.substring(0, 2)) + '</div>' +
        '<span class="gai-msg-name">' + esc(aiName) + '</span>' +
      '</div>' +
      '<div class="gai-msg-bubble">' +
        '<div class="gai-typing"><span></span><span></span><span></span></div>' +
      '</div>';
    messages.appendChild(el);
    messages.scrollTop = messages.scrollHeight;
    return el;
  }

  function updateFabBadge() {
    var badge = document.getElementById('gai-badge');
    if (!badge) return;
    if (aiUnreadCount > 0) {
      badge.textContent = aiUnreadCount > 9 ? '9+' : aiUnreadCount;
      badge.classList.add('show');
    } else {
      badge.classList.remove('show');
    }
  }

  function quickAsk(question) {
    var input = document.getElementById('gai-input');
    if (!input) return;
    input.value = question;
    autoResize(input);
    sendMessage();
  }

  // ── 拖拽调整宽度 ──
  function initResize() {
    var handle = document.getElementById('gai-resize');
    var sidebar = document.getElementById('gai-sidebar');
    if (!handle || !sidebar) return;
    var startX = 0, startW = 0;
    handle.addEventListener('mousedown', function(e) {
      startX = e.clientX;
      startW = sidebar.offsetWidth;
      sidebar.classList.add('dragging');
      document.addEventListener('mousemove', onResize);
      document.addEventListener('mouseup', stopResize);
      e.preventDefault();
    });
    function onResize(e) {
      var dx = startX - e.clientX;
      var newW = Math.max(300, Math.min(600, startW + dx));
      sidebar.style.width = newW + 'px';
    }
    function stopResize() {
      sidebar.classList.remove('dragging');
      document.removeEventListener('mousemove', onResize);
      document.removeEventListener('mouseup', stopResize);
    }
  }

  // ── 键盘快捷键 ──
  function initKeyboard() {
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape') {
        if (document.getElementById('gai-settings') && document.getElementById('gai-settings').classList.contains('show')) {
          toggleSettings();
        } else if (sidebarOpen) {
          toggleSidebar();
        }
      }
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        toggleSidebar();
      }
    });
  }

  // ── 注入 HTML ──
  function injectHTML() {
    // 构建工作流选项
    var wfOptions = WORKFLOWS.map(function(w) {
      return '<option value="' + w.id + '">' + esc(w.name) + '</option>';
    }).join('');

    // 构建预设对话按钮
    var presetBtns = PRESET_CONVERSATIONS.map(function(p) {
      return '<span class="gai-quick-btn" data-q="' + esc(p.q) + '">' + p.icon + ' ' + esc(p.label) + '</span>';
    }).join('');

    var html =
      // 用户 ID 弹窗
      '<div id="gai-user-modal">' +
        '<div class="gai-modal-card">' +
          '<div class="modal-icon">' +
            '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>' +
          '</div>' +
          '<h3>欢迎来到 OpenCrawler</h3>' +
          '<p>输入你的 ID，AI 助手会用这个名字称呼你<br>不输入则默认叫"用户"</p>' +
          '<div class="modal-input-wrap">' +
            '<input type="text" style="display:none" autocomplete="off" aria-hidden="true">' +
            '<input type="password" style="display:none" autocomplete="off" aria-hidden="true">' +
            '<input type="text" class="modal-input" id="gai-user-input" placeholder="输入你的 ID..." maxlength="20" autocomplete="new-password">' +
          '</div>' +
          '<div class="modal-btns">' +
            '<button class="modal-btn secondary" id="gai-user-skip">跳过</button>' +
            '<button class="modal-btn primary" id="gai-user-ok">确认</button>' +
          '</div>' +
        '</div>' +
      '</div>' +

      // 页面跳转提示
      '<div id="gai-toast"></div>' +

      // 悬浮按钮
      '<button id="gai-fab" title="打开 AI 助手">' +
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>' +
        '<span class="gai-badge" id="gai-badge">0</span>' +
      '</button>' +

      // 侧边栏
      '<div id="gai-sidebar">' +
        '<div id="gai-resize"></div>' +

        // 头部
        '<div class="gai-header">' +
          '<div class="gai-icon">' +
            '<svg viewBox="0 0 32 32" width="20" height="20"><circle cx="16" cy="16" r="14" fill="none" stroke="#fff" stroke-width="1.5" opacity="0.3"/><circle cx="16" cy="16" r="9" fill="none" stroke="#fff" stroke-width="1.5" opacity="0.5"/><circle cx="16" cy="16" r="4" fill="#fff"/><path d="M16 4 L16 8 M16 24 L16 28 M4 16 L8 16 M24 16 L28 16" stroke="#fff" stroke-width="1.5" stroke-linecap="round" opacity="0.4"/></svg>' +
          '</div>' +
          '<div class="gai-title-wrap">' +
            '<div class="gai-title">' + esc(aiName) + ' · <span class="gai-user-name" id="gai-user-name">用户</span></div>' +
            '<div class="gai-status"><span class="dot"></span> <span id="gai-model-status">就绪</span></div>' +
          '</div>' +
          '<button class="gai-btn" id="gai-btn-settings" title="API 设置">' +
            '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>' +
          '</button>' +
          '<button class="gai-btn" id="gai-btn-close" title="关闭">✕</button>' +
        '</div>' +

        // 聊天内页面位置提示
        '<div class="gai-page-indicator">' +
          '<span class="pi-name" id="gai-pi-name">用户</span>' +
          '<span class="pi-arrow">→</span>' +
          '<span class="pi-page" id="gai-pi-page">首页</span>' +
        '</div>' +

        // 工作流选择器
        '<div class="gai-workflow-bar">' +
          '<span class="gai-workflow-label">工作流</span>' +
          '<select class="gai-workflow-select" id="gai-workflow-select">' + wfOptions + '</select>' +
        '</div>' +

        // 上下文栏
        '<div class="gai-context-bar" id="gai-context-bar">' +
          '<span class="ctx-label">📎 上下文:</span>' +
          '<span id="gai-context-title" style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1"></span>' +
          '<span class="ctx-clear" id="gai-ctx-clear">✕</span>' +
        '</div>' +

        // 消息区
        '<div class="gai-messages" id="gai-messages">' +
          '<div class="gai-msg assistant">' +
            '<div class="gai-msg-head">' +
              '<div class="gai-msg-avatar">' + esc(aiName.substring(0, 2)) + '</div>' +
              '<span class="gai-msg-name">' + esc(aiName) + '</span>' +
            '</div>' +
            '<div class="gai-msg-bubble">' +
              '<p>你好！我是 <strong>' + esc(aiName) + '</strong>。</p>' +
              '<p>我可以帮你：</p>' +
              '<ul>' +
                '<li>分析当前页面内容</li>' +
                '<li>解答技术问题</li>' +
                '<li>总结资讯趋势</li>' +
              '</ul>' +
              '<p>上方可选择<strong>工作流</strong>，让我更有针对性地为你服务。</p>' +
            '</div>' +
          '</div>' +
        '</div>' +

        // 快捷操作（预设对话）
        '<div class="gai-quick">' + presetBtns + '</div>' +

        // 输入区
        '<div class="gai-input-area">' +
          '<div class="gai-input-wrap">' +
            '<textarea class="gai-input" id="gai-input" placeholder="输入消息，按 Enter 发送..." rows="1"></textarea>' +
            '<button class="gai-send" id="gai-send">' +
              '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>' +
            '</button>' +
          '</div>' +
          '<div class="gai-input-hint">Enter 发送 · Shift+Enter 换行 · Ctrl+K 开关</div>' +
        '</div>' +

        // API 设置面板
        '<div id="gai-settings">' +
          '<div class="gai-settings-header">' +
            '<span class="sh-title">设置</span>' +
            '<button class="gai-btn" id="gai-settings-close">✕</button>' +
          '</div>' +
          '<div class="gai-settings-body">' +
            '<div class="cfg-group">' +
              '<label class="cfg-label">AI 名字</label>' +
              '<input type="text" class="cfg-input" id="gai-cfg-ainame" placeholder="助手" maxlength="10" autocomplete="new-password">' +
              '<div class="cfg-hint">设置你喜欢的 AI 助手名字（最多 10 字）</div>' +
            '</div>' +
            '<button class="cfg-save" id="gai-cfg-ainame-save">应用名字</button>' +
            '<div class="cfg-divider"></div>' +
            '<div class="cfg-info">' +
              '配置你自己的 AI API（OpenAI 兼容格式）。留空则使用演示模式。<br>' +
              '支持 OpenAI / DeepSeek / 通义千问 / Moonshot 等。' +
            '</div>' +
            '<div class="cfg-divider"></div>' +
            '<div class="cfg-group">' +
              '<label class="cfg-label">API 地址</label>' +
              '<input type="text" class="cfg-input" id="gai-cfg-url" placeholder="https://api.openai.com/v1/chat/completions" autocomplete="new-password">' +
              '<div class="cfg-hint">OpenAI 兼容的 Chat Completions 端点</div>' +
            '</div>' +
            '<div class="cfg-group">' +
              '<label class="cfg-label">API Key</label>' +
              '<input type="password" class="cfg-input" id="gai-cfg-key" placeholder="sk-..." autocomplete="new-password">' +
              '<div class="cfg-hint">你的 API 密钥，存储在服务端</div>' +
            '</div>' +
            '<div class="cfg-group">' +
              '<label class="cfg-label">模型名称</label>' +
              '<input type="text" class="cfg-input" id="gai-cfg-model" placeholder="gpt-4o-mini" autocomplete="new-password">' +
              '<div class="cfg-hint">如 gpt-4o-mini / deepseek-chat / qwen-plus</div>' +
            '</div>' +
            '<button class="cfg-save" id="gai-cfg-save">保存配置</button>' +
            '<div class="cfg-status" id="gai-cfg-status"></div>' +
          '</div>' +
        '</div>' +
      '</div>';

    var container = document.createElement('div');
    container.innerHTML = html;
    while (container.firstChild) {
      document.body.appendChild(container.firstChild);
    }
  }

  // ── 绑定事件 ──
  function bindEvents() {
    var fab = document.getElementById('gai-fab');
    if (fab) fab.addEventListener('click', toggleSidebar);

    var btnClose = document.getElementById('gai-btn-close');
    if (btnClose) btnClose.addEventListener('click', toggleSidebar);

    var btnSettings = document.getElementById('gai-btn-settings');
    if (btnSettings) btnSettings.addEventListener('click', toggleSettings);

    var settingsClose = document.getElementById('gai-settings-close');
    if (settingsClose) settingsClose.addEventListener('click', toggleSettings);

    var cfgSave = document.getElementById('gai-cfg-save');
    if (cfgSave) cfgSave.addEventListener('click', saveAIConfig);

    var aiNameSave = document.getElementById('gai-cfg-ainame-save');
    if (aiNameSave) aiNameSave.addEventListener('click', function() {
      var input = document.getElementById('gai-cfg-ainame');
      var name = input ? input.value.trim() : '';
      saveAIName(name);
      var statusEl = document.getElementById('gai-cfg-status');
      if (statusEl) { statusEl.textContent = 'AI 名字已更新为「' + aiName + '」'; statusEl.className = 'cfg-status ok'; }
      setTimeout(function() { if (statusEl) { statusEl.textContent = ''; statusEl.className = 'cfg-status'; } }, 2000);
    });

    var aiNameInput = document.getElementById('gai-cfg-ainame');
    if (aiNameInput) {
      aiNameInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
          var name = this.value.trim();
          saveAIName(name);
          var statusEl = document.getElementById('gai-cfg-status');
          if (statusEl) { statusEl.textContent = 'AI 名字已更新为「' + aiName + '」'; statusEl.className = 'cfg-status ok'; }
          setTimeout(function() { if (statusEl) { statusEl.textContent = ''; statusEl.className = 'cfg-status'; } }, 2000);
        }
      });
    }

    var sendBtn = document.getElementById('gai-send');
    if (sendBtn) sendBtn.addEventListener('click', sendMessage);

    var input = document.getElementById('gai-input');
    if (input) {
      input.addEventListener('keydown', handleKeydown);
      input.addEventListener('input', function() { autoResize(this); });
    }

    document.querySelectorAll('.gai-quick-btn').forEach(function(btn) {
      btn.addEventListener('click', function() {
        quickAsk(this.getAttribute('data-q'));
      });
    });

    var ctxClear = document.getElementById('gai-ctx-clear');
    if (ctxClear) ctxClear.addEventListener('click', clearContext);

    // 工作流选择
    var wfSelect = document.getElementById('gai-workflow-select');
    if (wfSelect) wfSelect.addEventListener('change', onWorkflowChange);

    // 用户 ID 弹窗
    var userOk = document.getElementById('gai-user-ok');
    if (userOk) userOk.addEventListener('click', confirmUserName);

    var userSkip = document.getElementById('gai-user-skip');
    if (userSkip) userSkip.addEventListener('click', function() {
      saveUserName('用户');
      hideUserModal();
      updateUserNameDisplay();
      showPageToast();
    });

    var userInput = document.getElementById('gai-user-input');
    if (userInput) {
      userInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') confirmUserName();
      });
    }

    // 页面跳转检测
    window.addEventListener('popstate', function() {
      setTimeout(function() {
        showPageToast();
        updatePageIndicator();
      }, 100);
    });
  }

  // ── 初始化 ──
  function init() {
    if (window.__gaiInitialized) return;
    window.__gaiInitialized = true;

    loadAIName();
    loadUserName();
    injectHTML();

    if (!userName) {
      showUserModal();
    } else {
      updateUserNameDisplay();
      showPageToast();
    }

    bindEvents();
    initResize();
    initKeyboard();
    loadAIConfig();
  }

  // ── 暴露全局 API ──
  window.AIAssistant = {
    open: openSidebar,
    close: closeSidebar,
    toggle: toggleSidebar,
    setContext: setContext,
    clearContext: clearContext,
    ask: quickAsk,
    getUserName: function() { return userName; },
    getAIName: function() { return aiName; },
    setAIName: function(name) { saveAIName(name); },
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
