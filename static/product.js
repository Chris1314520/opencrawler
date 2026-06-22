// Demo page — real-time data via Free API Key
const DEMO_KEY = document.querySelector('meta[name="demo-key"]')?.content || '';

let currentSource = '';
let currentData = [];

function esc(s) {
    const d = document.createElement('div');
    d.textContent = s || '';
    return d.innerHTML;
}

function escAttr(s) {
    return String(s || '').replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/'/g, '&#39;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function truncate(s, n) {
    if (!s) return '';
    s = s.replace(/<[^>]*>/g, '').replace(/\s+/g, ' ');
    return s.length > n ? s.slice(0, n) + '...' : s;
}

function getSaved() {
    try { return JSON.parse(localStorage.getItem('opencrawler_saved') || '[]'); }
    catch(e) { return []; }
}

function isItemSaved(item) {
    return getSaved().some(s => s.url === item.url);
}

function saveItem(idx) {
    const item = currentData[idx];
    if (!item) return;
    const saved = getSaved();
    if (isItemSaved(item)) return;
    saved.push({
        title: item.title,
        url: item.url,
        description: item.description,
        source: item.source,
        source_label: item.source_label,
        tags: item.tags,
        extra: item.extra,
        saved_at: new Date().toISOString().slice(0, 19).replace('T', ' ')
    });
    localStorage.setItem('opencrawler_saved', JSON.stringify(saved));
    renderItems(currentData);
}

function unsaveItem(url) {
    const saved = getSaved().filter(s => s.url !== url);
    localStorage.setItem('opencrawler_saved', JSON.stringify(saved));
    renderItems(currentData);
}

function renderItems(items) {
    const container = document.getElementById('demo-items');
    if (!items || items.length === 0) {
        container.innerHTML = '<p style="color: var(--muted);">暂无数据</p>';
        return;
    }
    container.innerHTML = items.map((item, idx) => {
        const tags = (item.tags || '').split(',').filter(t => t.trim()).map(t => `<span class="item-tag">${esc(t.trim())}</span>`).join('');
        const extra = item.extra || {};
        let extraStr = '';
        if (extra.cvss) extraStr += `CVSS: ${esc(extra.cvss)} `;
        if (extra.stars_today) extraStr += `⭐ ${extra.stars_today} today `;
        if (extra.feed_name) extraStr += `来源: ${esc(extra.feed_name)} `;
        const saved = isItemSaved(item);
        const starIcon = saved ? '★' : '☆';
        const starTitle = saved ? '取消收藏' : '收藏';
        const starClass = saved ? 'save-btn saved' : 'save-btn';
        const onclick = saved
            ? `onclick="event.preventDefault();unsaveItem('${escAttr(item.url)}')"`
            : `onclick="event.preventDefault();saveItem(${idx})"`;
        return `
        <div class="item-card">
            <div class="item-title">
                <a href="${escAttr(item.url)}" target="_blank" rel="noopener">${esc(item.title)}</a>
                <button class="${starClass}" title="${starTitle}" ${onclick}>${starIcon}</button>
            </div>
            <div class="item-desc">${esc(truncate(item.description, 200))}</div>
            <div class="item-meta">
                <span>${esc(item.source_label || item.source)}</span>
                ${tags}
                ${extraStr}
            </div>
        </div>`;
    }).join('');
}

async function loadData() {
    const container = document.getElementById('demo-items');
    container.innerHTML = '<p style="color: var(--muted);">加载中...</p>';

    const params = new URLSearchParams();
    params.set('limit', '20');
    params.set('api_key', DEMO_KEY);
    if (currentSource) params.set('source', currentSource);

    try {
        const resp = await fetch(`/api/v1/trending?${params}`);
        const data = await resp.json();

        if (resp.status === 429) {
            container.innerHTML = `<p style="color: var(--red);">今日免费配额已用完，明天0:00重置。如需更多调用请 <a href="/pricing">升级 Pro</a>。</p>`;
            return;
        }
        if (resp.status !== 200) {
            container.innerHTML = `<p style="color: var(--red);">错误: ${esc(data.error || 'unknown')}</p>`;
            return;
        }

        currentData = data.items || [];
        renderItems(currentData);

        document.getElementById('quota-info').textContent =
            `今日已用: ${data.quota.used_today} / ${data.quota.daily_limit} 次 | 套餐: ${data.tier}`;

    } catch (e) {
        container.innerHTML = `<p style="color: var(--red);">请求失败: ${esc(e.message)}</p>`;
    }
}

function loadSavedData() {
    const saved = getSaved();
    currentData = saved;
    renderItems(saved);
    document.getElementById('quota-info').textContent = `已保存 ${saved.length} 条记录（本地存储）`;
}

function exportJSON() {
    const items = currentSource === '__saved__' ? getSaved() : currentData;
    if (items.length === 0) { alert('没有可导出的数据'); return; }
    const blob = new Blob([JSON.stringify(items, null, 2)], {type: 'application/json'});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'opencrawler_export_' + new Date().toISOString().slice(0,10) + '.json';
    a.click();
    URL.revokeObjectURL(a.href);
}

// Source filter
document.getElementById('source-tags').addEventListener('click', function(e) {
    if (e.target.id === 'export-btn') {
        exportJSON();
        return;
    }
    // 树状结构由 demo.html 内联 JS 处理,这里只处理旧版 source-tag
    if (e.target.classList.contains('source-tag')) {
        this.querySelectorAll('.source-tag').forEach(b => b.classList.remove('active'));
        e.target.classList.add('active');
        currentSource = e.target.dataset.source;
        if (currentSource === '__saved__') {
            loadSavedData();
        } else {
            loadData();
        }
    }
});

// Load on page ready
loadData();
