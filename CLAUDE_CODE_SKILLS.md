# Claude Code 技能参考

> 来源: `C:\Users\Chris\.claude\plugins\marketplaces\claude-plugins-official\plugins\`
> 整合时间: 2026-06-22

---

## 高价值技能详解

### 1. project-artifact — 项目状态页面生成器

**用途**: 生成多标签HTML项目状态页面, 适合跨多工作流的大型项目.

**核心流程**:
1. 解析项目配置 → 收集源材料(gh pr list / git log)
2. 选择标签页: Overview / Workstreams / Attention / Background / Plan / Risks / Decisions
3. 从 template.html 生成自包含HTML
4. 用 Artifact 工具发布到 claude.ai
5. 支持刷新: 重新收集 → 增量更新 → 重新部署同一URL

**关键特性**:
- 状态块嵌入: `<script type="application/json" id="artifact-state">` 用于增量diff
- 严格CSP: 所有CSS/JS内联, 无外部依赖
- 状态药丸: done / in progress / next / blocked / ⚠ caveat

### 2. skill-creator — 技能创建与评估

**用途**: 创建新技能、改进现有技能、运行评估测试.

**核心流程**:
1. 捕获意图 → 访谈研究 → 编写SKILL.md
2. 创建测试用例 → 并行运行(有技能 vs 无技能) → 评估结果
3. 生成基准测试 → 启动查看器 → 读取反馈 → 改进技能
4. 描述优化: 生成20个触发评估查询 → 运行优化循环 → 应用最佳描述

**技能结构**:
```
skill-name/
├── SKILL.md (必需: YAML frontmatter + Markdown)
├── scripts/    - 可执行代码
├── references/ - 按需加载的文档
└── assets/     - 模板/图标/字体
```

**渐进式披露**: 元数据(始终在上下文) → SKILL.md主体(触发时加载) → 捆绑资源(按需)

### 3. session-report — 会话使用报告

**用途**: 生成Claude Code使用情况的HTML报告.

**流程**:
1. 运行 `analyze-sessions.mjs` 分析最近7天数据
2. 读取JSON: overall / by_project / by_subagent_type / by_skill / cache_breaks / top_prompts
3. 复制template.html → 填充数据 → 添加发现和优化建议

### 4. frontend-design — 前端设计指导

**核心理念**: 作为小型工作室的设计主管, 给每个客户无法被混淆的视觉身份.

**设计原则**:
- Hero是论点: 用最具特征的事物开场
- 字体承载个性: 刻意搭配展示字体和正文字体
- 结构即信息: 编号/分隔线/标签应编码真实内容
- 动效刻意使用: 编排的时刻比分散效果更有力
- 复杂度匹配愿景: 极简方向需要精度, 极繁方向需要执行力

**AI默认风格(需避免)**:
1. 暖奶油背景(#F4F1EA) + 高对比衬线 + 赤陶强调色
2. 近黑背景 + 酸绿/朱红强调色
3. 报纸风格 + 细线 + 零圆角 + 密集列

**流程**: 头脑风暴 → 探索 → 计划 → 批评 → 构建 → 再批评

### 5. math-olympiad — 数学竞赛解题器

**用途**: 解IMO/Putnam/USAMO/AIME竞赛题, 带对抗式验证.

**五步流程**:
1. **解释检查**: 列出2-3种可能的解释, 选最难的那个
2. **并行生成**: 8-12个agent并行, 每个内部迭代(解决→改进→验证→修正)
3. **清理解法**: 剥离思维过程, 只保留干净证明(防止验证者偏见)
4. **对抗验证**: 新鲜上下文agent攻击证明, 使用特定失败模式检查
5. **排名投票**: 4票确认, 2票反驳(非对称阈值)

**关键检查模式**:
- #4: 定理特化到著名对象是否证明开放问题?
- #18: 中间恒等式代入"剩余缺口"是否同义反复?
- #40: "一行引理"提取一般形式, 找2×2反例
- #5: 每个调用的定理从头重新检查假设

**校准弃权**: 3次修正失败 → 停下承认"无自信解", 附带部分结果

### 6. playground — 交互式HTML探索器

**用途**: 创建自包含HTML交互工具, 用户调整控件 → 实时预览 → 复制生成的提示词.

**模板类型**:
- design-playground: 视觉设计决策
- data-explorer: 数据和查询构建
- concept-map: 学习和探索
- document-critique: 文档审查
- diff-review: 代码审查
- code-map: 代码库架构

**核心要求**: 单HTML文件 / 实时预览 / 提示词输出 / 复制按钮 / 预设 / 暗色主题

---

## 插件开发技能 (plugin-dev)

### skill-development
技能开发完整流程: 捕获意图 → 访谈 → 编写SKILL.md → 测试 → 评估 → 迭代

### plugin-structure
插件结构规范:
- manifest.json: 插件元数据
- skills/: 技能目录
- commands/: 命令目录
- agents/: 代理目录
- hooks/: 钩子目录

### plugin-settings
插件设置系统: 解析技术 / 真实世界示例 / 设置命令创建

### mcp-integration
MCP集成: 认证( OAuth/API Key/Bearer ) / 服务器类型(stdio/SSE/HTTP) / 工具使用

### hook-development
Hook开发: 模式(PreToolUse/PostToolUse/Notification) / 迁移 / 高级用法

### command-development
命令开发: frontmatter参考 / 文档模式 / 交互命令 / 测试策略

### agent-development
Agent开发: 系统提示词设计 / 触发示例 / 创建系统提示词

---

## MCP 服务器开发 (mcp-server-dev)

### build-mcp-server
MCP服务器构建:
- 认证: OAuth 2.1 / API Key / Bearer Token
- 部署: Cloudflare Workers / 本地stdio / 远程HTTP
- 工具设计: 输入验证 / 错误处理 / 资源和提示
- 服务器能力: 工具 / 资源 / 提示 / 日志 / 完成

### build-mcpb
MCPB包构建:
- Manifest schema: name / version / description / tools / resources
- 本地安全: 路径遍历 / 注入 / 权限

### build-mcp-app
MCP应用构建:
- 滥用防护: 速率限制 / 输入验证 / 输出过滤
- SDK消息: 工具调用 / 资源读取 / 提示渲染

---

## PR 审查工具包 (pr-review-toolkit)

6个专业Agent:

| Agent | 职责 |
|-------|------|
| code-reviewer | 代码审查(质量/安全/性能) |
| code-simplifier | 代码简化(可读性/维护性) |
| comment-analyzer | 评论分析(意图/情绪/行动项) |
| pr-test-analyzer | 测试分析(覆盖率/质量/缺失) |
| silent-failure-hunter | 静默失败猎手(边界/异常/竞态) |
| type-design-analyzer | 类型设计分析(接口/泛型/类型安全) |

---

## 其他技能

### ralph-loop
持续任务执行循环: 接收任务 → 执行 → 检查 → 继续/停止

### hookify (writing-rules)
规则编写: 将自然语言规则转换为可执行的Hook

### claude-md-management (claude-md-improver)
CLAUDE.md改进: 分析现有记忆文件 → 优化结构 → 合并重复 → 补充缺失

### claude-code-setup (claude-automation-recommender)
Claude Code自动化推荐: 分析工作流 → 推荐自动化配置

### cwc-makers
- m5-onboard: M5开发板入门
- cardputer-buddy: Cardputer伴侣
