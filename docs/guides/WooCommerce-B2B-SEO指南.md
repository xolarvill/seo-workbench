# WooCommerce B2B SEO 指南

本文适用于使用 WordPress 和 WooCommerce 展示工业品、原材料、零部件、设备或批发商品，并通过询价、账户审批、分级价格或批量订单成交的 B2B 网站。

B2B WooCommerce 的 SEO 难点通常不在文章数量，而在公开目录和登录后商务信息的边界。搜索爬虫以访客身份访问。如果产品、规格和分类全部登录后可见，搜索引擎就无法用这些页面承接采购需求。

通用判断规则见 [SEO 基础知识与证据模型](SEO基础知识与证据模型.md)。

## 建立 Workbench 项目

```bash
./seo --project b2b-woocommerce init general \
  --name "B2B WooCommerce" \
  --url "https://example.com" \
  --description "行业、采购角色、产品范围和询价流程" \
  --framework wordpress \
  --hosting managed-wordpress \
  --cms woocommerce
```

第一次采集：

```bash
./seo --project b2b-woocommerce evidence --rendered --technology --json
./seo --project b2b-woocommerce performance --json
```

技术识别应特别关注 WordPress、WooCommerce、主题、缓存、CDN、B2B/wholesale、询价、表单、同意管理和分析技术。未识别出某个插件不代表它不存在，登录后模块和条件加载脚本可能不在访客证据里。

## 先画出公开和私有边界

常见 B2B 商店有三种模式：

| 模式 | 访客看到什么 | SEO 影响 |
|---|---|---|
| 公开购买 | 商品、价格和购买按钮都公开 | 可以按普通电商处理，适合 Merchant Listing |
| 公开目录加询价 | 商品和规格公开，价格隐藏或显示询价 | 可以承接产品搜索，但商品展示资格要按实际购买能力判断 |
| 私有批发门户 | 目录、价格和订单仅登录后可见 | 登录后区域不能承担公开自然搜索获客 |

混合 B2B+B2C 站还可能按角色、地区或客户组显示不同价格和商品。把这些规则记录在项目 `context/`，审计时明确“匿名访客”“已批准客户”和“搜索爬虫”看到的内容是否相同。

适合多数获客型 B2B 站的边界：

```text
公开并可索引
├── 产品分类、系列和产品详情
├── 规格、兼容性、应用、认证和案例
├── 公司、工厂、服务范围和联系信息
└── 询价入口和注册说明

登录后或不索引
├── 客户专属价格、折扣和合同条款
├── 订单、账户、付款和发票
├── 私有文件和客户项目
└── 报价历史与审批流程
```

公开页面可以不显示价格，但应让采购人员确认产品是否符合需求，并提供清楚的询价路径。完全私有目录适合已有客户下单，公开获客需要另外建设可索引的产品和解决方案页面。

## B2B 搜索意图围绕采购任务

B2B 关键词经常包含：

- 产品名称、型号、SKU、标准件编号或替代型号；
- 材质、尺寸、负载、精度、温度、接口和认证；
- 行业、设备、工艺和应用场景；
- manufacturer、supplier、factory、distributor、wholesale、OEM、ODM；
- datasheet、manual、CAD、SDS、certificate、lead time、MOQ；
- 地区、交付能力和售后服务。

研究查询时同时识别采购角色：工程师关心规格和兼容性，采购关心 MOQ、交期和供应能力，管理者关心风险、总成本和案例。一个页面可以服务多个角色，但主要任务要清楚。

不要根据搜索量排除型号和长尾规格词。它们的流量可能很低，询价价值却很高。把 GSC 查询、站内搜索、销售邮件、RFQ 表单和客服问题放在一起分析。

## 推荐页面体系

### 产品分类页

分类页帮助采购人员缩小选择，应包含：

- 分类范围和主要差异；
- 可筛选的关键规格；
- 产品链接和简要比较；
- 适用行业、标准和使用边界；
- 需要帮助选型时的联系入口。

不要在商品表格下面堆固定字数的通用介绍。分类说明要帮助选型，并链接到规格、应用和产品详情。

### 产品详情页

详情页常见模块：

- 产品名称、型号和一句准确说明；
- 参数表、尺寸、材质、标准和公差；
- 变体与选型规则；
- 应用、兼容设备和限制；
- 图纸、手册、证书和安全资料；
- 包装、MOQ、交期或询价条件；
- 售后、质保和联系信息；
- Add to Quote、Request a Sample 或购买动作。

参数不要只放在无法读取的图片或 PDF 中。HTML 页面提供核心规格，PDF 作为可下载的完整资料，并为 PDF 使用稳定 URL、正确响应头和必要的 `X-Robots-Tag` 策略。

### 解决方案和行业页

当产品需要结合设备、流程或行业选择时，建立应用页：

- 用户面临的工况和约束；
- 可选产品和选型理由；
- 安装或集成方式；
- 实际案例、测试或结果；
- 风险、限制和不适用情况；
- 需要哪些信息才能出具报价。

这些页面连接信息型和交易型需求，也为产品页提供更有意义的内部链接。

## WooCommerce URL、分类和筛选

WooCommerce 常见路径包括产品、product category、tag、attribute、搜索和参数 URL。主题、SEO 插件和筛选插件会改变实际输出，不能按默认印象处理。

抽样检查：

```bash
./seo --project b2b-woocommerce evidence --rendered --crawl-limit 5 --json
```

重点观察：

- 同一产品是否存在多个可索引 URL；
- product category、tag 和 attribute archive 是否有独特用途；
- 排序、价格、规格组合是否制造大量参数 URL；
- 空筛选、无效分页和不存在产品是否返回 404；
- 站内搜索、购物车、结账、账户和询价列表是否 noindex；
- 分页产品能否通过普通链接访问。

不要一律关闭所有 attribute archive。具有真实搜索需求和稳定商品集合的属性可以建设为落地页；临时组合和近乎无限的筛选参数应限制抓取或索引。canonical 只能缓解重复，不能代替合理的 URL 空间设计。

## 产品可见性和缓存需要一起测试

B2B 插件经常按用户角色隐藏产品、价格或整个目录，也可能有自己的 visibility cache。页面缓存、对象缓存和 CDN 如果不了解用户角色，可能把客户价格缓存给访客，或把隐藏页面缓存给搜索爬虫。

测试至少覆盖：

- 未登录访客；
- 普通注册用户；
- 已批准批发客户；
- 搜索爬虫可见的匿名 HTML；
- 缓存冷启动和命中后的响应。

涉及价格和账户信息时，这也是安全与隐私检查。不要把客户专属价格、报价或联系方式写入可公开缓存的 HTML 和审计附件。

## 结构化数据按成交模式决定

公开可购买商品可以使用面向商家的 Product 和 Offer 数据，并与页面、WooCommerce 和 Merchant Center 保持一致。

仅询价页面需要谨慎：

- 不要虚构公开价格、库存或购买能力；
- 页面不是直接购买入口时，不要承诺 Merchant Listing 资格；
- 可以用 Product 描述真实产品属性，但应验证 Google 当前支持的字段和资格；
- 客户专属价格不能出现在匿名页面 JSON-LD；
- 评价和 AggregateRating 必须与页面可见的真实评价一致。

混合站可以让公开零售商品进入 Merchant Center，把仅供询价或登录后定价的产品留在普通搜索和业务目录中。

## WordPress Sitemap 与 SEO 插件

WordPress Core 自 5.5 起具备 XML Sitemap 系统，SEO 插件也可能接管 Sitemap、canonical、robots 和 metadata。只保留一个明确的数据来源，避免同时输出两套 Sitemap 或多份 canonical。

Sitemap 应包含：

- 希望公开索引的产品、分类、解决方案和内容页；
- 返回 200 的 canonical URL；
- 正确的更新时间。

排除购物车、结账、账户、询价历史、内部搜索和私有内容。Sitemap 成功读取不等于页面已经索引。

## 性能优化不要只数插件

WordPress 和 WooCommerce 性能受主机、PHP、数据库查询、主题、插件、缓存、图片和第三方脚本共同影响。B2B 价格和可见性规则还会增加动态查询和缓存分支。

测试首页、分类、产品和询价流程：

```bash
./seo --project b2b-woocommerce performance --json
./seo --project b2b-woocommerce crux --json
```

优先检查：

- HTML TTFB 和服务端查询；
- 页面缓存是否适用于访客，登录用户是否正确绕过；
- 持久对象缓存和数据库热点；
- 产品表格、筛选和变体脚本；
- 首屏图片、字体和主题 CSS；
- 询价、聊天、分析和同意脚本；
- 大量下载文件是否由合适的静态存储或 CDN 提供。

逐个停用插件是定位方法之一，但必须在测试或 staging 环境中进行，并验证报价、角色和缓存没有被破坏。

## GSC 和业务转化一起看

```bash
./seo --project b2b-woocommerce gsc collect --json
```

GSC 可以告诉你哪些页面、查询、设备和国家带来展示和点击，不能告诉你询价质量和最终成交。至少把这些业务事件保存在自己的分析或 CRM：

- RFQ 提交；
- 样品申请；
- 规格书或 CAD 下载；
- 账户申请；
- 电话、邮件或会议预约；
- 合格询盘、报价和成交。

不要把客户名称、报价内容和 CRM 数据写入 Git 或公开审计。Workbench 当前不直接接入 CRM，报告只需说明 SEO 页面与业务事件如何对应。

## B2B 上线检查清单

### 公开与私有边界

- [ ] 匿名访客能看到用于获客的产品、分类和规格
- [ ] 客户价格、报价、订单和账户数据需要认证
- [ ] 角色与缓存组合不会泄露价格或私有内容
- [ ] 登录、账户、购物车、结账和报价历史不进入索引
- [ ] 私有目录另有公开获客页面

### 商品和内容

- [ ] 产品型号、规格、单位和认证准确
- [ ] 核心规格存在于 HTML，不只存在于图片或 PDF
- [ ] 分类页能帮助采购人员选型
- [ ] 解决方案页连接应用、产品和案例
- [ ] 询价表单说明需要提交哪些信息
- [ ] 页面没有虚构价格、库存、案例或资质

### 技术和测量

- [ ] 产品、分类、筛选和分页 URL 已抽样检查
- [ ] 只有一套明确的 metadata 和 Sitemap 来源
- [ ] Product 数据符合公开成交模式
- [ ] 代表模板完成 Lighthouse，流量足够时检查 CrUX
- [ ] GSC property、Sitemap 和已索引版本已检查
- [ ] RFQ、样品、下载和合格询盘有自有测量
- [ ] 修复前后保存 Workbench 审计快照

## 官方参考

- [WooCommerce B2B & Wholesale Suite](https://woocommerce.com/document/b2b-wholesale-suite/)
- [WooCommerce B2B request a quote](https://woocommerce.com/document/b2b-for-woocommerce/)
- [WordPress XML Sitemaps API](https://developer.wordpress.org/reference/functions/wp_sitemaps_get_server/)
- [WordPress performance optimization](https://developer.wordpress.org/advanced-administration/performance/optimization/)
- [Google 电商站点结构](https://developers.google.com/search/docs/specialty/ecommerce/help-google-understand-your-ecommerce-site-structure)
- [Google faceted navigation](https://developers.google.com/crawling/docs/faceted-navigation)
- [Google Merchant Listing](https://developers.google.com/search/docs/appearance/structured-data/merchant-listing)
