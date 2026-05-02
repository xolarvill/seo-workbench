# SEO 三件套协同工作流指南

三条开源项目（SuperSEO、SEO Machine、Claude SEO）覆盖 SEO 全链路：**战略→生产→质检→审计**。本指南记录如何将它们串联成一套可复现的工作流。

---

## 工具速览

| 工具 | 定位 | 一句话 |
|------|------|--------|
| **SuperSEO** | 内容战略顾问 | 给关键词或URL，Agent 自行读 SERP、分析竞品、输出策略 |
| **SEO Machine** | 内容生产流水线 | 研究→写作→优化→发布，一竿子到底 |
| **Claude SEO** | 全站技术审计 | 15 代理并行，诊断技术/内容/性能/结构化数据 |

---

## 第一阶段：战略规划（SuperSEO）

**目标：** 搞清楚写什么、按什么顺序写、每篇怎么写。

### 步骤 1：关键词深潜

```
/superseo:keyword-deep-dive
```

输入目标关键词。Agent 会：
- 读取 Google SERP 前10
- 判断搜索意图（信息型/商业型/交易型/导航型）
- 评估零点击风险、AI Overview 影响
- 读取前3名竞品的完整页面
- 输出 90 天排名计划

**产出：** 关键词作战地图——这个词有没有机会、要多久、需要什么强度的内容。

### 步骤 2：话题集群规划

```
/superseo:topic-cluster-planning
```

输入种子话题。Agent 会：
- 扫描该领域的核心话题和子话题
- 识别支柱页（Hub）和支撑文章（Spoke）
- 设计内部链接权重矩阵
- 输出发布顺序建议

**产出：** Hub & Spoke 内容架构 + 发布路线图。

### 步骤 3：内容简报

```
/superseo:content-brief
```

为每篇待写文章生成简报。Agent 会：
- 读取目标关键词的 SERP 前10
- 分类搜索意图
- 绘制内容缺口：竞品覆盖了哪些你不具备的角度
- 给出结构建议 + 页面要素清单

**产出：** 写手可以直接开写的简报（包含标题建议、大纲、必备要点、推荐字数）。

---

## 第二阶段：内容生产（SEO Machine）

**目标：** 把简报变成一篇在 WordPress 上发出去的、SEO 优化完毕的文章。

### 步骤 4：关键词研究

```
/research [主题]
```

SEO Machine 会：
- 分析前10竞品的内容长度、标题模式、结构
- 识别内容缺口
- 生成研究简报，为写作做准备

### 步骤 5：写文章

```
/write [主题]
```

自动触发 4 个代理：
- **SEO 优化器**：关键词密度、标题层级、摘要优化
- **元数据创建器**：生成5个标题变体 + 5个描述变体
- **内部链接器**：推荐3-5条精确内链，含锚文本和放置位置
- **关键词映射器**：分布热力图、LSI 覆盖检查、蚕食风险预警

**注意：** 写作前确保 `context/brand-voice.md` 和 `context/writing-examples.md` 已配置好品牌语调。

### 步骤 6：发布前优化

```
/optimize [文件路径]
```

最终 SEO 检查：
- 评分 0-100，不达标返回修改
- 修复优先级排序（高/中/低）
- 确认元数据、标题层级、图片Alt文本

### 步骤 7：发布到 WordPress

```
/publish-draft [文件路径]
```

通过 WordPress REST API 发布，自动携带 Yoast SEO 元数据。

**前置条件：** `wp-config/local.json` 中配置好站点 URL 和应用密码。

---

## 第三阶段：质量审查（SuperSEO）

**目标：** 文章发出去了，检查它能不能排上去。

### 步骤 8：页面审计

```
/superseo:page-audit
```

输入已发布页面的 URL。Agent 会从7个维度诊断：
1. 内容质量
2. 技术 SEO
3. E-E-A-T 信号
4. 内容结构
5. 内部链接
6. Schema 标记
7. 竞争定位（对标前3）

### 步骤 9：语义缺口分析

```
/superseo:semantic-gap-analysis
```

如果你的页面排在 4-10 名进不去前3——Agent 对比你的页面和前3名竞品，用 EAV（实体-属性-值）三元组思维输出：
- 你缺少了哪些实体
- 你缺少了哪些子话题
- 你缺少了哪些语义关系

### 步骤 10：内容改进

```
/superseo:improve-content
```

针对审计和缺口分析的结果重写薄弱段落。运用反 AI 味规则集：
- 禁用空洞过渡词（"In today's digital landscape"、"It is important to note that"）
- 禁用模糊夸大语（"comprehensive"、"cutting-edge"、"unparalleled"）
- 星座测试法：把品牌名去掉，读者还能认出是你写的吗？

---

## 第四阶段：全站体检（Claude SEO，周期性）

**目标：** 定期检查技术基础不滑坡。建议每次大改版后 + 每月一次例行。

### 步骤 11：全站审计

```
/seo audit [网址]
```

15 个代理同时并行工作（8 个必开 + 7 个条件触发）：
- **必开：** 技术、内容、Schema、Sitemap、性能、视觉、GEO、SXO
- **条件触发：** 检测到电商→开电商审计；检测到本地业务→开本地SEO、地图情报；有Google API→开GSC/GMS/GA4数据

**产出：** SEO 健康分 (0-100) + PDF 报告。

### 步骤 12：技术SEO深度检查

```
/seo technical [网址]
```

9 个维度逐一排查：
- 抓取能力（robots.txt、抓取预算）
- 索引能力（noindex 误用、canonical 冲突）
- 安全性（HTTPS、混合内容）
- URL 结构
- 移动端适配
- Core Web Vitals（LCP、INP、CLS）
- 结构化数据
- JavaScript 渲染
- IndexNow 协议

### 步骤 13：SEO 漂移监控

```
/seo drift baseline [网址]    # 建立基线
/seo drift compare [网址]     # 改版后对比
/seo drift history [网址]     # 查看历史变化
```

这是一套"SEO 的版本控制"：
- 抓取页面 SEO 关键元素存入 SQLite
- 17 条对比规则覆盖标题、meta、canonical、hreflang、Schema、结构化内容等
- 变更分级：INFO / WARNING / CRITICAL

**使用场景：** 每次上线前建基线，上线后立即对比，防止无意中改了 title 或 noindex 导致暴跌。

### 步骤 14：外链审计

```
/seo backlinks [网址]
```

多数据源融合：
- Moz Link Explorer（DA/PA、垃圾评分、锚文本分布）
- Bing Webmaster Tools（外链数、竞品对比）
- Common Crawl Web Graph（PageRank、入度）

**产出：** 外链健康度报告——哪些引荐域好、哪些可疑、竞品在哪里拿链接。

---

## 完整流程图

```
┌─────────────────────────────────────────────────────────┐
│                    第〇步：一次性初始化                      │
│  SEO Machine: 配置 brand-voice.md, writing-examples.md     │
│  SEO Machine: 配置 WordPress 发布凭证                       │
│  Claude SEO: 配置 Google API / Moz API（可选，增强数据）      │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│             第一阶段：战略规划（SuperSEO）                    │
│                                                         │
│  keyword-deep-dive → topic-cluster-planning → content-brief │
│                                                         │
│  输出：内容路线图 + 每篇简报                                   │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│            第二阶段：内容生产（SEO Machine）                  │
│                                                         │
│    /research → /write → /optimize → /publish-draft       │
│                                                         │
│  输出：已发布、已优化的 WordPress 文章                         │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│              第三阶段：质量审查（SuperSEO）                    │
│                                                         │
│  page-audit → semantic-gap-analysis → improve-content    │
│                                                         │
│  输出：改进方案 → 回到第二阶段 /rewrite 执行                   │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│           第四阶段：全站体检（Claude SEO，周期性）             │
│                                                         │
│   /seo audit → /seo technical → /seo drift → /seo backlinks │
│                                                         │
│  输出：健康报告 + 修复优先级 + 漂移记录                         │
└─────────────────────────────────────────────────────────┘
```

---

## 节奏建议

| 环节 | 频率 | 工具 |
|------|------|------|
| 内容战略规划 | 每季度 | SuperSEO |
| 关键词深潜 | 每篇新文章前 | SuperSEO |
| 文章生产 | 按内容日历 | SEO Machine |
| 已发布页面审计 | 发布后1个月 | SuperSEO |
| 全站技术审计 | 每月 + 每次改版 | Claude SEO |
| 漂移基线对比 | 每次上线部署 | Claude SEO |
| 外链审计 | 每季度 | Claude SEO |
| E-E-A-T 审计 | 核心页面每季度 | SuperSEO |

---

## 常见问题

**Q: 三个工具必须一起用吗？**

不必。如果你还没内容，从 SEO Machine 开始（先要有东西可排）。如果你有内容但不排名，从 SuperSEO 的 page-audit + semantic-gap-analysis 开始（诊断问题）。如果你流量突然跌了，从 Claude SEO 的 drift compare 开始（查是不是改坏了什么）。

**Q: 这三者会不会功能重叠？**

有几个交集点但角度不同：
- SuperSEO 的 `topic-cluster-planning` 和 Claude SEO 的 `seo-cluster` 都做话题集群，但前者重内容策略，后者重 SERP 重叠度计算
- SuperSEO 的 `page-audit` 和 Claude SEO 的 `seo-page` 都做单页分析，但前者对标竞品，后者面向技术诊断
- SEO Machine 的 `seo-audit` 技能和 Claude SEO 的 `/seo audit` 功能不同：前者侧重页面级建议，后者是全站多代理并行审计

**Q: 需要哪些外部 API 才能跑通全流程？**

- **SuperSEO：** 零依赖，Agent 自己爬 SERP
- **SEO Machine：** DataForSEO（关键词数据）、GA4 + GSC（效果数据，可选）、WordPress 凭证（发布必需）
- **Claude SEO：** Google API（GSC/CrUX/GA4，可选但建议）、Moz API（外链）、DataForSEO（实时 SERP）
