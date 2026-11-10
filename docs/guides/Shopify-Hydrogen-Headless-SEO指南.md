# Shopify Hydrogen SEO 指南

本文适用于当前 Shopify Hydrogen、Oxygen 和自行托管的 Hydrogen。现代 Hydrogen 项目是预配置了 Shopify 能力的 React Router 应用。Next.js、Nuxt 和其他自建 Storefront 可以沿用本文的搜索原则，但路由、渲染和部署实现应以各自框架文档为准。

通用判断规则见 [SEO 基础知识与证据模型](SEO基础知识与证据模型.md)。

## 建立 Workbench 项目

```bash
./seo --project hydrogen-store init shopify-headless \
  --name "Hydrogen Store" \
  --url "https://example.com" \
  --framework hydrogen \
  --hosting oxygen \
  --cms shopify
```

如果内容来自 Sanity、Contentful 或其他 CMS，把真实 CMS 写进初始化参数和项目上下文。Shopify Blog 本身也可以通过 Storefront API 使用，Headless 不要求一定增加外部 CMS。

第一次基线：

```bash
./seo --project hydrogen-store evidence --rendered --technology --json
./seo --project hydrogen-store performance --json
```

Hydrogen 审计要同时看服务器返回的 HTML、浏览器渲染结果和最终 URL。只检测到 React 或 Shopify 不能证明 SSR、canonical 或结构化数据正确。

## 当前 Hydrogen 的请求链

```text
用户或爬虫请求
      │
      ▼
Oxygen 或自托管运行时
      │
      ├── React Router loader
      │     ├── Storefront API
      │     └── 可选内容或业务 API
      │
      ├── 服务端渲染和流式响应
      │
      └── 浏览器 hydration 与交互
```

正文可以通过服务端渲染直接出现在 HTML 中，也可以在流式响应的后续部分到达。Google 能处理 JavaScript 和流式页面，但核心商品、标题、链接、canonical 和时效敏感的 Product 数据优先在服务端输出，用户和其他爬虫也能更快拿到。

不要把所有延迟数据都视为 SEO 故障。推荐商品、个性化模块和交互组件可以延迟；产品名称、主要描述、价格状态和购买条件通常应随主响应提供。

## 使用当前 React Router metadata 接口

Hydrogen 提供 `getSeoMeta`，可以合并父路由和当前路由的 SEO 配置，并输出 canonical、Open Graph、robots 和 JSON-LD。

```tsx
import type {LoaderFunctionArgs, MetaFunction} from 'react-router';
import {getSeoMeta} from '@shopify/hydrogen';

export async function loader({params, context}: LoaderFunctionArgs) {
  const {product} = await context.storefront.query(PRODUCT_QUERY, {
    variables: {handle: params.handle},
  });

  if (!product) {
    throw new Response('Not found', {status: 404});
  }

  return {
    product,
    seo: {
      title: product.seo?.title || product.title,
      description: product.seo?.description || product.description,
      url: `https://example.com/products/${product.handle}`,
    },
  };
}

export const meta: MetaFunction<typeof loader> = ({data, matches}) =>
  getSeoMeta(matches[0]?.data?.seo, data?.seo);
```

代码结构会随项目版本变化，升级前查看当前 Hydrogen API。审计关注输出结果：

- 每个可索引 route 有准确 title 和描述；
- canonical 是绝对 URL，并与市场和变体策略一致；
- 404 route 返回 404，不是带错误文案的 200；
- 搜索、账户、购物车和无价值参数页有合适的索引策略；
- 父子路由没有生成重复或冲突 metadata。

## 路由设计先确定稳定 URL

Hydrogen 可以自定义 URL，但自由修改路径会增加迁移和重复风险。常见结构仍可保持 Shopify 用户熟悉的形式：

```text
/products/:handle
/collections/:handle
/blogs/:blogHandle
/blogs/:blogHandle/:articleHandle
/pages/:handle
/search
/account/*
```

同一资源不要同时提供多个可索引路径。筛选、排序、币种和追踪参数需要明确 canonical、noindex 和抓取策略。每个分页页面应有独立 URL 和普通链接。

无结果筛选、无效 handle 和不存在分页应返回 404。不要把所有未知路径重定向到首页，这会制造 soft 404。

## Sitemap 使用 Hydrogen 官方能力

当前 Hydrogen 提供 Sitemap route 生成器：

```bash
npx shopify hydrogen generate route sitemap
```

也可以在 route 中直接使用 `getSitemap`：

```tsx
import type {LoaderFunctionArgs} from 'react-router';
import {getSitemap} from '@shopify/hydrogen';

export async function loader({request, params, context}: LoaderFunctionArgs) {
  return getSitemap({
    storefront: context.storefront,
    request,
    params,
    locales: ['EN-US', 'ZH-CN'],
  });
}
```

生成后的 route 默认缓存，产品增加、下架和 locale 变化会在缓存更新后反映。自建 CMS 页面不一定在 Shopify 商品 Sitemap 中，需要确认生成 route 是否包含这些 URL，或增加独立 Sitemap 和 index。

不要手写一个无法分页读取完整目录的 XML。大目录还要检查单个 Sitemap 的 URL 数量、缓存更新和 API 分页。

## robots.txt 也有官方 route

```bash
npx shopify hydrogen generate route robots
```

Hydrogen quickstart 包含 robots route。部署到 Oxygen 时，非生产环境会被平台设置为禁止爬虫访问；生产环境需要自定义域名后才提供正式 robots.txt。这能减少预览部署进入索引的风险，但上线前仍要实际访问确认。

robots.txt 不负责 noindex。账户、购物车、搜索和其他不应出现在结果中的 route 应返回正确的 robots meta 或认证状态。

## Shopify Blog 仍然可用

Storefront API 提供 `Blog` 和 `Article`，包括文章正文、作者、图片、标签和 SEO 信息。可以直接在 Shopify Admin 管理内容，再通过 Hydrogen route 渲染：

```text
Shopify Admin Blog
      │
      ▼
Storefront API Blog / Article
      │
      ▼
React Router loader
      │
      ▼
服务端 HTML 和 Article metadata
```

外部 CMS 适合需要复杂内容模型、多人编辑、内容复用或更强媒体工作流的团队。选择 CMS 是产品和编辑决策，不是 Headless SEO 的强制要求。

无论使用哪种来源，都应输出准确作者、日期、正文、内部链接和适用的 Article 结构化数据。不要为了 E-E-A-T 虚构资质字段，也不要自动把 `updatedAt` 改成当前日期。

## Product 结构化数据来自同一份商品事实

产品 JSON-LD 应使用 Storefront API 返回的产品和变体数据，并与页面可见内容一致。重点检查：

- 产品名称、描述和图片；
- 品牌、SKU、GTIN 或 MPN；
- 变体 URL 和 `ProductGroup` 关系；
- 当前市场的价格、币种、库存；
- 配送、退货和适用的评价；
- 页面能否实际购买该商品。

Google 建议 Merchant Listing 的 Product 数据存在于初始 HTML。Hydrogen 的 `getSeoMeta` 支持 JSON-LD，也可以在 route 组件中输出 `application/ld+json` script。选择一种稳定方式，避免父子 route 和评价集成重复生成 Product。

Merchant Center feed 与页面 JSON-LD 应从相同商品系统同步。Markets、促销和变体切换尤其容易造成价格或库存不一致。

## Markets、语言和币种

Headless 项目要自己把市场上下文接入 URL、Storefront API 查询和 SEO 输出。每个 locale 版本需要：

- 独立稳定 URL；
- self-canonical；
- 指向所有替代版本的 hreflang；
- 与 URL 一致的语言、币种和商品可用性；
- Sitemap 中对应的 alternate 链接；
- 用户可见的语言和地区切换器。

不要让同一个 URL 根据 Cookie、IP 或浏览器语言返回完全不同的可索引内容。自动跳转不能阻止爬虫访问其他市场版本。

## Hydrogen Image 组件的实际边界

当前 `@shopify/hydrogen` 的 `Image` 组件使用 Storefront API Image 数据生成响应式图片。`aspectRatio` 或固定尺寸可以减少布局移动，`sizes` 和 srcset 决定浏览器选择的资源。

```tsx
import {Image} from '@shopify/hydrogen';

<Image
  data={product.featuredImage}
  sizes="(min-width: 48rem) 50vw, 100vw"
  aspectRatio="4/5"
  loading="eager"
/>
```

组件不会替你写准确 alt。Storefront API 图片数据应包含 `altText`，装饰图则使用空 alt。首屏主图的优先级根据实际 LCP 元素决定，不要把所有首屏缩略图都设为高优先级。

## 性能责任在服务器、数据和 hydration

Hydrogen 或 Oxygen 不保证页面天然快于 Liquid。主要风险包括：

- Storefront API 或 CMS 请求串行等待；
- 缓存策略不适合数据更新频率；
- 过大的客户端 JavaScript 和 hydration；
- 第三方营销、评价和同意脚本；
- 主图、字体和 CSS 阻塞 LCP；
- 个性化组件造成布局移动；
- 自托管运行时的区域、冷启动和资源限制。

分别测试首页、集合、产品和内容 route：

```bash
./seo --project hydrogen-store performance --json
./seo --project hydrogen-store performance --form-factor desktop --json
./seo --project hydrogen-store crux --json
```

Lighthouse 中的 TBT 可以辅助发现主线程问题，但不能代替真实用户 INP。使用 CrUX 或自建 RUM 判断用户分布和具体交互。

## 每次部署后的 raw/rendered 对比

```bash
./seo --project hydrogen-store evidence --rendered --crawl-limit 5 --json
./seo --project hydrogen-store audit-diff --json
```

检查：

- 请求 URL、最终 URL 和 canonical 是否一致；
- 原始 HTML 是否有核心内容和可抓取链接；
- 渲染后有没有删除或覆盖 title、canonical、robots 和 JSON-LD；
- 移动与桌面是否进入不同路由；
- 404 和错误边界是否保留正确状态码；
- Sitemap 和导航是否发现新 route。

## 上线检查清单

### 路由和索引

- [ ] 正常 route 返回 200，不存在资源返回 404
- [ ] 一个首选 HTTPS 主域名
- [ ] canonical、hreflang、内部链接和 Sitemap 一致
- [ ] 筛选、搜索、账户和购物车有明确索引策略
- [ ] 生产 robots.txt 可访问，预览部署保持不可索引
- [ ] Sitemap 覆盖 Shopify 和外部 CMS 的目标 URL

### 页面和商品

- [ ] 代表 route 有准确 metadata
- [ ] 商品、集合和内容正文在 raw 或可靠服务端响应中可用
- [ ] Product 数据与页面、市场和 Merchant Center 一致
- [ ] Blog 使用 Shopify 或外部 CMS 的决定已写入项目上下文
- [ ] 图片有正确尺寸和 alt
- [ ] 不存在重复冲突的 JSON-LD

### 性能和监测

- [ ] 关键 loader、缓存和错误处理已验证
- [ ] 代表 route 完成移动与桌面 Lighthouse
- [ ] 有流量时检查 CrUX URL 和 origin 范围
- [ ] GSC property 与正式域名和市场结构匹配
- [ ] 部署前后保存可比较审计快照

## 官方参考

- [Hydrogen and Oxygen fundamentals](https://shopify.dev/docs/storefronts/headless/hydrogen/fundamentals)
- [Hydrogen SEO](https://shopify.dev/docs/storefronts/headless/hydrogen/seo)
- [Hydrogen getSeoMeta](https://shopify.dev/docs/api/hydrogen/latest/utilities/getseometa)
- [Hydrogen getSitemap](https://shopify.dev/docs/api/hydrogen/latest/utilities/getsitemap)
- [Hydrogen Image](https://shopify.dev/docs/api/hydrogen/latest/components/media/image)
- [Storefront API Blog](https://shopify.dev/docs/api/storefront/latest/objects/Blog)
- [Storefront API Article](https://shopify.dev/docs/api/storefront/latest/objects/Article)
- [Google JavaScript SEO](https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics)
