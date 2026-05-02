# Shopify 从0到1 SEO 建设进阶教程

使用 SuperSEO + SEO Machine + Claude SEO 搭建一个从零起步的 Shopify 独立站 SEO 体系。

> **📌 本教程适用于 Shopify Liquid (Online Store 2.0 / 传统 Theme)。** 如果你用的是 **Hydrogen / Remix / Next.js 等 Headless 方案**，请阅读 `Shopify-Hydrogen-Headless-SEO指南.md`——Headless 的 SEO 基线、URL 结构、Schema 管理、Sitemap 生成方式都与 Liquid 完全不同。

---

## Shopify SEO 的特殊性

Shopify 让建站变简单了，但它的 SEO 有很多"出厂缺陷"和独特挑战：

### Shopify 的先天不足

| 问题 | 影响 |
|------|------|
| **URL 强制层级**：产品永远是 `/products/xxx`，集合永远是 `/collections/xxx` | 你无法自定义 URL 结构，所有产品平级 |
| **重复 URL**：同一产品可通过多个路径访问（`/products/shirt`、`/collections/summer/products/shirt`） | 自带重复内容风险 |
| **Collection 页面内容贫瘠**：集合页默认只有产品列表，没有文字内容 | Google 可能判定为薄内容 |
| **Sitemap 自动生成不可控**：Shopify 自动生成 sitemap 但你不能精细控制哪些页面收录 |
| **Tags 会生成分页**：`/collections/summer/tag` 会生成大量低质量 URL |
| **Blog 功能简陋**：Shopify 的博客系统远不如 WordPress | 没有目录、没有内链推荐、没有 Schema 自动化 |
| **图片无法自动转 WebP/AVIF**：需要手动处理或依赖 App |
| **结账页无法自定义 SEO**：`/checkout` 不受你控制（但没关系，不应该被索引） |

### 本教程的路由策略

知道这些限制后，我们不会去对抗 Shopify，而是绕过它的弱点、放大它的优势：

- 产品页和集合页**不做过度优化**——把精力花在内容和外链上
- 用 Blog 功能建立内容护城河——这是 Shopify 站最被低估的 SEO 资产
- 用 Claude SEO 做技术兜底——自动发现重复 URL、Schema 缺失等问题
- 用 SuperSEO 做内容策略——电商站的内容不只是产品描述

---

## 第〇步：战前准备

### 安装和配置三个工具

**SEO Machine**：

1. 在 `seomachine/context/brand-voice.md` 中定义电商品牌的语调（店铺风格、目标客群语气）
2. 在 `seomachine/context/target-keywords.md` 中列出：
   - 5-10 个核心品类词（如 "cotton baby clothes"、"organic newborn pajamas"）
   - 5-10 个核心信息型词（如 "what should newborn wear to sleep"、"baby clothing size guide"）
3. **不用配置 WordPress 发布**——Shopify 有自己的内容系统，用 `/write` 写内容后手动粘贴到 Shopify Blog，或者直接让 Agent 参考你的风格但不发布

**Claude SEO**：

配置 Google API（GSC + GA4）和 DataForSEO（用于 Google Shopping 数据和竞品价格分析）。

### Shopify 本身的 SEO 基础设置

在开始用三个工具前，先在 Shopify 后台做完这些：

- [ ] 验证 GSC（通过 DNS 或 HTML 标签）
- [ ] 提交 sitemap.xml 到 GSC
- [ ] 确认 Online Store > Preferences 里的 Title 和 Meta Description 已填（这是整站的）
- [ ] 确认Settings > Domains 里只有**一个主域名**，所有其他域名 301 重定向到主域
- [ ] 确认 Settings > Store Details 里的地址、电话、邮箱准确（本地 SEO + E-E-A-T）
- [ ] 在 Theme > Edit code 里检查 `theme.liquid` 的 `<head>` 没有硬编码的 noindex

---

## 第一阶段：品类与关键词战略（SuperSEO + SEO Machine）

电商站和内容站的最大区别：你同时要打**交易型关键词**（买我产品的人）和**信息型关键词**（需要教育的人）。两者需要完全不同的内容策略。

### 电商站关键词三角形

```
           交易型（买）
          /product page
         /   landing page
        /_____________
        \             \
         \             \
    商业调研型（比）    信息型（学）
    /comparison page   /buying guide
    /alternatives page /blog article
```

### 步骤 1：品类关键词深潜（交易型）

对每个核心品类做深潜。比如你卖婴儿睡衣，不要只查 "baby pajamas" 一个词：

```
/superseo:keyword-deep-dive  →  "baby pajamas"（大词，交易型）
/superseo:keyword-deep-dive  →  "organic baby pajamas"（长尾，交易型）
/superseo:keyword-deep-dive  →  "newborn pajamas no feet"（超长尾，交易型）
/superseo:keyword-deep-dive  →  "best baby pajamas"（商业调研型）
```

对每个关键词，Agent 会输出搜索意图和竞争格局。重点关注：
- **哪些搜索结果中有 Shopify 独立站的身影**——说明这个词独立站还有机会，不是亚马逊/Etsy 完全垄断
- **SERP Features**——有没有 Shopping Ads 霸屏、有没有 Featured Snippet 可以抢

### 步骤 2：信息型关键词深潜（内容机会）

```
/superseo:keyword-deep-dive  →  "what should newborn wear to sleep"
/superseo:keyword-deep-dive  →  "baby pajamas size guide"
/superseo:keyword-deep-dive  →  "merino wool vs cotton baby clothes"
/superseo:keyword-deep-dive  →  "how to dress baby for sleep by temperature"
```

这些词的特点是搜索量大、竞争相对低，而且 Amazon 上很难有高质量答案——这正是 Shopify 独立站用 Blog 切入的机会。

### 步骤 3：话题集群规划（信息型内容架构）

```
/superseo:topic-cluster-planning
```

以你的核心品类为种子话题，Agent 会输出多个 Hub & Spoke 架构。电商站常见的信息型集群模式：

**示例（婴儿睡衣店）：**

```
Hub: 婴儿睡眠穿着完全指南
├── Spoke: 不同温度的婴儿穿着建议
├── Spoke: 新生儿与6个月婴儿睡衣区别
├── Spoke: 有机棉 vs 普通棉婴儿衣物
├── Spoke: 婴儿睡衣面料材质全解析
├── Spoke: 婴儿睡衣尺码对照表+测量方法
├── Spoke: 季节性婴儿睡衣选购指南
├── Spoke: 婴儿连体衣 vs 分体睡衣怎么选
└── Spoke: 婴儿睡衣常见安全问题清单
```

**每一篇 Spoke 都要有天然的产品植入点**——不是硬广，是"你讲的东西刚好和你的产品有关"。

### 步骤 4：商业调研型内容规划

```
/superseo:content-brief  →  "best baby pajamas"
/superseo:content-brief  →  "bamboo vs cotton baby pajamas"
```

这两类内容对电商站是金矿：
- **Best X 类文章**：搜索意图强、转化率高。但要写得真实——真买过、真用过、真有对比
- **X vs Y 类文章**：搜索量不大但转化率极高，因为搜这类词的人已经在决策边缘

### 步骤 5：生成内容简报

```
/superseo:content-brief
```

为集群中的每篇文章和每个商业调研页生成简报。

**产出：** 一个电商内容路线图——接下来 3 个月写什么，哪些是信息型（引流），哪些是商业调研型（转化）。

---

## 第二阶段：页面优化的优先级顺序（Claude SEO + SuperSEO）

电商站不需要所有页面都深度优化。精力分配的优先级：

```
产品页  >  集合页  >  Blog文章  >  品牌页
（赚钱的）（聚合词的）（引流的）  （E-E-A-T）
```

### 步骤 6：产品页 SEO——最值得花时间的地方

用 Claude SEO 对每个核心产品页面做分析：

```
/seo page [产品URL]
```

**Shopify 产品页 SEO 检查清单：**

| 检查项 | 怎么做 |
|--------|--------|
| **Title Tag** | `[产品名] - [品类] by [品牌名]` 或 `[产品名] | [核心卖点]`。60字符以内 |
| **Meta Description** | 含品类词 + 卖点 + CTA。不要用 Shopify 自动生成的 |
| **H1** | 产品名称。只有一个 H1 |
| **H2** | 产品描述里用 H2 分块：特点、规格、用途、常见问题 |
| **产品描述** | 至少 300-500 字，含品类关键词的自然分布。不要在描述里写"FREE SHIPPING!!"——写产品本身 |
| **图片 Alt Text** | 每张产品图写描述性 Alt 文本，含品类词 |
| **图片文件名** | 上传前改名：`organic-baby-pajamas-blue-front.jpg` |
| **URL** | Shopify 自动生成 `/products/xxx`，确保 handle 含关键词，不包含数字编号 |
| **Product Schema** | 在 theme.liquid 确认 Shopify 自动生成的 Product Schema 正确（含价格、库存、评价） |
| **Reviews** | 安装 Judge.me 或 Loox 等评价 App，让评价数据带入 AggregateRating Schema |

### 步骤 7：集合页 SEO——被最多人忽略的地方

```
/seo page [Collection URL]
```

大多数 Shopify 店集合页只有产品列表 + 顶部一行标题。Google 可能判断为 Thin Content。

**做法：** 在每个 Collection 页底部（不是顶部）添加 300-500 字品类描述。放在底部不影响转化（用户先买后读），但给 Google 足够的内容信号。

**示例：**

> ## About Our Organic Baby Pajamas
>
> Every pair of pajamas in this collection is made from GOTS-certified organic cotton grown without pesticides. We carry sizes from newborn to 24 months, with both zipper and snap closures available. [展开讲为什么有机棉适合婴儿、含什么认证、几个常见FAQ]

### 步骤 8：Blog 页面优化

SEO Machine 的 `/write` 负责生产 Blog 内容。关键技巧：

- **每篇 Blog 至少 1800 字**（电商站 Blog 最容易犯的错误是写太短）
- **每篇都有 2-3 个自然的产品链接**（不推销，但在讲到相关点时顺便链向产品）
- **CTA 放在文中而非文章底部**（大部分人看不到底）
- **第一段直接给出最有用的信息**（不要写"在当今世界，婴儿睡衣的选择越来越多..."这种废话）

---

## 第三阶段：E-E-A-T 建设——让 Google 信任你

### 步骤 9：E-E-A-T 专项审计

对站点整体和核心产品页做审计：

```
/superseo:eeat-audit
```

**电商站 E-E-A-T 打分重点：**

**Experience（经验）**
- 关于页有没有创始人/团队的真实故事和照片？
- 产品描述里有没有体现"用过"的细节？（不是"舒适面料"而是"我们测试了8种不同克重的面料后选了这款，因为它在30°C天和15°C天穿起来都刚刚好"）
- 有没有真实用户生成内容（UGC）展示在页面里？

**Expertise（专业知识）**
- Blog 文章有作者署名和简介吗？
- 技术性产品（比如母婴用品）有没有引用行业标准（GOTS、OEKO-TEX、CPSC）？
- 是否有尺寸指南、材质对比等体现专业知识的内容？

**Authoritativeness（权威性）**
- 新站不要指望马上被引用，但可以在内容中引用权威来源（AAP 婴儿睡眠指南、FDA 标准等）
- 有媒体报道过你吗？有的话专门建一个 Press 页

**Trustworthiness（可信度）**
- 联系页有真实地址和电话吗（不是仅一个表单）？
- 退换货政策清晰可见吗？
- 隐私政策、Terms of Service 完整吗？
- 在线客服或联系方式容易找到吗？

### 步骤 10：E-E-A-T 补充内容生产

根据审计结果，用 SEO Machine 生产 E-E-A-T 支撑内容：

```
/write "关于我们——[品牌名]的创立故事"
/write "[品牌名]的有机棉到底好在哪——从棉花到成衣的全流程"
/write "为什么我们选择GOTS认证有机棉——面料安全深度解析"
```

**电商站最重要的3篇 E-E-A-T 内容：**

1. **关于页**：创始人真名、真照片、真实创立动机（不是"我们热衷于提供最好的X"这种废话）
2. **材质/工艺深解**：如果你在卖实物产品，深度讲你的面料、工艺、供应链——这是 Amazon 卖家做不到的
3. **客户故事/Case**：用真实客户的体验来证明你的产品确实好用

---

## 第四阶段：Schema 与结构化数据（Claude SEO）

电商站 Schema 直接关系 Rich Results 展示（评价星星、价格、库存状态），影响点击率。

### 步骤 11：Schema 全面审计

```
/seo schema [网址]
```

**Shopify 站最小必要 Schema 清单：**

| Schema 类型 | 放置位置 | 说明 |
|------------|---------|------|
| `Organization` | 首页 | 品牌 Logo、社交链接、联系信息 |
| `WebSite` + `SearchAction` | 首页 | 启用 Sitelinks Search Box |
| `Product` + `Offer` | 产品页 | Shopify 自动生成，**但要验证价格、库存、评价字段是否准确** |
| `AggregateRating` | 产品页 | 由评价 App 生成。如果没有评价 App，尽快安装一个 |
| `BreadcrumbList` | 所有页面 | Shopify 自动生成，但要验证路径正确 |
| `Article` | Blog 文章 | Shopify Blog 不自动生成 Article Schema，需手动检查/添加 |
| `CollectionPage` | 集合页 | 如未自动生成，考虑手动添加 |
| `FAQPage` | 产品页（如有FAQ段落） | 有机会出现在 FAQ Rich Result |
| `LocalBusiness` | 如有实体店 | 地址、营业时间、坐标 |

对于没有自动生成 Schema 的页面类型（如 Article 和 CollectionPage），用 Claude SEO 的生成功能：

```
/seo schema generate --type Article --url [文章URL]
/seo schema generate --type CollectionPage --url [集合页URL]
```

在 Shopify Admin > Online Store > Themes > Edit Code > `theme.liquid` 的 `<head>` 区域添加 JSON-LD。

---

## 第五阶段：技术 SEO 加固（Claude SEO）

### 步骤 12：全站技术审计

```
/seo technical [网址]
```

**Shopify 站高频技术问题：**

| 问题 | 修复方式 |
|------|---------|
| **重复产品 URL** | 在 `theme.liquid` 里添加 canonical 标签，确保所有产品页面 canonical 指向 `/products/xxx` 而非 `/collections/xxx/products/xxx` |
| **Tags 页面被索引** | 在 GSC 或 robots.txt 里屏蔽 tags URL（大多数情况下 Tags 页面没有独特价值） |
| **Vendor 页面被索引** | Shopify 自动生成的 vendor 集合页通常没内容价值，视情况 noindex |
| **分页页面** | Shopify 自动处理 `rel="next"` 和 `rel="prev"`，但要确认模板正确输出 |
| **图片未压缩** | 上传前用 Squoosh 或类似工具压缩。对于已有图片，用 Crush Pics 等 App 批量处理 |
| **JS 渲染问题** | Shopify Theme 通常是 SSR，但如果你装了大量 App 导致 JS 繁重，用 Claude SEO 检查渲染差异 |
| **结账页被爬取** | 确认 `/checkout`、`/cart`、`/account` 等页面不被索引（Shopify 默认处理但建议确认） |

### 步骤 13：图片 SEO 专项

```
/seo images [网址]
```

这是 Shopify 站最容易被忽略的大项。电商站图片多，每一步优化都放大：

- **Alt Text**：写"有机棉婴儿睡衣 蓝色 正面"，而不是"产品图片 1"
- **文件名**：上传前改为描述性命名
- **格式**：用 JPEG（照片）和 PNG（Logo/图标），理想情况转 WebP
- **尺寸**：响应式加载——产品图在移动端不需要 2000px 宽
- **Lazy Loading**：首屏4张产品图不放 lazy load，其余图片 lazy load

---

## 第六阶段：外链建设（SuperSEO）

### 步骤 14：确定阶段并获取策略

```
/superseo:linkbuilding
```

新 Shopify 店通常被判定为 Foundation 阶段，推荐的战术侧重：

- **供应商/制造商链接**：如果你卖品牌产品，让品牌方在他们的"Where to Buy"页面链向你
- **行业目录**：母婴、户外、宠物等垂直目录
- **媒体 sample 寄送**：给垂直媒体、博主寄产品样品，换取评测和链接
- **客座博客**：在行业相关的小站写嘉宾文章
- **资源推荐列表**：找到"最佳X资源"类型的页面，申请把你的 Blog 内容加进去
- **播客赞助/嘉宾**：电商创始人出现在播客通常能拿到一个网站链接

### 步骤 15：定期监控外链

```
/seo backlinks [网址]
```

每月检查一次：
- 新增了哪些外链
- 有没有垃圾链接需要 disavow（通常不需要，Google 会忽略大部分垃圾链接）
- 竞品在哪些域拿到了链接——你也能去试试吗

---

## 第七阶段：Google Shopping 与电商搜索可见性（Claude SEO）

如果有 DataForSEO 扩展，可以获取 Google Shopping 数据：

### 步骤 16：电商搜索分析

```
/seo ecommerce [网址]
```

分析覆盖：
- 你的产品在 Google Shopping 的可见度
- 价格与竞品的差距（你在 Shopping 搜索结果里是贵了还是便宜了——这直接影响 CTR）
- Product Schema 验证（确保价格、库存、评价在 Schema 里完整携带）
- Amazon 竞品分析——你的产品在 Amazon 上也有在卖吗？差价多少

---

## Shopify 站发布前检查清单

### 技术基础
- [ ] GSC 已验证并提交 sitemap
- [ ] 只有一个主域名，其他域名 301 到主域
- [ ] HTTPS 全站
- [ ] `/products/xxx` 是 canonical URL，collection 内部链接不产生重复索引
- [ ] Tags 页面、Vendor 页面视情况 noindex
- [ ] 核心页面不存在 noindex meta 标签
- [ ] robots.txt 没有 block 重要内容
- [ ] `rel="next"` 和 `rel="prev"` 在分页页面上正确

### Schema
- [ ] Organization（首页，含 Logo）
- [ ] WebSite + SearchAction（首页）
- [ ] Product + Offer（产品页，验证价格精度）
- [ ] AggregateRating（产品页，有评价时必须有）
- [ ] BreadcrumbList（全站）
- [ ] Article（Blog 文章页，手动添加如果缺失）
- [ ] FAQPage（如果有产品FAQ）

### 内容
- [ ] 核心品类每个至少 150 字描述（集合页底部）
- [ ] 核心产品每个至少 300 字描述（产品页，含场景和细节）
- [ ] 至少 5 篇 Blog 文章已就绪
- [ ] About 页完整（真名+真照片+真实故事）
- [ ] 联系页、隐私政策、退换货政策公开可访问
- [ ] 每篇 Blog 文章有作者署名和简介

### 图片
- [ ] 产品图 Alt Text 含品类关键词
- [ ] 图片文件名有描述性
- [ ] 首屏图片使用 `<img>` 或 `<link rel="preload">`，无 lazy load
- [ ] OG 社交分享图默认存在

### 电商特有
- [ ] Google Merchant Center 已配置（如投 Shopping Ads）
- [ ] Product Schema 的价格与页面显示价格一致
- [ ] 评价 App 已安装（Judge.me / Loox / Stamped.io）

---

## 第1-6个月节奏（Shopify 版）

| 月份 | 核心工作 | 用到的工具/命令 |
|------|---------|---------------|
| **第1月** | 确定关键词战略；完成核心产品页优化（描述+Schema）；写 About 页和3-5篇 Blog | SuperSEO（keyword-deep-dive + cluster）+ SEO Machine（write）+ Claude SEO（page + schema） |
| **第2月** | 继续写 Blog 内容（目标10篇）；优化集合页描述；配置 Schema 全覆盖 | SEO Machine（write）+ Claude SEO（schema + technical） |
| **第3月** | 启动外链建设（供应商链接、目录、样品寄送）；写商业调研型内容（Best X、X vs Y） | SuperSEO（linkbuilding + content-brief）+ SEO Machine（write） |
| **第4月** | 全站技术审计；修复重复 URL 问题；图片 SEO 专项优化；分析 GSC 数据 | Claude SEO（technical + images + google）+ SuperSEO（page-audit） |
| **第5月** | 对表现不佳的产品页做单页审计和优化；写 E-E-A-T 深度内容 | SuperSEO（page-audit + semantic-gap + eeat-audit）+ SEO Machine（write） |
| **第6月** | 全站审计；外链审计；决定是否开第二个话题集群或新品类线 | Claude SEO（audit + backlinks）+ SuperSEO（content-brief） |

---

## Shopify 常见 SEO 错误

**错误1：依赖 Shopify 自动生成的 Title 和 Meta Description。**
Shopify 的默认模板是用产品名+店铺名+META 拼凑的，多半不可读。每个核心产品页单独写。

**错误2：产品描述只有两句话。**
"100%有机棉，舒适耐穿"——这不是描述，这是标签。电商站唯一能和 Amazon 拉开差距的就是你可以在产品描述里讲故事、写细节、展示专业知识。

**错误3：集合页没有文字内容。**
只有产品列表的集合页 = Google 眼里的薄内容页面。在底部加 150-300 字的品类描述。

**错误4：Blog 文章写得太短。**
750 字的 "5 Tips for Baby Sleep" 在 2026 年基本没机会。信息型内容至少 1500 字，真正有用的内容至少 2000 字。

**错误5：没装评价 App。**
产品页没有评价就无法触发 AggregateRating Rich Result。装上 Judge.me 或类似 App，哪怕只有几个评价也比零好。

**错误6：App 装太多。**
每个 App 都会加载 JS/CSS。30 个 App 的 Shopify 店通常打开时间超过 5 秒。定期审计并删掉不用的 App。用 Claude SEO 检查页面速度和渲染问题。

**错误7：忽略内链。**
电商站天然有产品页和集合页的内链结构，但 Blog 文章往往缺乏内链。每篇 Blog 必须链接到 2-3 个相关产品，同时链接到 2-3 篇其他 Blog 文章。
