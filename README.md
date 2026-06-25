# OpenCrawler — 多源开发者情报聚合平台

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/flask-3.0+-green.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![TRAE](https://img.shields.io/badge/built%20with-TRAE%20IDE-6c5ce7.svg)](https://www.trae.ai)

将 GitHub 趋势榜、Hacker News、RSS 订阅、CVE 漏洞、短视频热门、金融数据等 **7 大数据源**统一为标准化 RESTful API + 可视化前端。开发者在 30 秒内获取任意技术领域的最新情报。

**在线 Demo**：[web-production-9832c5.up.railway.app](https://web-production-9832c5.up.railway.app)

---

## 这是干嘛的

每天打开浏览器就是十几个标签页——GitHub Trending 看项目、Hacker News 看讨论、RSS 订阅刷技术博客、CVE 盯安全漏洞、还得扫一眼股市和短视频趋势。信息源碎片化到让人烦躁。

OpenCrawler 把这些全揉到一个平台里，定时抓取、自动清洗、统一接口。一个页面看完所有技术动态，需要原文可以一键抓取翻译下载。

## 面向谁

- **独立开发者** — 追踪开源项目趋势，发现下一个值得贡献或学习的仓库
- **技术博主/内容创作者** — 30 秒找到今天的写作素材，不用自己翻十几个网站
- **安全研究员** — CVE 漏洞自动聚合，高危严重标签一目了然
- **量化/金融爱好者** — A 股指数 + 全球汇率一站式查看，悬停看阶梯趋势图
- **AI 开发者** — 25+ AI Agent 工具导航，浏览器自动化/编程助手/图像视频/LLM 平台四分类

## 我为什么写这个

我是 2026 级大一新生，职高对口高考考上来的。没有团队、没有后端经验、没有钱买服务器——就是用 TRAE IDE 一句句对话，一个文件一个文件磨出来的。

选这个方向的原因很简单：**我自己就需要它**。每天在十几个信息源之间来回跳，效率低还容易漏东西。市面上有类似工具，要么收费、要么数据源不够、要么不开源没法自己改。

于是就想：不如自己做一个。做出来了，就开源出来。有同样需求的人直接用，想改的自己 fork。

这也是我参加 **TRAE AI 创造力大赛** 的作品——一个完全没有编程背景的人，靠 AI 辅助开发能走到哪一步的答案。

## 技术栈

| 层 | 选型 | 说明 |
|---|------|------|
| **Web 框架** | Flask 3.0 | 轻量，单文件部署，够用 |
| **数据库** | SQLite (WAL 模式) | 零配置，单用户场景性能足够 |
| **调度器** | APScheduler | 后台定时抓取，30-120 分钟间隔 |
| **HTTP 客户端** | requests + curl_cffi | 标准抓取 + 反爬指纹绕过 |
| **HTML 解析** | BeautifulSoup 4 | 正文提取 + 数据清洗 |
| **前端** | Jinja2 + Vanilla JS + CSS | 无构建工具，模板渲染 + 原生动效 |
| **部署** | Railway (PaaS) | GitHub Push → 自动部署 |

## 数据源

| 源 | 抓取方式 | 更新间隔 | 说明 |
|---|---------|---------|------|
| GitHub Trending | API 抓取 | 60 min | 每日/每周趋势，多语言筛选 |
| Hacker News | API 抓取 | 30 min | Top Stories + 原文正文 |
| RSS 订阅 (13 源) | feedparser | 30 min | 少数派、36氪、阮一峰、Dev.to、ArXiv AI 等 |
| RSS 反爬 (10 源) | curl_cffi | 30 min | 量子位、知乎、IT之家、OpenAI/Anthropic/DeepSeek Blog 等 |
| CVE 漏洞 | NVD API | 120 min | 最近 7 天，按严重度排序 |
| 短视频热门 | API 抓取 | 60 min | B站/抖音/快手/小红书 4 平台趋势 |
| 金融数据 | API 抓取 | 1440 min | A股指数 + 全球汇率 |

## 功能特性

- **RESTful API** — 免费层 20 次/天，支持按源/标签/时间筛选，JSON 格式
- **原文抓取+翻译** — 输入 URL 自动清洗正文，英文内容一键翻译中文，支持 TXT/MD 下载
- **图片代理** — 绕过 CDN 防盗链，B站/快手/小红书图片正常显示
- **GitHub 风格复刻** — 1:1 照搬 GitHub.com 项目卡片排版，100+ 开源项目导航
- **全站悬停 Tooltip** — 悬停 0.8s 弹出项目详情/股票阶梯图/汇率信息
- **金融阶梯图** — SVG step-after 图表，OHLC 数据 + 渐变填充 + 昨收参考线
- **AI 助手浮窗** — 全站右下角悬浮对话入口，可对接 OpenAI 兼容 API
- **AI 工作流引擎** — 12 个预设工作流，localStorage 持久化配置
- **AI Agent 部署指南** — 25+ 开源 Agent 工具导航，全部分类+项目卡片
- **网络营销导航** — 8 大电商平台 + 6 跨境市场 + 6 个开源营销工具
- **软件站** — 4 款明星软件深度介绍 + 16 款工具分类导航
- **移动端响应式** — 双断点（768px/480px），汉堡菜单，触屏适配

## API 使用

```bash
# 获取聚合趋势数据
curl "https://your-instance/api/v1/trending?source=github_trending&limit=10" \
  -H "Authorization: Bearer YOUR_API_KEY"

# 搜索所有数据源
curl "https://your-instance/api/v1/search?q=AI&limit=20" \
  -H "Authorization: Bearer YOUR_API_KEY"

# 抓取原文并清洗
curl "https://your-instance/api/fetch?url=https://example.com/article"

# 下载原文为 TXT（自动翻译英文内容）
curl "https://your-instance/api/download?url=https://example.com/article&format=txt"
```

## 快速开始

```bash
# 1. 克隆
git clone https://github.com/Chris1314520/opencrawler.git
cd opencrawler

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置（可选，默认配置即可运行）
cp config.yaml config.local.yaml
# 编辑 config.local.yaml：设置代理、调整抓取间隔、配置 AI API Key 等

# 4. 启动
python server.py

# 访问 http://localhost:5000
# 管理面板 http://localhost:5000/admin/login
```

## 项目结构

```
opencrawler/
├── server.py              # Flask 主入口 + API 路由 + Monitor
├── monitor.py             # 独立监视器入口（可选）
├── storage.py             # SQLite 存储层（批量写入 + 线程安全）
├── notifier.py            # 通知模块
├── config.yaml            # 抓取配置（数据源/间隔/API Key）
├── requirements.txt       # Python 依赖
├── fetchers/              # 抓取器模块
│   ├── __init__.py        # BaseFetcher + HTTP 重试/连接池
│   ├── github_trending.py # GitHub 趋势榜
│   ├── hackernews.py      # Hacker News
│   ├── rss_feeds.py       # RSS 标准抓取
│   ├── curl_cffi_rss.py   # RSS 反爬抓取（TLS 指纹）
│   ├── nvd_cve.py         # CVE 漏洞数据
│   ├── shortvideo_trending.py # 短视频热门
│   └── finance_data.py    # 金融数据
├── templates/             # Jinja2 页面模板（19 个）
│   ├── landing.html       # 首页
│   ├── dashboard.html     # 情报面板
│   ├── github.html        # GitHub 项目导航（104 个项目）
│   ├── software.html      # 软件站
│   ├── agents.html        # AI Agent 导航
│   ├── agent_deploy.html  # Agent 部署指南
│   ├── ai_workflow.html   # AI 工作流引擎
│   ├── finance.html       # 金融数据
│   ├── platforms.html     # 平台数据
│   ├── marketing.html     # 网络营销导航
│   ├── script_market.html # 脚本市场
│   ├── console.html       # 管理控制台
│   └── ...
├── static/                # 前端静态资源
│   ├── hover-tooltip.js   # 悬停详情 + SVG 图表（498 行）
│   ├── gh-avatars.js      # GitHub 头像预缓存
│   ├── ai-assistant.js    # AI 助手浮窗
│   ├── ai-assistant.css   # AI 助手样式
│   ├── product.css        # 产品页样式
│   ├── animations.css     # 动效系统
│   ├── animations.js      # 动效逻辑
│   └── logos/             # 平台 SVG 图标
└── data/                  # 本地数据库目录
```

## 部署

### Railway（推荐）

GitHub Push → Railway 自动部署，零配置：

1. 在 [Railway](https://railway.app) 用 GitHub 登录
2. 点击 "New Project → Deploy from GitHub repo"
3. 选择 `Chris1314520/opencrawler`
4. Railway 自动识别 Python 项目并部署

`railway.json` 和 `Procfile` 已预配置。

### 其他方式

支持任何能跑 Python + Flask 的环境：VPS、Docker、Render、Fly.io 等。只需：

```bash
pip install -r requirements.txt
python server.py --port 5000
```

## 致谢

- [TRAE IDE](https://www.trae.ai) — 本项目全部代码通过 TRAE 辅助生成
- 所有 RSS 内容源和 API 数据提供方
- 开源社区中每一个被导航收录的项目

## License

MIT — 随便用，随便改，随便部署。标注出处更好，不标注也行。
