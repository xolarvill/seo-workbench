# 自建普通网站 SEO 指南

本文适用于没有 WordPress、Shopify、Next.js 等平台能力的普通网站，例如静态 HTML、PHP 模板、Java/JSP、ASP.NET、服务端模板或公司内部开发的网站。

“没有特殊技术框架”不会让 SEO 更简单。平台原本会代为处理的状态码、metadata、canonical、Sitemap、结构化数据、缓存和发布检查，现在都由网站团队自己负责。好处是行为可控，风险是错误也更容易被复制到全站。

通用判断规则见 [SEO 基础知识与证据模型](SEO基础知识与证据模型.md)。

## 建立 Workbench 项目

```bash
./seo --project custom-site init general \
  --name "Custom Site" \
  --url "https://example.com" \
  --description "业务、客户、地区、产品或服务范围" \
  --framework server-rendered \
  --hosting self-hosted \
  --cms custom
```

先保存基线：

```bash
./seo --project custom-site evidence --rendered --technology --json
./seo --project custom-site performance --json
./seo --project custom-site audit-diff --json
```

技术识别结果很少并不等于网站有问题。探针只能报告可观察到的服务器、HTML、脚本、Cookie、DNS 和运行时信号。自研系统没有公开指纹时，应把结论写成“未识别到已知框架”，不能写成“网站没有技术栈”。

## 先定义每个 URL 的技术合同

每种页面模板都应明确下面这些行为：

| 合同 | 正常行为 |
|---|---|
| 成功页面 | 返回 `200`，包含主要正文和可抓取链接 |
| 永久迁移 | 返回 `301` 或 `308`，尽量一次跳到最终 URL |
| 临时跳转 | 只在确实临时时使用 `302` 或 `307` |
| 不存在页面 | 返回真正的 `404` 或 `410`，不能显示错误页却返回 `200` |
| 主版本 | HTTPS、主机名、尾斜杠和大小写规则一致 |
| 索引控制 | HTML `robots` 或 HTTP `X-Robots-Tag` 与页面用途一致 |
| 规范地址 | canonical 指向希望保留的可索引 URL |
| 内容输出 | 关键标题、正文和链接在初始 HTML 或可可靠渲染的 DOM 中存在 |

抽样检查首页、栏目页、详情页、搜索页、分页、重定向和不存在 URL。不要只检查一个首页。

如果访问根域名会跳到语言目录，例如 `/gongkongWeb/`，先确认这是有意的信息架构还是历史部署遗留。最终首页可以位于子目录，但应满足：

- 根 URL 使用单次永久重定向；
- 跳转目的地长期稳定；
- canonical、Sitemap、内部链接和 hreflang 使用同一版本；
- 用户和搜索爬虫不会因 User-Agent、Cookie 或 IP 获得矛盾跳转；
- 目录名具有可维护性，不依赖临时项目名。

## HTML head 的最低要求

每个可索引页面至少输出与页面一致的 title、description、canonical 和移动端 viewport。示例：

```html
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>页面主题与品牌</title>
  <meta name="description" content="准确概括页面能解决的问题，不复制全站通用文案。">
  <link rel="canonical" href="https://example.com/products/example/">
  <meta name="robots" content="index,follow">
  <meta property="og:title" content="页面主题与品牌">
  <meta property="og:description" content="用于分享预览的准确说明。">
  <meta property="og:url" content="https://example.com/products/example/">
</head>
```

字符数只能作为预览风险提示，不是排名规则。更重要的是标题能区分页面、描述不误导、canonical 由当前路由生成，而不是所有页面硬编码成首页。

`noindex` 页面必须允许爬虫读取该指令。不要同时用 `robots.txt` 阻止访问，然后期待搜索引擎看到页面中的 `noindex`。

## 路由和信息架构

用业务结构设计 URL，而不是用服务器文件结构设计 URL：

```text
/
├── products/ 或 services/
│   ├── category-a/
│   └── item-or-service/
├── solutions/
│   └── industry-or-use-case/
├── resources/
│   └── guide-or-case-study/
├── about/
└── contact/
```

原则：

- 重要页面可以从导航、栏目或正文链接到达；
- 链接使用真实 `<a href>`，不要只绑定 JavaScript 点击事件；
- URL 表达稳定对象，标题变化不应频繁改变地址；
- 删除或合并页面时映射到最相关的新页面，不要全部跳首页；
- 参数 URL、打印页和重复详情页要有明确保留、canonical 或关闭策略；
- 分页使用可抓取的顺序链接，每页可以独立返回内容。

## robots.txt 与 Sitemap

最小 `robots.txt` 可以很简单：

```text
User-agent: *
Disallow: /admin/
Disallow: /internal-search/

Sitemap: https://example.com/sitemap.xml
```

`robots.txt` 是抓取管理工具，不是可靠的移除索引工具，也不是访问控制。管理后台和私有文件需要认证，不能只靠 `Disallow`。

Sitemap 只列入你希望索引的 canonical URL，并确保它们返回 `200`。如果是自研生成器，至少验证：

- XML 能被解析，URL 使用绝对地址；
- 不包含重定向、404、noindex、登录后或重复 URL；
- `lastmod` 来自真实内容更新时间，不是每次部署全部刷新；
- 大站按类型拆分 Sitemap 并使用 Sitemap index；
- 发布、迁移和删除页面后能自动更新。

提交 Sitemap 只是发现线索，不保证抓取或索引。

## 内容体系适合普通公司站

一个可靠的公司站通常需要四类公开页面：

1. 产品或服务页：说明具体提供什么、适用条件、规格、流程和下一步动作。
2. 行业或解决方案页：围绕客户问题连接多个产品、服务和案例。
3. 证据页：公司、团队、资质、方法、案例、政策和联系方式。
4. 知识页：回答研究、选型、比较、实施和维护问题。

不要用同一段公司介绍替换不同页面的主要内容，也不要为了覆盖城市或关键词批量生成只有名称不同的页面。页面长度由任务复杂度决定，没有统一最低字数。

如果网站是中文原文再自动翻译，需特别检查：

- 翻译是否准确、完整并符合目标市场术语；
- 每个语言版本是否有独立稳定 URL；
- `html lang` 和可选的 hreflang 是否正确；
- 用户能否切换语言，且不会因 Cookie 强制跳转；
- 不同语言的 title、description、图片文字和表单是否也被本地化；
- 低质量机器翻译是否真的能帮助用户，而不是仅用于扩大索引页数。

## JavaScript 和渲染

普通站点常把菜单、产品列表或正文通过 Ajax 注入。搜索引擎可以处理部分 JavaScript，但服务端输出关键内容更容易验证，也减少渲染失败带来的不确定性。

至少确保：

- 初始 HTML 有页面主题、主要内容或清晰的加载路径；
- 关键链接有可抓取 `href`；
- API 失败时不会得到空白 `200` 页面；
- JavaScript 生成的 canonical、robots 和结构化数据与原始 HTML 不冲突；
- 桌面和移动端不会进入不同或错误的首页；
- 关闭 JavaScript后的退化行为不会隐藏所有业务信息。

Workbench 的 rendered evidence 用于比较原始 HTML 和浏览器渲染结果：

```bash
./seo --project custom-site evidence --rendered --crawl-limit 5 --json
```

## 结构化数据只描述页面事实

按页面类型选择官方支持的 schema，例如 Organization、BreadcrumbList、Product、Article 或 LocalBusiness。结构化数据不是把所有业务字段塞进 JSON-LD 的地方。

要求：

- 字段与用户可见内容一致；
- 价格、库存、评价、作者和日期真实；
- 每个实体使用稳定 URL 或 `@id`；
- 发布前通过 Google Rich Results Test 和 Schema Markup Validator 检查；
- 没有适合的富媒体类型时，保持语义清楚即可，不必强行添加。

FAQ 和 HowTo 标记不能被当作通用流量开关。是否有搜索展示资格取决于 Google 当前支持范围，页面本身仍应先帮助用户。

## 性能从服务器和资源链路定位

```bash
./seo --project custom-site performance --json
./seo --project custom-site crux --json
```

Lighthouse 是实验室证据，CrUX 是满足数据门槛后的真实用户证据，两者不要合成一个分数。

自建站优先检查：

- DNS、TLS、服务器处理和数据库造成的 TTFB；
- HTML、CSS、JavaScript、字体和图片的缓存策略；
- Brotli 或 gzip 压缩；
- 首屏图片尺寸、格式、宽高属性和加载优先级；
- 阻塞渲染的 CSS、同步脚本和第三方标签；
- 交互后的布局变化和主线程长任务；
- CDN 缓存是否尊重 Cookie、语言和登录状态。

不要为了 Lighthouse 分数删除业务必要功能。先确认真实瓶颈、用户影响和修复后的回归风险。

## 分析、GSC 和隐私

自建网站没有默认的搜索或转化测量。至少完成：

- 验证 GSC Domain 或 URL-prefix property；
- 提交并监测 Sitemap；
- 检查代表 URL 的已索引版本和 canonical；
- 记录表单成功、电话、邮件、下载或购买等业务事件；
- 对 GA4、百度统计或其他脚本实施适用的同意与隐私规则；
- 避免在 URL、日志和审计产物中保存敏感表单内容。

```bash
./seo --project custom-site gsc collect --json
```

GSC 未接入时，Workbench 会把它报告为认证交接，不应把它误判为站点故障。若网站只使用百度统计，也不能由此推断 Google 是否抓取或索引，仍需用 GSC 或公开搜索证据验证。

## 把 SEO 检查放进发布流程

自建系统最值得补的是自动化契约测试。每次发布至少抽样验证：

- 关键路由和错误路由的状态码；
- title、canonical、robots、hreflang 和结构化数据；
- 导航与正文内部链接；
- Sitemap 是否包含新 URL 并移除失效 URL；
- CSS、JavaScript、图片和字体没有 404；
- 表单和转化事件仍然工作；
- 代表页面的性能没有显著回退。

发布前后保存不可变审计，再做可比 diff：

```bash
./seo --project custom-site evidence --rendered --technology --performance --json
./seo --project custom-site audit-diff --json
```

如果最终 URL、运行环境或采集范围不同，先解决可比性，不要把差异直接定性为 SEO 回归。

## 上线检查清单

### 抓取与索引

- [ ] HTTP、HTTPS 和不同主机名收敛到唯一版本
- [ ] 成功、重定向、404 和 410 状态码真实
- [ ] canonical、内部链接和 Sitemap 使用同一 URL 规则
- [ ] noindex 页面没有同时被 robots.txt 阻断
- [ ] 管理与私有区域有认证，而不只依赖 robots.txt
- [ ] 参数、搜索、打印和重复页面有明确策略

### 页面与内容

- [ ] 每个主要页面有独立任务和可辨识 title
- [ ] 关键正文和链接可以在原始或可靠渲染的 HTML 中读取
- [ ] 产品、服务、解决方案、证据和知识页面互相连接
- [ ] 移动端没有缺失正文、错误跳转或不可用交互
- [ ] 多语言版本由用户可切换，翻译经过质量检查
- [ ] 结构化数据与页面可见事实一致

### 性能与运营

- [ ] 代表模板完成 Lighthouse，数据足够时检查 CrUX
- [ ] 缓存、压缩、图片和第三方脚本已经检查
- [ ] GSC property、Sitemap 和代表 URL Inspection 已配置
- [ ] 表单、电话、下载或购买事件可以测量
- [ ] 发布流程能检查核心 SEO 合同
- [ ] 修复前后保留 Workbench 证据和可比 diff

## 官方参考

- [Google SEO Starter Guide](https://developers.google.com/search/docs/fundamentals/seo-starter-guide)
- [Google HTTP 状态码与网络错误](https://developers.google.com/search/docs/crawling-indexing/http-network-errors)
- [Google robots.txt 说明](https://developers.google.com/search/docs/crawling-indexing/robots/intro)
- [Google Sitemap 构建与提交](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap)
- [Google JavaScript SEO 基础](https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics)
- [Google 结构化数据通用指南](https://developers.google.com/search/docs/appearance/structured-data/sd-policies)
- [web.dev Core Web Vitals](https://web.dev/articles/vitals)
