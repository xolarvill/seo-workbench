# Shopify Liquid SEO 指南

本文适用于 Shopify Online Store 2.0 和 Liquid Theme。Hydrogen 店铺见 [Shopify Hydrogen SEO 指南](Shopify-Hydrogen-Headless-SEO指南.md)。通用判断规则见 [SEO 基础知识与证据模型](SEO基础知识与证据模型.md)。

Shopify 已经处理 HTTPS、基础 URL 模式、canonical、robots.txt 和 Sitemap 等底层能力。SEO 工作重点是确认主题和 App 没有破坏这些默认行为，再改善目录结构、商品数据、内容和页面体验。

## 建立 Workbench 项目

```bash
./seo --project shopify-store init shopify \
  --name "Shopify Store" \
  --url "https://example.com" \
  --framework liquid \
  --hosting shopify \
  --cms shopify
```

第一次采集：

```bash
./seo --project shopify-store evidence --rendered --technology --json
./seo --project shopify-store performance --json
```

技术识别可以发现主题外注入的评价、营销、分析、同意管理和支付技术。检测到技术不代表它影响所有模板，也不能单凭 App 数量推测性能。

## Shopify 已经提供什么

Shopify 官方当前提供：

- 自动生成的 `sitemap.xml` 和默认 `robots.txt`；
- 页面 canonical；
- 产品、集合、页面和博客的 SEO 标题、描述及 handle 编辑入口；
- HTTPS 和主域名管理；
- Shopify 主题必须具备的基础 SEO metadata 和产品结构化数据；
- Shopify Markets 下的 canonical、hreflang 和国际 Sitemap。

这些能力仍需要验证。第三方主题可能输出重复 title、canonical 或 JSON-LD，App 也可能在运行时添加脚本和结构化数据。

## 目录结构决定商品能否被发现

典型结构：

```text
首页
├── 集合
│   ├── 子集合或精选入口
│   └── 产品
├── 购买和使用指南
└── 品牌、联系和政策
```

菜单、集合页、产品推荐和内容链接共同表达页面关系。重要产品不应只能通过站内搜索或筛选器找到。

Shopify URL 路径有固定部分，如 `/products/`、`/collections/` 和 `/blogs/`。SEO 不需要为了删除这些路径迁移到 Headless。handle 应稳定、可读，修改后创建到新地址的 301 重定向。

## 产品页围绕购买决定组织信息

核心产品页应准确表达：

- 产品是什么，适合谁和什么场景；
- 关键规格、材质、尺寸、兼容性或使用限制；
- 变体之间的真实差异；
- 价格、币种、库存、配送和退货信息；
- 图片、视频、认证、测试或客户使用证据；
- 购买前常见问题及下一步。

描述长度由产品复杂度决定。简单耗材可能只需规格和几段说明，安全、兼容性或高客单产品需要更多证据。不要在所有产品上复制供应商描述，也不要给每张图片机械重复同一个关键词。

标题和 meta description 需要准确、独特、可读。Google 没有固定字符限制，但过长内容可能被截断或重写。大目录可以使用清楚的程序化模板，再优先人工编辑高价值产品。

## 集合页需要帮助用户选择

集合页的价值不取决于底部是否存在固定字数的文字。更重要的是：

- 集合范围和分类逻辑清楚；
- 商品可以通过可抓取链接访问；
- 筛选项与用户决策相关；
- 页面提供必要的选择说明、规格差异或购买建议；
- 空筛选和无效分页返回合理状态；
- 核心集合获得菜单、首页和相关文章的内部链接。

文字可以放在不会妨碍选购的位置，也可以拆成简短说明、比较表和 FAQ。不要添加与选择无关的长段落来制造“厚内容”。

## 参数、标签和重复 URL

产品可能通过集合路径、推荐组件和参数访问。Shopify 默认 canonical 通常会合并重复版本，仍应抽样确认：

```bash
./seo --project shopify-store evidence --rendered --crawl-limit 5 --json
```

检查以下 URL：

- 产品 clean URL 与集合上下文 URL；
- 排序、筛选和分页；
- 站内搜索；
- tags、vendor 和自动集合；
- Markets 的语言和地区 URL。

tags 或 vendor 页面不应一律 noindex。页面有独特商品集合、用户需求和内部链接时可以保留；大量重复、空或组合参数需要限制索引或抓取。robots.txt 只管理抓取，不能用于删除已经索引的 URL。

Google 已不再把 `rel="next"` 和 `rel="prev"` 当作索引信号。分页要有独立 URL 和可抓取链接，不能只依赖无限滚动。

## 不要轻易覆盖 robots.txt.liquid

Shopify 的默认 robots.txt 会随平台更新。只有确认具体抓取问题后才添加 `robots.txt.liquid`，优先追加规则，不要复制一份静态默认文件后长期不更新。

修改前后检查：

- 产品、集合、博客和必要资源仍可抓取；
- 参数规则没有误伤 canonical 页面；
- Sitemap 声明仍存在；
- 自定义规则符合 Google 和其他目标爬虫的语法。

## Sitemap 自动生成，但仍要检查

Shopify 在主域名根目录提供 `sitemap.xml`，并随产品、集合、页面、博客和图片更新。使用 Markets 时，每个国际域名也可能有对应 Sitemap。

在 GSC 网页端提交正确 property 下的 Sitemap。Workbench 的 GSC 接入是只读的：

```bash
./seo --project shopify-store gsc collect --json
```

Sitemap 成功读取只说明 Google 能处理文件，不代表每个商品已经收录。产品级问题继续用 URL Inspection 和 Page Indexing 报告判断。

## 结构化数据和 Merchant Center

Shopify 主题通常已经输出产品结构化数据。先验证现有 JSON-LD，再决定是否修改或增加 App，避免同一产品出现多份互相冲突的价格、库存和评价。

产品页重点检查：

- `Product` 和具体 `Offer`；
- 商品标识，如品牌、SKU、GTIN 或 MPN；
- 变体 URL 与价格、币种、库存的一致性；
- 页面可见评价与 `AggregateRating` 的一致性；
- 配送和退货信息；
- 结构化数据是否存在于初始或可靠渲染后的 HTML。

Google 建议同时使用页面结构化数据和 Merchant Center feed，提高商品数据覆盖和验证能力。两边发生冲突时应修复数据源，不要只改 JSON-LD 来通过测试。

FAQPage、HowTo 和 Sitelinks Search Box 不再是普通 Shopify 站的默认 Rich Result 机会。继续提供用户需要的 FAQ，但不要承诺 FAQ Schema 会显示下拉结果。

## 内容战略连接商品与使用场景

Shopify Blog 可以承载购买指南、产品比较、使用方法、维护、案例和品牌知识。内容选题来自真实客户任务：

- 购买前需要理解的规格和差异；
- 选择错误可能造成的成本或风险；
- 产品使用、保养和故障排查；
- 材料、工艺、认证和测试过程；
- 客户案例和适用边界。

每篇内容应在自然位置链接到相关集合或产品，也应让产品页链接回有助于决策的内容。链接数量由用户需要决定，不设每篇固定数量。

使用本地 `keyword-deep-dive` 和 `content-brief` skill 时，让 agent 读取产品数据、客服问题和品牌资料，避免只根据 SERP 改写竞品。

## Shopify Markets

Markets 可以用子目录、子域或独立域名承载不同语言和地区。Shopify 会为已配置的市场生成 self-canonical、hreflang 和国际 Sitemap。

仍需检查：

- 每个市场 URL 有真实本地化内容、币种和商品可用性；
- 语言和地区切换器可以正常访问其他版本；
- 不依赖强制 IP 跳转阻止爬虫访问；
- GSC property 和数据分析范围与市场结构匹配；
- 翻译没有把品牌、规格、单位或法律信息改错。

## 性能以模板和资源为单位

主题、图片、字体、第三方 App、同意管理和营销脚本都会影响性能。App 数量不是性能指标，一个 App 也可能注入大量脚本，多个轻量 App 也可能没有明显影响。

分别测试首页、核心集合和代表产品：

```bash
./seo --project shopify-store performance --json
./seo --project shopify-store crux --json
```

Lighthouse 用来定位 LCP 图片、阻塞脚本、主线程任务和布局移动。CrUX 用来观察真实用户的 LCP、INP 和 CLS。只有在请求和最终 URL、设备及测试环境相同时才比较 Lighthouse 快照。

图片优化包括正确尺寸、响应式候选、稳定宽高、合理的首屏优先级和有意义的 alt。装饰图片使用空 alt，不要给所有图片塞入商品关键词。

## 上线和主题更新检查清单

### Shopify 配置

- [ ] 主域名和 HTTPS 正常
- [ ] `sitemap.xml`、`robots.txt` 可访问
- [ ] 产品、集合、页面和博客 SEO 字段已抽样检查
- [ ] handle 修改有 301 重定向
- [ ] Markets URL、canonical 和 hreflang 抽样正确

### 商品和内容

- [ ] 核心集合可以通过导航到达
- [ ] 重要产品可以从集合和相关内容到达
- [ ] 产品数据足以支持购买决定
- [ ] 页面、JSON-LD 和 Merchant Center 数据一致
- [ ] 评价标记只包含页面可见的真实评价
- [ ] About、Contact、配送、退货和隐私政策准确

### 技术和性能

- [ ] raw 与 rendered 中没有 title、canonical 或正文冲突
- [ ] 不存在产品和筛选页返回正确状态码
- [ ] 主题与 App 没有输出重复冲突的结构化数据
- [ ] 代表模板已运行 Lighthouse
- [ ] 有流量时已检查 CrUX 移动端和桌面端
- [ ] GSC 只读证据和审计基线已保存

## 官方参考

- [Shopify SEO overview](https://help.shopify.com/en/manual/promoting-marketing/seo/seo-overview)
- [Shopify Sitemap](https://help.shopify.com/en/manual/promoting-marketing/seo/find-site-map)
- [Shopify robots.txt.liquid](https://help.shopify.com/en/manual/promoting-marketing/seo/editing-robots-txt)
- [Shopify Theme SEO metadata](https://shopify.dev/docs/storefronts/themes/seo/metadata)
- [Shopify Markets 国际 SEO](https://help.shopify.com/en/manual/markets/seo)
- [Google 电商 SEO 指南](https://developers.google.com/search/docs/specialty/ecommerce)
