# SEO Workbench

三套开源 SEO 工具包的编排层，覆盖 SEO 全链路：战略规划 → 内容生产 → 质量审查 → 技术审计 → 外链建设 → 持续监控。

## 使用场景与覆盖状态

| # | 场景 | 项目类型 | 覆盖状态 |
|---|------|---------|---------|
| 1 | Shopify Liquid 新站 (Online Store 2.0) | `shopify` | ✅ 完整覆盖 |
| 2 | Shopify Headless 新站 (Hydrogen + Oxygen) | `shopify-headless` | ✅ 完整覆盖 |
| 3 | Shopify Headless 新站 (Hydrogen + Vercel) | `shopify-headless` | ✅ 完整覆盖 |
| 4 | Shopify Headless 新站 (Next.js + Shopify) | `shopify-headless` | ✅ 完整覆盖 |
| 5 | 通用新站 (WordPress / 其他 CMS) | `general` | ✅ 完整覆盖 |
| 6 | 已有站改造 (Liquid / 通用 CMS) | `existing` | ✅ 完整覆盖 |
| 7 | **Liquid → Headless 迁移** | — | ❌ 暂未适配 |
| 8 | **Headless 已有站改造** | — | ❌ `existing` 未区分 platform |
| 9 | **混合架构（部分页面 Headless）** | — | ❌ 暂未适配 |

### 场景说明

**场景 1-6（已覆盖）：** 工作流六阶段（INIT → STRATEGY → CONTENT_PRODUCTION → QUALITY_REVIEW → TECHNICAL_AUDIT → OFF_PAGE → MONITORING）完整可用。Headless 项目的 INIT 和 TECHNICAL_AUDIT 阶段会根据 `platform` 配置（framework / hosting / cms）自动注入对应的检查清单和技术审计上下文。

**场景 7 - Liquid → Headless 迁移：** 真实需求——商家从传统 Shopify Theme 迁移到 Hydrogen。迁移期间有独特的 SEO 风险：URL 结构是否变化、301 重定向完整性、Schema JSON-LD 格式是否兼容、Sitemap 生成器替换后 URL 覆盖率是否一致。当前 workbench 没有针对迁移场景的专项检查步骤。如需使用，需要手动组合 `existing` 的审计能力 + `shopify-headless` 的技术基线检查。

**场景 8 - Headless 已有站改造：** 当前 `existing` 类型未区分 `platform`，无法根据 framework/hosting 输出不同的 INIT 检查清单。Headless 已有站的改造需要额外关注：现有 JSON-LD 组件审查、流式 SSR 性能基线、路由 SEO 审计、CMS 内容管线评估。`existing` 类型的功能仍可使用（STRATEGY → QUALITY_REVIEW → TECHNICAL_AUDIT），但 INIT 阶段不会展示 Headless 特有的基线检查清单。

**场景 9 - 混合架构：** 部分页面用 Hydrogen（如产品页），部分保持 Liquid（如 Blog 和静态页）。这种情况的 SEO 复杂度最高：需要同时维护两套 SEO 管线，确保 Sitemap 的 URL 来源正确合并，Schema 在两套系统中一致，Canonical 跨架构正确指向。当前 workbench 不支持此类混合项目。

## 支持的 Headless 技术路线

| 框架 | 托管 | CMS | 项目类型 |
|------|------|-----|---------|
| Hydrogen (Remix) | Oxygen | Sanity / Contentful / Strapi / 无 | `shopify-headless` |
| Hydrogen (Remix) | Vercel | Sanity / Contentful / Strapi / 无 | `shopify-headless` |
| Hydrogen (Remix) | 自托管 | Sanity / Contentful / Strapi / 无 | `shopify-headless` |
| Next.js | Vercel / Netlify / 自托管 | Sanity / Contentful / Strapi / 无 | `shopify-headless` |
| 其他框架 | 任意 | 任意 | `shopify-headless --framework other` |

## 快速开始

### 1. 克隆并安装依赖

```bash
git clone https://github.com/<your-org>/seo-workbench.git
cd seo-workbench
./setup.sh
```

`setup.sh` 会自动克隆三个外部技能包（`superseo-skills`、`seomachine`、`claude-seo`）到项目根目录。

**前置条件：** `git`、`uv`、Python 3.11。Claude Code 只在使用 legacy slash commands 时需要。

### 2. 初始化项目

Agent-neutral CLI:

```bash
env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench \
  init shopify-headless --name "我的店铺" --url "https://myshop.com" \
  --framework hydrogen --hosting oxygen --cms sanity

env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench status
env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench next
```

Claude legacy commands remain available:

```bash
claude
```

在 Claude Code 中执行：

```
# Liquid Shopify 新站
/workflow:init shopify --name "我的店铺" --url "https://myshop.com"

# Headless Shopify 新站
/workflow:init shopify-headless --name "我的店铺" --url "https://myshop.com" \
  --framework hydrogen --hosting oxygen --cms sanity

# 通用新站
/workflow:init general --name "项目名" --url "https://example.com"

# 已有站改造
/workflow:init existing --name "项目名" --url "https://example.com"
```

然后跟着 `/workflow:next` 一步步走。

### 3. 技术审计机器证据

进入 `TECHNICAL_AUDIT` 阶段时，workflow 会先运行本地胶水工具采集机器证据：

```bash
env UV_CACHE_DIR=.uv-cache uv run --python 3.11 python -m seo_workbench_tools.workflow_evidence
```

产出写入：

```text
seo-workbench/audits/raw/evidence-*.json
```

后续 `technical-audit`、`schema`、`sitemap`、`images` 等步骤会读取这份 JSON，把页面状态码、最终 URL、页面类型、title/meta/canonical、HTTP headers、内容结构、JSON-LD 结构校验、图片统计、robots.txt、sitemap freshness、hreflang 和静态资源缓存证据注入到对应 Skill 的 prompt 中。

如需截图、移动端、above-the-fold 或渲染后 DOM 证据，可运行：

```bash
env UV_CACHE_DIR=.uv-cache uv run --python 3.11 --extra rendered python -m seo_workbench_tools.rendered_probe https://example.com
```

产出写入：

```text
seo-workbench/audits/rendered/
```

## 教程索引

| 教程 | 适用场景 |
|------|---------|
| `Shopify从0到1-SEO建设进阶教程.md` | Shopify Liquid (Online Store 2.0) |
| `Shopify-Hydrogen-Headless-SEO指南.md` | Shopify Headless (Hydrogen / Next.js) |
| `从0到1新站SEO建设教程.md` | 通用新站 (WordPress / CMS) |
| `SEO工具链协同工作流指南.md` | 三工具协同通用指南 |

## 目录结构

```
seo-workbench/
├── README.md                                    ← 本文件
├── CLAUDE.md                                    ← 根配置文件
├── pyproject.toml                               ← uv / Python 3.11 工具环境
├── seo_workbench_tools/                         ← 技术审计机器证据采集工具
├── seo-workbench/
│   ├── CLAUDE.md                                ← 编排引擎定义 (状态机、Handoff、错误处理)
│   ├── templates/state.json                     ← 状态文件模板
│   ├── state.json                               ← 运行时状态
│   ├── strategy/                                ← SuperSEO 产出
│   ├── content/                                 ← 内容产出
│   └── audits/                                  ← 审计产出 (含 raw/evidence-*.json)
├── .claude/commands/                            ← 工作流命令
│   ├── workflow-init.md
│   ├── workflow-next.md
│   ├── workflow-status.md
│   └── workflow-phase.md
├── superseo-skills/                             ← SuperSEO: 内容战略顾问 (setup.sh 克隆)
├── seomachine/                                  ← SEO Machine: 内容生产流水线 (setup.sh 克隆)
├── claude-seo/                                  ← Claude SEO: 技术审计平台 (setup.sh 克隆)
└── setup.sh                                     ← 依赖安装脚本
```

## 已知限制

- **外部 Skill 不感知 Headless。** `claude-seo:seo-technical` 等 skill 是平台无关的。Workbench 通过 TECHNICAL_AUDIT 阶段的 `workflow_evidence` + `headless-precheck` 补充 raw HTML、HTTP headers、Schema、图片、robots.txt、sitemap、hreflang 和资源缓存机器证据。
- **渲染后证据依赖 Playwright。** raw HTML、robots.txt、sitemap、资源缓存检查默认可跑；截图和 rendered DOM 使用 `seo_workbench_tools.rendered_probe`，需要用 `--extra rendered` 并先安装 Chromium。
- **无自动发布。** `/write` 产出草稿后需手动发布（WordPress 除外）。Headless CMS 的自动发布管线不在当前 scope。
- **单站点假设。** 当前工作流假设一个项目对应一个站点。多站点/多语言 SEO 不在此版本覆盖。
