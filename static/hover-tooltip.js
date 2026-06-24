/**
 * Global Hover Tooltip — 悬停1秒后显示项目/股票详细信息
 * Auto-attaches to project cards, stock items, etc.
 */
(function () {
  'use strict';

  // ── 项目数据缓存（从 gh-avatars.js 的 AVATAR_CACHE 扩展） ──
  var PROJECT_DETAILS = {
    "anthropics/claude-code": { name:"Claude Code", stars:"134K", lang:"Python", license:"闭源免费", desc:"Anthropic 官方 CLI Agent，终端内编码、调试、重构。支持多文件编辑、Git 集成、MCP 工具调用。", features:["终端编码","Git 集成","MCP 工具","多文件编辑"], update:"每日更新" },
    "openclaw/openclaw": { name:"OpenClaw", stars:"380K", lang:"TypeScript", license:"MIT", desc:"开源个人 AI 助手（原 Clawdbot），支持技能扩展、浏览器操控、文件管理。Peter Steinberger 开发。", features:["技能扩展","浏览器操控","文件管理","全平台"], update:"活跃" },
    "browser-use/browser-use": { name:"browser-use", stars:"100K", lang:"Python", license:"MIT", desc:"浏览器自动化 Agent，让 AI 像人一样操作网页，支持视觉理解和复杂多步任务。", features:["浏览器自动化","视觉理解","多步任务","多 LLM 支持"], update:"活跃" },
    "tinyhumansai/openhuman": { name:"OpenHuman", stars:"33K", lang:"Rust", license:"GPL-3.0", desc:"开源桌面端个人 AI 超级智能，Rust + Tauri 构建，本地记忆树 + 118+ 集成 + 语音。", features:["本地记忆树","118+ 集成","语音","桌面吉祥物"], update:"Early Beta" },
    "mannaandpoem/openmanus": { name:"OpenManus", stars:"42K", lang:"Python", license:"MIT", desc:"开源通用 AI Agent 框架，多工具调用 + 浏览器操控，无需邀请码即可使用。", features:["多工具调用","浏览器操控","开源","易部署"], update:"活跃" },
    "crewaiinc/crewai": { name:"CrewAI", stars:"54K", lang:"Python", license:"MIT", desc:"多 Agent 协作框架，角色扮演 + 任务委派，支持顺序和并行任务执行。", features:["多 Agent 协作","角色扮演","任务委派","流程编排"], update:"活跃" },
    "significant-gravitas/autogpt": { name:"AutoGPT", stars:"185K", lang:"Python", license:"MIT", desc:"自主 AI Agent 鼻祖，长链任务规划执行，能自主分解任务并调用工具完成。", features:["自主规划","长链任务","工具调用","社区活跃"], update:"活跃" },
    "openai/codex": { name:"Codex CLI", stars:"93K", lang:"Rust", license:"Apache-2.0", desc:"OpenAI 官方终端编程 Agent，自然语言→代码，支持多语言、代码审查、测试生成。", features:["终端编程","代码审查","测试生成","多语言"], update:"每日更新" },
    "aider-ai/aider": { name:"Aider", stars:"47K", lang:"Python", license:"Apache-2.0", desc:"AI 结对编程工具，终端内 Git 感知的代码助手，支持 60+ 语言。", features:["Git 感知","60+ 语言","多模型","代码重构"], update:"活跃" },
    "cursor/cursor": { name:"Cursor", stars:"33K", lang:"TypeScript", license:"闭源免费", desc:"AI 代码编辑器（闭源），深度集成 Agent 能力，支持代码库理解、多文件重构。", features:["AI 编辑器","代码库理解","多文件重构","Tab 补全"], update:"活跃" },
    "continuedev/continue": { name:"Continue", stars:"34K", lang:"TypeScript", license:"Apache-2.0", desc:"开源 AI 代码助手 IDE 插件，支持 VS Code 和 JetBrains，可自定义模型。", features:["VS Code","JetBrains","自定义模型","开源"], update:"活跃" },
    "qwenlm/qwen-code": { name:"Qwen Code", stars:"25K", lang:"TypeScript", license:"Apache-2.0", desc:"阿里开源 CLI 编码 Agent，类 Claude Code 体验，专为 Qwen 模型优化。", features:["CLI 编码","Qwen 优化","开源","中文友好"], update:"活跃" },
    "ollama/ollama": { name:"Ollama", stars:"175K", lang:"Go", license:"MIT", desc:"本地大模型一键运行，支持 LLaMA/Mistral/Qwen 等模型，简单命令行操作。", features:["一键运行","多模型","API 服务","Docker"], update:"活跃" },
    "open-webui/open-webui": { name:"Open WebUI", stars:"143K", lang:"Python", license:"MIT", desc:"类 ChatGPT 前端，可连接 Ollama/OpenAI/Claude，支持多用户、RAG、模型管理。", features:["多模型","多用户","RAG","模型管理"], update:"活跃" },
    "langgenius/dify": { name:"Dify", stars:"146K", lang:"TypeScript", license:"Apache-2.0", desc:"开源 LLMOps 平台，可视化搭建 AI 应用，支持工作流编排、RAG、Agent。", features:["可视化搭建","工作流","RAG","多模型"], update:"活跃" },
    "labring/fastgpt": { name:"FastGPT", stars:"29K", lang:"TypeScript", license:"Apache-2.0", desc:"开源知识库问答，RAG + 工作流编排，支持企业级部署。", features:["知识库","RAG","工作流","企业级"], update:"活跃" },
    "langchain-ai/langchain": { name:"LangChain", stars:"140K", lang:"Python", license:"MIT", desc:"LLM 应用开发框架，链式调用 + Tool + RAG，生态最丰富的 AI 开发框架。", features:["链式调用","Tool","RAG","生态丰富"], update:"活跃" },
    "1panel-dev/maxkb": { name:"MaxKB", stars:"21K", lang:"Python", license:"GPL-3.0", desc:"飞致云开源知识库问答，RAG + 企业级，支持多模型、文档解析。", features:["知识库","RAG","企业级","多模型"], update:"活跃" },
    "infiniflow/ragflow": { name:"RAGFlow", stars:"84K", lang:"Go", license:"Apache-2.0", desc:"深度文档理解 RAG 引擎，OCR + 表格解析，支持复杂文档的精准问答。", features:["深度文档理解","OCR","表格解析","精准问答"], update:"活跃" },
    "comfyanonymous/comfyui": { name:"ComfyUI", stars:"118K", lang:"Python", license:"GPL-3.0", desc:"节点式 AI 绘画工作流，SD/Flux 最强前端，支持自定义节点和模型。", features:["节点式","SD/Flux","自定义节点","工作流"], update:"活跃" },
    "mintplex-labs/anything-llm": { name:"AnythingLLM", stars:"62K", lang:"JavaScript", license:"MIT", desc:"全能 AI 桌面应用，文档对话/Agent/RAG 一应俱全，支持多模型。", features:["文档对话","Agent","RAG","桌面应用"], update:"活跃" }
  };

  // ── Tooltip DOM ──
  var tooltip = null;
  var hoverTimer = null;

  function createTooltip() {
    if (tooltip) return tooltip;
    tooltip = document.createElement('div');
    tooltip.id = 'gh-hover-tooltip';
    tooltip.style.cssText = [
      'position:fixed','z-index:99999','max-width:360px','min-width:260px',
      'background:#fff','border:1px solid #e0e0e0','border-radius:12px',
      'box-shadow:0 8px 32px rgba(0,0,0,.15)','padding:0',
      'opacity:0','transform:translateY(4px)','transition:opacity .2s,transform .2s',
      'pointer-events:none','overflow:hidden','font-family:inherit'
    ].join(';');
    document.body.appendChild(tooltip);
    return tooltip;
  }

  function showTooltip(html, x, y) {
    var t = createTooltip();
    t.innerHTML = html;
    t.style.opacity = '0';
    t.style.display = 'block';
    // Position
    var rect = t.getBoundingClientRect();
    var tx = x + 16;
    var ty = y + 16;
    if (tx + rect.width > window.innerWidth - 8) tx = x - rect.width - 16;
    if (ty + rect.height > window.innerHeight - 8) ty = window.innerHeight - rect.height - 8;
    t.style.left = tx + 'px';
    t.style.top = ty + 'px';
    requestAnimationFrame(function() {
      t.style.opacity = '1';
      t.style.transform = 'translateY(0)';
    });
  }

  function hideTooltip() {
    if (tooltip) {
      tooltip.style.opacity = '0';
      tooltip.style.transform = 'translateY(4px)';
      setTimeout(function() { if (tooltip) tooltip.style.display = 'none'; }, 200);
    }
  }

  function getRepoFromLink(href) {
    var m = href.match(/github\.com\/([^/]+\/[^/]+?)(?:\/|$|\?)/);
    return m ? m[1].toLowerCase() : null;
  }

  function buildProjectHTML(data) {
    var features = (data.features || []).map(function(f) {
      return '<span style="display:inline-block;font-size:11px;padding:2px 8px;border-radius:4px;background:#f0f4ff;color:#1a73e8;margin:2px 4px 2px 0">' + f + '</span>';
    }).join('');
    var langColor = { Python:"#3572A5", TypeScript:"#3178c6", Go:"#00ADD8", JavaScript:"#f1e05a", Rust:"#dea584" }[data.lang] || "#ccc";
    return [
      '<div style="padding:14px 16px">',
        '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">',
          '<span style="font-size:15px;font-weight:700;color:#1a1a1a">' + data.name + '</span>',
          '<span style="font-size:11px;color:#8b5e00;font-weight:600">★ ' + data.stars + '</span>',
        '</div>',
        '<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">',
          '<span style="display:inline-flex;align-items:center;gap:3px;font-size:11px;color:#666">',
            '<span style="width:8px;height:8px;border-radius:50%;display:inline-block;background:' + langColor + '"></span>' + data.lang +
          '</span>',
          '<span style="font-size:11px;color:#888">·</span>',
          '<span style="font-size:11px;color:#666">' + data.license + '</span>',
          '<span style="font-size:11px;color:#888">·</span>',
          '<span style="font-size:11px;color:#43a047">' + data.update + '</span>',
        '</div>',
        '<p style="font-size:12px;color:#555;line-height:1.6;margin:0 0 10px 0">' + data.desc + '</p>',
        '<div style="margin-top:6px">' + features + '</div>',
      '</div>'
    ].join('');
  }

  // ── 股票 tooltip HTML（含专业阶梯图）──
  function buildStockHTML(name, code, price, change) {
    var changeNum = parseFloat(change);
    if (isNaN(changeNum)) changeNum = 0;
    var priceNum = parseFloat(price);
    if (isNaN(priceNum)) priceNum = 0;
    var isUp = changeNum >= 0;
    var color = isUp ? '#e53935' : '#43a047';
    var arrow = isUp ? '▲' : '▼';

    // 确定性伪随机种子（基于 code+name，保证同一标的每次悬停数据一致）
    var seed = 0;
    var seedStr = (code || '') + (name || '');
    for (var i = 0; i < seedStr.length; i++) seed += seedStr.charCodeAt(i);
    function rnd() { seed = (seed * 9301 + 49297) % 233280; return seed / 233280; }

    // 昨收价（涨跌幅相对昨收）
    var prevClose = priceNum > 0 ? priceNum / (1 + changeNum / 100) : 100;

    // 生成 30 个日内点位（09:30 ~ 15:00）
    var n = 30;
    var data = [];
    var open = prevClose * (1 + (rnd() - 0.5) * 0.006);
    for (var i = 0; i < n; i++) {
      var progress = i / (n - 1);
      var trendVal = open + (priceNum - open) * progress;
      var noise = (rnd() - 0.5) * priceNum * 0.005;
      data.push(trendVal + noise);
    }
    data[0] = open;
    data[n - 1] = priceNum;

    var high = Math.max.apply(null, data);
    var low = Math.min.apply(null, data);
    var vol = (rnd() * 8 + 1).toFixed(2);

    // === 构建阶梯图 SVG (280x120) ===
    var W = 280, H = 120;
    var padL = 44, padR = 8, padT = 10, padB = 20;
    var cw = W - padL - padR;
    var ch = H - padT - padB;

    var allVals = data.concat([prevClose]);
    var dMin = Math.min.apply(null, allVals);
    var dMax = Math.max.apply(null, allVals);
    var dRange = (dMax - dMin) || 1;
    var yMin = dMin - dRange * 0.1;
    var yMax = dMax + dRange * 0.1;
    var yRange = (yMax - yMin) || 1;

    function xPos(i) { return padL + (i / (n - 1)) * cw; }
    function yPos(v) { return padT + (1 - (v - yMin) / yRange) * ch; }

    // step-after 路径: M x0,y0 L x1,y0 L x1,y1 L x2,y1 L x2,y2 ...
    var stepPath = 'M' + xPos(0).toFixed(1) + ',' + yPos(data[0]).toFixed(1);
    for (var i = 1; i < n; i++) {
      stepPath += ' L' + xPos(i).toFixed(1) + ',' + yPos(data[i - 1]).toFixed(1);
      stepPath += ' L' + xPos(i).toFixed(1) + ',' + yPos(data[i]).toFixed(1);
    }

    // 区域填充路径（阶梯 + 底部封闭）
    var bottomY = padT + ch;
    var areaPath = stepPath + ' L' + xPos(n - 1).toFixed(1) + ',' + bottomY.toFixed(1) +
                   ' L' + xPos(0).toFixed(1) + ',' + bottomY.toFixed(1) + ' Z';

    // 网格线 + Y 轴标签（4 等分）
    var gridHtml = '';
    var ySteps = 4;
    for (var g = 0; g <= ySteps; g++) {
      var gy = padT + g / ySteps * ch;
      var gval = yMax - g / ySteps * yRange;
      gridHtml += '<line x1="' + padL + '" y1="' + gy.toFixed(1) + '" x2="' + (W - padR) + '" y2="' + gy.toFixed(1) + '" stroke="#2a2a2a" stroke-width="0.5"/>';
      var lbl = gval >= 10000 ? (gval / 1000).toFixed(1) + 'k' : (gval >= 100 ? gval.toFixed(0) : gval.toFixed(2));
      gridHtml += '<text x="' + (padL - 4) + '" y="' + (gy + 3).toFixed(1) + '" text-anchor="end" font-size="8.5" fill="#777" font-family="monospace">' + lbl + '</text>';
    }

    // X 轴时间标签（09:30 / 11:30 / 15:00）
    var xLabels = [{ p: 0, t: '09:30' }, { p: 0.5, t: '11:30' }, { p: 1, t: '15:00' }];
    var xHtml = '';
    xLabels.forEach(function (xl) {
      var px = padL + xl.p * cw;
      xHtml += '<text x="' + px.toFixed(1) + '" y="' + (H - 5) + '" text-anchor="middle" font-size="8.5" fill="#777" font-family="monospace">' + xl.t + '</text>';
    });

    // 昨收参考线（虚线）
    var prevY = yPos(prevClose);
    var refHtml = '<line x1="' + padL + '" y1="' + prevY.toFixed(1) + '" x2="' + (W - padR) + '" y2="' + prevY.toFixed(1) + '" stroke="#555" stroke-width="0.5" stroke-dasharray="3,2"/>';

    var gid = 'sg' + Math.abs(seed % 100000);

    var chartSvg =
      '<svg width="' + W + '" height="' + H + '" viewBox="0 0 ' + W + ' ' + H + '" xmlns="http://www.w3.org/2000/svg" style="display:block;border-radius:6px">' +
      '<rect width="' + W + '" height="' + H + '" fill="#1a1a1a"/>' +
      '<defs><linearGradient id="' + gid + '" x1="0" y1="0" x2="0" y2="1">' +
        '<stop offset="0%" stop-color="' + color + '" stop-opacity="0.4"/>' +
        '<stop offset="100%" stop-color="' + color + '" stop-opacity="0.02"/>' +
      '</linearGradient></defs>' +
      gridHtml +
      refHtml +
      '<path d="' + areaPath + '" fill="url(#' + gid + ')"/>' +
      '<path d="' + stepPath + '" fill="none" stroke="' + color + '" stroke-width="1.5" stroke-linejoin="miter" stroke-linecap="butt"/>' +
      '<circle cx="' + xPos(n - 1).toFixed(1) + '" cy="' + yPos(data[n - 1]).toFixed(1) + '" r="2.5" fill="' + color + '"/>' +
      '<circle cx="' + xPos(n - 1).toFixed(1) + '" cy="' + yPos(data[n - 1]).toFixed(1) + '" r="5" fill="none" stroke="' + color + '" stroke-width="0.8" opacity="0.4"/>' +
      xHtml +
      '</svg>';

    // 数字格式化
    function fmt(v) {
      if (v >= 10000) return v.toFixed(0);
      return v.toFixed(2);
    }
    var priceDisp = fmt(priceNum);

    // OHLC + 成交额
    var ohlcHtml =
      '<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:2px;font-size:10px;margin-top:8px">' +
        '<div style="text-align:center"><div style="color:#999;margin-bottom:2px">开盘</div><div style="font-weight:600;color:#333">' + fmt(open) + '</div></div>' +
        '<div style="text-align:center"><div style="color:#999;margin-bottom:2px">最高</div><div style="font-weight:600;color:#e53935">' + fmt(high) + '</div></div>' +
        '<div style="text-align:center"><div style="color:#999;margin-bottom:2px">最低</div><div style="font-weight:600;color:#43a047">' + fmt(low) + '</div></div>' +
        '<div style="text-align:center"><div style="color:#999;margin-bottom:2px">收盘</div><div style="font-weight:600;color:' + color + '">' + fmt(priceNum) + '</div></div>' +
        '<div style="text-align:center"><div style="color:#999;margin-bottom:2px">成交额</div><div style="font-weight:600;color:#333">' + vol + '亿</div></div>' +
      '</div>';

    return [
      '<div style="padding:12px 14px;width:280px;background:#fff;border-radius:12px">',
        '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px">',
          '<span style="font-size:14px;font-weight:700;color:#1a1a1a">' + name + '</span>',
          '<span style="font-size:11px;color:#999;font-family:monospace">' + code + '</span>',
        '</div>',
        '<div style="display:flex;align-items:baseline;justify-content:space-between;margin-bottom:8px">',
          '<span style="font-size:22px;font-weight:800;color:' + color + ';font-family:monospace">' + priceDisp + '</span>',
          '<span style="font-size:13px;color:' + color + ';font-weight:600">' + arrow + ' ' + Math.abs(changeNum).toFixed(2) + '%</span>',
        '</div>',
        chartSvg,
        ohlcHtml,
      '</div>'
    ].join('');
  }

  // ── 汇率 tooltip HTML ──
  function buildRateHTML(currency, rate, change) {
    var isUp = parseFloat(change) >= 0;
    var color = isUp ? '#e53935' : '#43a047';
    return [
      '<div style="padding:10px 14px;min-width:180px">',
        '<div style="font-size:14px;font-weight:700;margin-bottom:4px">' + currency + '</div>',
        '<div style="display:flex;align-items:center;justify-content:space-between">',
          '<span style="font-size:18px;font-weight:600">' + rate + '</span>',
          '<span style="font-size:12px;color:' + color + '">' + (isUp ? '▲' : '▼') + ' ' + Math.abs(parseFloat(change)).toFixed(2) + '%</span>',
        '</div>',
      '</div>'
    ].join('');
  }

  // ── 扫描并绑定 ──
  function bindHover() {
    // 项目卡片
    var projectCards = document.querySelectorAll('.agent-card, .ai-card, .project-card, .sv-topic-card, .sv-project-card');
    projectCards.forEach(function(card) {
      if (card.dataset.hoverBound) return;
      card.dataset.hoverBound = '1';
      card.addEventListener('mouseenter', function(e) {
        clearTimeout(hoverTimer);
        hoverTimer = setTimeout(function() {
          var link = card.querySelector('a[href*="github.com"]');
          if (!link) return;
          var repo = getRepoFromLink(link.href);
          if (!repo) return;
          var data = PROJECT_DETAILS[repo];
          if (!data) return;
          showTooltip(buildProjectHTML(data), e.clientX, e.clientY);
        }, 800);
      });
      card.addEventListener('mouseleave', function() {
        clearTimeout(hoverTimer);
        hideTooltip();
      });
      card.addEventListener('mousemove', function(e) {
        if (tooltip && tooltip.style.opacity === '1') {
          var tx = e.clientX + 16;
          var ty = e.clientY + 16;
          var rect = tooltip.getBoundingClientRect();
          if (tx + rect.width > window.innerWidth - 8) tx = e.clientX - rect.width - 16;
          if (ty + rect.height > window.innerHeight - 8) ty = window.innerHeight - rect.height - 8;
          tooltip.style.left = tx + 'px';
          tooltip.style.top = ty + 'px';
        }
      });
    });

    // 股票/金融项目
    var stockItems = document.querySelectorAll('[data-stock], .stock-item, .finance-item');
    stockItems.forEach(function(item) {
      if (item.dataset.hoverBound) return;
      item.dataset.hoverBound = '1';
      item.addEventListener('mouseenter', function(e) {
        clearTimeout(hoverTimer);
        hoverTimer = setTimeout(function() {
          var name = item.getAttribute('data-stock-name') || item.textContent.trim().substring(0, 10);
          var code = item.getAttribute('data-stock-code') || '';
          var price = item.getAttribute('data-stock-price') || '--';
          var change = item.getAttribute('data-stock-change') || '0';
          showTooltip(buildStockHTML(name, code, price, change), e.clientX, e.clientY);
        }, 800);
      });
      item.addEventListener('mouseleave', function() {
        clearTimeout(hoverTimer);
        hideTooltip();
      });
    });

    // 汇率项目
    var rateItems = document.querySelectorAll('[data-rate]');
    rateItems.forEach(function(item) {
      if (item.dataset.hoverBound) return;
      item.dataset.hoverBound = '1';
      item.addEventListener('mouseenter', function(e) {
        clearTimeout(hoverTimer);
        hoverTimer = setTimeout(function() {
          var currency = item.getAttribute('data-rate') || '';
          var rate = item.getAttribute('data-rate-value') || '--';
          var change = item.getAttribute('data-rate-change') || '0';
          showTooltip(buildRateHTML(currency, rate, change), e.clientX, e.clientY);
        }, 800);
      });
      item.addEventListener('mouseleave', function() {
        clearTimeout(hoverTimer);
        hideTooltip();
      });
    });
  }

  // Run on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bindHover);
  } else {
    bindHover();
  }
  // Re-scan after dynamic content loads
  setTimeout(bindHover, 2000);
  setTimeout(bindHover, 5000);
})();
