# Workflow Status Command

展示当前 SEO 项目的完整进度面板。

## Usage

```
/workflow:status
```

## Process

1. 读取 `seo-workbench/state.json`
2. 读取 `seo-workbench/CLAUDE.md` 获取阶段定义
3. 格式化输出进度面板

## 输出格式

### 项目概览

```
╔══════════════════════════════════════════╗
║  📋 {project.name}                       
║  🏷  类型: {typeDisplay}                  
║  🔗 URL: {project.url}                    
║  📅 创建: {project.createdAt}              
║  📍 阶段: {currentPhase}                   
║  ⏱  最后活动: {lastAction}                 
╚══════════════════════════════════════════╝
```

typeDisplay 根据 `project.type` 和 `project.platform` 动态生成：
- `shopify` → "Shopify 从0到1 (Liquid)"
- `shopify-headless` → "Shopify 从0到1 (Headless: {platform.framework} + {platform.hosting})"，如 CMS 非 none 加 " + {platform.cms}"
- `general` → "通用新站 从0到1"
- `existing` → "已有站改造"

### 阶段进度

用表格展示所有阶段及其状态：

```
阶段                      状态        步骤完成
─────────────────────────────────────────────
INIT                     ✅ 已完成    3/3
STRATEGY                 🔄 进行中    2/4
  ├── 产品品类关键词深潜   ✅ done
  ├── 信息型关键词深潜     ✅ done
  ├── 话题集群规划         🔄 in_progress
  └── 内容简报生成         ⏳ pending
CONTENT_PRODUCTION       ⏳ 待开始    0/0
QUALITY_REVIEW           ⏳ 待开始    0/3
TECHNICAL_AUDIT          ⏳ 待开始    0/5
OFF_PAGE                 ⏳ 待开始    0/2
MONITORING               ⏳ 待开始    0/3
```

状态图标:
- ✅ = 阶段中所有步骤 done
- 🔄 = 阶段中有步骤 in_progress
- ⏳ = 阶段中所有步骤 pending
- ⚠️ = 阶段中有步骤失败

### 内容队列 (CONTENT_PRODUCTION 阶段专用)

```
内容队列 (contentQueue)
─────────────────────────────────────────────
Hub: 婴儿睡眠穿着完全指南           [已发布] 🔗
  ├── 不同温度的婴儿穿着建议         [已发布] 🔗
  ├── 新生儿与6个月婴儿睡衣区别       [草稿]   📝
  ├── 有机棉 vs 普通棉婴儿衣物        [计划中] ⏳
  ├── 婴儿睡衣面料材质全解析          [计划中] ⏳
  └── ...还有 4 篇
─────────────────────────────────────────────
进度: 2/10 已发布 | 1/10 草稿 | 7/10 计划中
```

### 产出文件列表

```
产出文件
─────────────────────────────────────────────
strategy/
  ├── keyword-dives/product-organic-baby-pajamas.md
  ├── keyword-dives/info-baby-sleep-guide.md
  └── cluster-plan.md
content/drafts/
  └── newborn-vs-6month-pajamas.md
audits/
  └── (空)
```

### 下一步

```
👉 下一步: 为"有机棉 vs 普通棉婴儿衣物"生成内容简报
   执行 /workflow:next 继续
```

## 如果 state.json 不存在

```
⚠️ 未找到项目。请先执行 /workflow:init 创建项目。

用法:
  /workflow:init shopify           --name "项目名" --url "https://xxx.com"   (Liquid)
  /workflow:init shopify-headless  --name "项目名" --url "https://xxx.com"   (Headless)
  /workflow:init general           --name "项目名" --url "https://xxx.com"   (通用)
```

## 如果所有阶段都完成

```
🎉 恭喜！{project.name} 已完成全部 7 个阶段。

建议下一轮:
  - 开新的话题集群: 回到 STRATEGY 阶段 (/workflow:phase strategy)
  - 月度技术复查: 回到 MONITORING 阶段 (/workflow:phase monitoring)
  - 查看详细教程: SEO工具链协同工作流指南.md
```
