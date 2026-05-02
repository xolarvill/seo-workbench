# Workflow Init Command

初始化一个新的 SEO 项目。创建状态文件和输出目录。

## Usage

```
# Liquid Shopify 新站 (默认)
/workflow:init shopify --name "我的店铺" --url "https://myshop.com"

# Headless Shopify 新站
/workflow:init shopify-headless --name "我的店铺" --url "https://myshop.com" \
  --framework hydrogen --hosting oxygen --cms sanity

# 通用新站
/workflow:init general --name "项目名" --url "https://example.com"

# 已有站改造
/workflow:init existing --name "项目名" --url "https://example.com"
```

参数：
- 第一个位置参数: 项目类型。可选 `shopify` (Liquid, 默认), `shopify-headless` (Headless), `general` (通用新站), `existing` (已有站改造)
- `--name`: 项目名称
- `--url`: 网站 URL
- `--framework`: (仅 shopify-headless) 前端框架。`hydrogen` (默认), `nextjs`, `other`
- `--hosting`: (仅 shopify-headless) 托管平台。`oxygen` (默认), `vercel`, `netlify`, `self-hosted`
- `--cms`: (仅 shopify-headless) 内容管理系统。`none` (默认), `sanity`, `contentful`, `strapi`

## Process

### Step 1: 读取模板并创建状态文件

1. 读取 `seo-workbench/templates/state.json` 获得模板结构
2. 根据 `--name`, `--url` 和项目类型填充 `project` 字段
3. 如果是 `shopify-headless` 类型: 将 `project.platform` 设置为 `{ "framework": "--framework值", "hosting": "--hosting值", "cms": "--cms值" }`。未传的参数使用默认值 (hydrogen / oxygen / none)
4. 如果非 `shopify-headless` 类型: `project.platform` 保持 `null`
5. 设置 `createdAt` 为当天日期 (YYYY-MM-DD)
6. 如果项目类型是 `existing`: 将 `phaseOrder` 调整为 `[INIT, QUALITY_REVIEW, TECHNICAL_AUDIT, STRATEGY, CONTENT_PRODUCTION, OFF_PAGE, MONITORING]`
7. 写入 `seo-workbench/state.json`

### Step 2: 创建输出目录

确认以下目录存在（不存在则创建）:
- `seo-workbench/strategy/keyword-dives/`
- `seo-workbench/strategy/briefs/`
- `seo-workbench/content/drafts/`
- `seo-workbench/audits/`

### Step 3: 引导 INIT 阶段配置

告诉用户接下来需要做的事（不要自动执行，只引导）:

**Shopify Liquid 项目**:
1. 配置 `seomachine/context/brand-voice.md` — 品牌语调、目标客群、禁用词汇
2. 配置 `seomachine/context/target-keywords.md` — 5-10个品类词 + 5-10个信息型词
3. 在 Shopify 后台完成 GSC 验证、主域名确认、HTTPS 检查

**Shopify Headless 项目**:
1. 配置 `seomachine/context/brand-voice.md` — 品牌语调、目标客群、禁用词汇
2. 配置 `seomachine/context/target-keywords.md` — 5-10个品类词 + 5-10个信息型词
3. 确认 Headless SEO 基线 — 参考 `Shopify-Hydrogen-Headless-SEO指南.md` 第二章 (MetaFunction / JSON-LD 组件 / sitemap / robots / 404)
4. 确认部署配置 — 根据 `--framework` 和 `--hosting` 选择对应检查清单 (见 `seo-workbench/CLAUDE.md` 末尾「Headless 平台检查清单」)

**通用项目**:
1. 配置 `seomachine/context/brand-voice.md`
2. 配置 `seomachine/context/target-keywords.md`

### Step 4: 完成初始化

更新 state.json:
- `currentPhase` = "INIT"
- `phases.INIT.status` = "in_progress"
- `nextAction` = "配置品牌声音与目标关键词文档"
- `lastAction` = "workflow:init 初始化完成"

输出 (根据项目类型适配):
```
✅ 项目 {name} 初始化完成 ({typeLabel})

📋 接下来的步骤:
  1. 编辑 seomachine/context/brand-voice.md — 定义品牌语调
  2. 编辑 seomachine/context/target-keywords.md — 列出目标关键词
  3. ({platformCheckLabel}) 验证技术基线
  4. 完成后执行 /workflow:next 继续

📖 参考教程: {tutorialPath}
```

typeLabel 和 tutorialPath 映射:
- shopify → "Shopify Liquid", `Shopify从0到1-SEO建设进阶教程.md`
- shopify-headless → "Shopify Headless ({framework} + {hosting})", `Shopify-Hydrogen-Headless-SEO指南.md`
- general → "通用新站", `从0到1新站SEO建设教程.md`
- existing → "已有站改造", `SEO工具链协同工作流指南.md`

## 如果 state.json 已存在

提示用户:
```
⚠️ 项目 {name} 已存在 (创建于 {createdAt})。

选择:
  - 继续当前项目: 直接使用 /workflow:next
  - 重置项目: /workflow:init shopify --name "新名称" --url "新URL"
  - 查看进度: /workflow:status
```

不覆盖已有 state.json。
