# SEO 基础知识与证据模型

> 本文是 SEO Workbench 各场景教程共用的知识基础，最后核验于 2026-07-18。平台教程只补充各自的实现差异，不重复维护这些规则。需要把搜索指标继续拆到访问、商品和收入时，使用 [SEO 增长诊断与拆解](SEO增长诊断与拆解.md)。

SEO 工作经常把抓取、收录、排名和流量混在一起。出现问题时，先确认它发生在哪一层，再选择证据和修复方法。

## 搜索引擎处理页面的六个阶段

### 1. 发现

搜索引擎可以通过站内链接、外部链接、XML Sitemap 和其他数据源发现 URL。Sitemap 是发现信号，不保证页面一定被抓取或收录。重要页面还应当能从首页、分类页或相关内容通过普通 `<a href>` 链接到达。

新站没有外链时，清楚的导航和 Sitemap 都有帮助。不要把站内搜索框当作主要发现方式，Googlebot 通常不会填写搜索表单来寻找页面。

### 2. 抓取

抓取是搜索引擎向 URL 发出请求并读取响应。需要检查：

- DNS、TLS 和服务器是否稳定；
- 最终状态码是否符合页面状态；
- robots.txt、CDN 和防火墙是否允许搜索爬虫访问；
- 重定向是否短而稳定；
- HTML、CSS、JavaScript 和图片资源是否可访问。

robots.txt 管理抓取，不负责删除索引。一个被 robots.txt 阻止的 URL 仍可能凭借外部链接出现在搜索结果中。如果页面需要退出索引，应让爬虫能够访问页面并读取 `noindex`，或返回合适的 404、410、认证响应。

### 3. 渲染

服务器返回的原始 HTML 可能已经包含完整内容，也可能只是一个等待 JavaScript 填充的外壳。Google 可以运行 JavaScript，但渲染需要额外资源和时间，其他搜索引擎、社交预览和部分 agent 也未必执行 JavaScript。

标题、正文、内部链接、canonical、robots 指令和时效敏感的商品结构化数据，优先放进服务器输出的 HTML。JavaScript 站点应比较原始 HTML 和渲染后 DOM，而不是根据框架名称推测可索引性。

### 4. 索引

页面可抓取不代表一定被索引。搜索引擎还会判断 canonical、重复内容、内容价值、站点质量和政策合规。一个 URL 也可能被视为另一个 URL 的重复版本。

URL Inspection API 返回 Google 已索引版本的状态，不执行实时测试，也不能批量请求收录。Google Indexing API 只适用于带 `JobPosting` 或直播 `BroadcastEvent` 的页面，不是普通网页的提交接口。

### 5. 展示和排名

被索引后，页面才有资格参与具体查询的结果排序。搜索意图、内容相关性、信息质量、页面体验、站点和页面信号都会影响结果。没有工具可以从页面检查结果直接推导 Google 的内部评分。

标题链接和摘要由 Google 根据查询动态生成。`<title>` 和 meta description 应准确、独特、简洁，但没有固定字符上限。搜索结果会根据设备宽度和查询需要截断或改写它们。

### 6. 点击和业务结果

展示、点击、询盘、注册和成交是不同阶段。高展示低点击可能是意图、标题或 SERP 版式问题；有点击无转化可能是页面承诺、产品匹配、价格、信任或表单问题。SEO 报告不应只看排名。

## 内容质量不靠固定字数

Google 没有偏好的文章字数。页面需要多长，取决于用户任务、主题复杂度、页面类型和你能提供的信息。产品规格页可以很短，采购指南可能需要更详细的比较；为了达到字数而重复解释会降低可用性。

规划内容时可以记录竞品篇幅，但它只能帮助估算制作成本。内容简报应回答下面这些问题：

- 这个查询背后的任务是什么；
- 用户需要做出什么决定；
- 页面需要哪些事实、步骤、比较或证据；
- 现有结果遗漏了什么；
- 我们能提供哪些第一方经验、数据、图片、测试或案例；
- 哪些说法需要引用一手来源；
- 页面完成后，用户是否还需要继续搜索才能解决同一个问题。

内容数量也不应写死。新站可以先发布少量关键页面，也可以在资料和编辑能力充足时一次上线完整目录。发布节奏由业务优先级、内容质量、索引反馈和团队产能决定。

## 如何正确使用 E-E-A-T

E-E-A-T 指经验、专业性、权威性和可信度。Google 明确说明，E-E-A-T 本身不是一个单独的排名因子，质量评估员的评分也不直接改变页面排名。

Workbench 可以用内部量表检查信任证据，但输出必须标为诊断意见，不能写成 Google 分数。更有用的检查包括：

- 作者、审核人和发布者是谁，是否需要公开说明；
- 内容中的经验能否由过程、图片、数据、样品或案例证明；
- 重要事实是否来自可靠的一手来源；
- 产品、公司、价格、库存、政策和联系方式是否一致；
- 内容的创建、测试和更新方法是否需要向读者解释；
- 医疗、金融、法律和安全等 YMYL 主题是否经过合格人员审核。

作者简介和 About 页面可以帮助用户判断来源，但不能替代准确内容。不要虚构经验、资质、客户案例或测试结果。

## AI 辅助内容的边界

Google 不因内容由 AI 辅助就自动降低排名。批量生成缺乏原创价值、准确性和编辑责任的页面，可能触及 scaled content abuse 政策。

在 Workbench 中使用 agent 写作时，至少保留：

- 目标受众、业务边界和品牌语气；
- 一手资料、访谈、产品数据或真实操作记录；
- 事实核验和来源；
- 由人承担的编辑与发布决定；
- 必要时对自动化使用方式作出说明。

AI Overviews 和 AI Mode 仍建立在 Google Search 的抓取、索引和质量系统上。Google 没有要求专用的 AI Schema 或新的机器可读文件。可抓取、可索引、正文清楚、内部链接合理和内容有独特价值仍是基础。

## 技术 SEO 的判断顺序

### 状态码表达页面状态

- 正常页面返回 200；
- 永久迁移使用 301 或 308；
- 临时迁移使用 302 或 307；
- 不存在的页面返回 404，永久删除可返回 410；
- 不要让错误页、空搜索结果或不存在的产品返回 200。

重定向应直接到最终目标。跨域、协议和 www 版本要统一到一个首选地址。

### canonical 是合并提示

canonical 用于表达多个相似 URL 中的首选版本。它是强提示，不是强制命令，也不是处理完全不同内容的工具。

canonical、Sitemap、内部链接、hreflang 和重定向应尽量指向同一个首选 URL。JavaScript 不应把服务器输出的 canonical 改成另一个值。

### noindex 与 robots.txt 分工不同

- 不想让页面被索引，但允许抓取：使用 robots meta 或 `X-Robots-Tag: noindex`；
- 不想让无价值参数消耗大量抓取资源：可以在确认索引策略后用 robots.txt 管理抓取；
- 需要保护私密信息：使用认证或访问控制，不能依赖 robots.txt。

### 分页需要可抓取的 URL 和链接

每个分页页面需要独立 URL，并通过普通链接连接前后页面。Google 已不再把 `rel="next"` 和 `rel="prev"` 当作索引信号。无限滚动应提供搜索引擎可以访问的分页后备路径。

### 多语言和多地区页面locale\hreflang

每个语言或地区版本使用独立、稳定的 URL。页面应有自指 canonical，并用 hreflang 相互引用所有替代版本，包括自身。不要只根据 IP 或浏览器语言强制跳转，用户和爬虫应能切换版本。

## 结构化数据只描述页面已有事实

结构化数据帮助搜索引擎理解页面，并可能让页面获得特定搜索展示资格。正确标记不保证一定出现 Rich Result，也不应标记页面上看不到的内容。

常见有效类型包括：

- `Organization` 或适用的 `LocalBusiness`；
- `BreadcrumbList`；
- `Article` 或 `BlogPosting`；
- 可购买产品页上的 `Product`、`Offer`、变体、配送和退货信息；
- 符合对应功能政策的其他受支持类型。

FAQ Rich Result 主要面向权威政府和健康网站，HowTo 搜索展示已停止，Sitelinks Search Box 也已停止。可以保留对其他消费者有用的 schema.org 数据，但教程不能承诺这些标记带来 Google 展示。

电商站应让页面可见信息、结构化数据和 Merchant Center feed 保持一致，尤其是产品标识、价格、币种、库存、变体、配送和退货政策。只有用户能在页面上购买的产品页才适合 Merchant Listing；仅供询价或完全登录后成交的 B2B 页面需要单独判断资格。

## 页面体验与 Core Web Vitals

当前 Core Web Vitals 是 LCP、INP 和 CLS，合格阈值按移动端和桌面端分别查看第 75 百分位：

- LCP 不高于 2.5 秒；
- INP 不高于 200 毫秒；
- CLS 不高于 0.1。

实验室数据和真实用户数据回答不同问题：

| 证据 | 适合回答的问题 | 主要限制 |
|---|---|---|
| Lighthouse | 在可控环境中定位加载、主线程、图片和脚本问题 | 模拟环境，不代表用户分布，不能直接测量 INP |
| CrUX | Chrome 用户在过去周期的真实体验和趋势 | 需要足够流量，数据按页面或 origin 聚合 |
| 自建 RUM | 自己用户、模板、地区和业务流程的实时表现 | 需要埋点、数据治理和长期维护 |

不要把 Lighthouse 分数和 CrUX 指标合成一个总分。修复时用 Lighthouse 和浏览器性能工具定位原因，再用 CrUX 或自建 RUM 观察真实用户变化。

## SEO Workbench 的证据层

Workbench 将证据分开保存，因为它们的观察范围不同：

| 层 | 命令 | 能确认什么 |
|---|---|---|
| 原始响应 | `./seo evidence --json` | 状态码、重定向、原始 HTML、元数据、robots、Sitemap、代表路由 |
| 浏览器渲染 | `./seo evidence --rendered --json` | JavaScript 执行后的 DOM、移动和桌面导航、raw/rendered 差异 |
| 技术栈 | `./seo technology --json` | 观察期内有证据的框架、平台、分析和第三方技术 |
| 实验室性能 | `./seo performance --json` | 多次 Lighthouse 运行及可复现的诊断线索 |
| 真实用户性能 | `./seo crux --json` | 当前与历史 CrUX 指标，可能从 URL 回退到 origin |
| Google Search | `./seo gsc collect --json` | Search Analytics、Sitemap 状态和已索引版本抽样 |
| 变化 | `./seo audit-diff --json` | 两个可比较快照之间的变化 |

技术检测只证明观察到了某项技术。没有检测到 GA4、GSC 验证标签或某个框架，不足以证明全站不存在它。运行时注入、交互后加载、受地区或同意状态限制的脚本都可能不在本次观察范围内。

diff 也必须先判断可比性。最终 URL、设备类型、CrUX 实际范围、GSC property、时间窗口或数据完整性不同，就不应把差异归类为回归。

## 从证据到任务

审计结果按影响和确定性排序：

1. 先处理阻止访问、抓取、渲染和索引的确定性故障；
2. 再处理影响核心页面理解、商品资格和用户完成任务的问题；
3. 性能优化要指向具体模板、资源或交互；
4. 内容项目需要同时说明用户价值、业务价值和所需资料；
5. 缺少证据时记录验证动作，不把推测写成故障。

修复完成后重新采集同范围证据，并用 audit diff 检查变化。排名和流量通常有更长反馈周期，应结合 GSC 的完整时间窗口观察，避免用一两天的数据下结论。

## 官方参考

- [Google 如何创建以用户为中心的可靠内容](https://developers.google.com/search/docs/fundamentals/creating-helpful-content)
- [Google JavaScript SEO 基础](https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics)
- [Google robots meta 规范](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag)
- [Google canonical 指南](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls)
- [Google 结构化数据总览](https://developers.google.com/search/docs/appearance/structured-data/search-gallery)
- [Google 电商 SEO 指南](https://developers.google.com/search/docs/specialty/ecommerce)
- [Google 对生成式 AI 内容的说明](https://developers.google.com/search/docs/fundamentals/using-gen-ai-content)
- [Web Vitals](https://web.dev/articles/vitals)
- [SEO Workbench Google 集成](google-integrations.md)
