# 本地 Agent 资源总索引

> 搜索时间: 2026-06-22
> 搜索范围: Claude Code / Continue / TRAE 内置 / VS Code 扩展

---

## 一、Claude Code 记忆库 (16 个文件)

路径: `C:\Users\Chris\.claude\projects\d--Code-claude-code\memory\`

| 文件 | 类型 | 描述 |
|------|------|------|
| `MEMORY.md` | 索引 | 记忆库总索引 |
| `user_profile.md` | 用户画像 | Chris 的完整画像 — 职高→二本→211硕士证道路 |
| `project_chris_journey.md` | 项目 | 考研证道路线图,数学补全5阶段,时间线2026-2029 |
| `project_trae_competition.md` | 项目 | TRAE AI 创造力大赛信息,奖金百万,07.15截止 |
| `project_opencrawler.md` | 项目 | OpenCrawler 统一事件监视器开发记录 |
| `project_novel_mc_witch.md` | 项目 | MC灾厄魔女小说写作协作流程 |
| `project_time_anchor.md` | 项目 | 时间锚石策略 — 今日之我增援未来之我 |
| `monetization_paths.md` | 项目 | 5条变现路径完整方案 |
| `pdf_ocr_workflow.md` | 项目 | PDF教材OCR工作流,数学公式转LaTeX |
| `mirror_session_context.md` | 项目 | 本我镜像最后对话状态 |
| `reference_anime_db.md` | 参考 | 4K番剧资源库,689条动漫,SQLite |
| `feedback_china_network.md` | 反馈 | 中国网络环境规则 — 外网下载策略 |
| `feedback_no_hallucination.md` | 反馈 | 严禁AI幻觉 — 不确定就搜索 |
| `feedback_stop_looping.md` | 反馈 | 死循环熔断规则 — 5次自审8次停 |
| `feedback_nearby_download.md` | 反馈 | 就近下载规则 — 国内镜像优先 |
| `feedback_no_sycophancy.md` | 反馈 | 严禁谄媚 — 不奉承不美化 |
| `feedback_design_workflow.md` | 反馈 | 设计偏好 — 黑白简约,卡片混合布局 |

**整合文件**: 见 `CLAUDE_CODE_MEMORY.md`

---

## 二、Claude Code 插件技能 (15 个插件, 23 个技能)

路径: `C:\Users\Chris\.claude\plugins\marketplaces\claude-plugins-official\plugins\`

### 高价值技能

| 插件 | 技能 | 描述 |
|------|------|------|
| `project-artifact` | project-artifact | 生成项目状态页面(多标签HTML),支持刷新和增量更新 |
| `skill-creator` | skill-creator | 创建/改进/评估技能,含盲比较和描述优化 |
| `session-report` | session-report | 生成Claude Code使用报告HTML(token/缓存/子代理) |
| `frontend-design` | frontend-design | 前端设计指导 — 调色板/字体/布局的刻意选择 |
| `math-olympiad` | math-olympiad | 数学竞赛解题器(IMO/Putnam),对抗式验证 |
| `playground` | playground | 交互式HTML探索器生成器 |
| `claude-md-management` | claude-md-improver | CLAUDE.md 记忆文件改进器 |
| `claude-code-setup` | claude-automation-recommender | Claude Code 自动化推荐器 |

### 插件开发技能 (plugin-dev)

| 技能 | 描述 |
|------|------|
| `skill-development` | 技能开发完整流程 |
| `plugin-structure` | 插件结构规范(manifest/components) |
| `plugin-settings` | 插件设置系统(解析/配置) |
| `mcp-integration` | MCP 集成(认证/服务器类型) |
| `hook-development` | Hook 开发(模式/迁移/高级) |
| `command-development` | 命令开发(frontmatter/工作流) |
| `agent-development` | Agent 开发(系统提示词设计) |

### MCP 服务器开发技能 (mcp-server-dev)

| 技能 | 描述 |
|------|------|
| `build-mcp-server` | MCP 服务器构建(认证/部署/工具设计) |
| `build-mcpb` | MCPB 包构建(manifest schema/安全) |
| `build-mcp-app` | MCP 应用构建(滥用防护/SDK消息) |

### 其他插件

| 插件 | 描述 |
|------|------|
| `pr-review-toolkit` | PR 审查工具包(6个agent: code-reviewer/simplifier等) |
| `ralph-loop` | Ralph 循环(持续任务执行) |
| `hookify` | 规则编写(writing-rules) |
| `cwc-makers` | M5开发板入门/cardputer伴侣 |

**整合文件**: 见 `CLAUDE_CODE_SKILLS.md`

---

## 三、TRAE 内置技能

路径: `C:\Users\Chris\.trae-cn\builtin\`

### 工作区技能 (work/default)

| 技能 | 描述 |
|------|------|
| `TRAE-product-knowledge` | TRAE 品牌和产品知识 |
| `doc-writing-guide` | 文档写作指南(PRD/规格/技术提案) |
| `docx` | Word 文档创建/编辑/分析 |
| `html-deck` | HTML 幻灯片演示文稿创建 |
| `html-report` | HTML 报告/白皮书/仪表盘创建 |
| `pdf` | PDF 操作(提取/创建/合并/表单) |
| `pptx` | PowerPoint 演示文稿创建/编辑 |
| `xlsx` | Excel 电子表格操作 |
| `research-guide` | 研究与分析指南 |

### 代码技能 (code/default)

| 技能 | 描述 |
|------|------|
| `web-dev` | Web 开发指南 |
| `TRAE-code-review` | 代码审查 |
| `TRAE-debugger` | 调试器(含debug-server) |
| `TRAE-generate-mini-app` | 迷你应用生成器 |
| `TRAE-security-review` | 安全审查 |

### 全局技能 (global)

| 技能 | 描述 |
|------|------|
| `digital-avatar-creator` | 数字头像创建器 |
| `skill-creator` | TRAE 技能创建器 |

### 多版本技能

TRAE 为不同模型版本提供了技能变体:
- `default` / `iris` / `penelope` / `iphigenia` / `medea` / `deidamia` / `thetis` / `eurydice` / `hebe`

---

## 四、其他 Agent 资源

### Continue (VS Code 扩展)

路径: `C:\Users\Chris\.vscode\extensions\continue.continue-2.1.0-win32-x64\`

- AI 编码助手扩展,支持自定义模型和规则
- 内置 `rules.md` 规则文件
- 支持 LanceDB 向量数据库

### 已安装的其他 VS Code AI 扩展

| 扩展 | 说明 |
|------|------|
| GitHub Copilot Chat | GitHub 的 AI 编码助手 |
| OpenAI ChatGPT | OpenAI 官方扩展 |
| Hermes AI Agent | 多模型 AI 代理 |

---

## 五、Claude Code 配置

路径: `C:\Users\Chris\.claude\settings.json`

- 启用的插件: project-artifact, skill-creator, session-report, frontend-design, math-olympiad, playground, plugin-dev, mcp-server-dev, pr-review-toolkit, ralph-loop, hookify, cwc-makers, claude-md-management, claude-code-setup
- MCP 服务器配置
- 权限设置

---

## 六、关键数据资产

| 资产 | 路径 | 说明 |
|------|------|------|
| 番剧数据库 | `d:\Code\claude code\爬虫\anime_db.sqlite` | 689条4K番剧,12分类 |
| PDF OCR 脚本 | `D:\本地AI知识库\Raw\学习进度\高等数学教材\scripts\` | PDF→LaTeX 三件套 |
| 小说项目 | `D:\小说\MC灾厄魔女\` | 已超2万字,含知识库和写作系统 |
| 本地AI知识库 | `D:\本地AI知识库\` | Chris 的知识管理体系 |
