# Shopify Hydrogen / Headless SEO 建设指南

使用 SuperSEO + SEO Machine + Claude SEO 为一个 Headless Shopify 站（Hydrogen + Oxygen 或 Hydrogen 自托管）搭建 SEO 体系。

---

## 一、Headless Shopify SEO 的特殊性

### 1.1 先搞清楚你在用什么

Shopify 电商站现在有三条技术路线:

| 方案 | 前端 | 托管 | SEO 控制力 |
|------|------|------|-----------|
| **Liquid (Online Store 2.0)** | Liquid 模板 + Theme | Shopify 托管 | 受限于 Theme 框架 |
| **Hydrogen + Oxygen** | Remix (React) | Shopify Oxygen | 完全控制，但需自己建设 |
| **Hydrogen 自托管** | Remix (React) | 任意 Node 环境 | 完全控制 + 自行运维 |
| **第三方 Headless** | Next.js / Nuxt / 其他 | Vercel / Netlify / 自建 | 完全控制 + Shopify 无关 |

本指南覆盖后三种，统称「Headless 方案」。

### 1.2 Liquid vs Headless: 差异对照表

| 维度 | Liquid 传统站 | Headless 站 |
|------|--------------|-------------|
| **URL 结构** | 强制 `/products/xxx` `/collections/xxx` | 完全自定义，你想用什么路径都行 |
| **模板系统** | Liquid 模板，Theme 框架约束 SEO 输出 | React 组件，每一个 HTML 标签你都可控 |
| **渲染方式** | 纯 SSR（Shopify 服务器渲染 Liquid） | SSR + Streaming + 可选 SSG/ISR |
| **Schema** | theme.liquid 写死或 App 注入 | 程序化 JSON-LD，数据从 Storefront API 动态获取 |
| **Sitemap** | 自动生成，不可精细控制 | 自己写，完全可控 |
| **robots.txt** | 自动生成 | 自己写 resource route |
| **Blog** | Shopify 内置 Blog（功能有限） | 不存在，需对接 Headless CMS |
| **图片优化** | 手动处理或安装 App | Hydrogen `<Image>` 内置 + Oxygen CDN 自动转格式 |
| **性能** | 受 App 数量拖累 | 天生轻量，但 hydration 有成本 |
| **App 生态** | 一键安装，App 在 Shopify 服务器运行 | 需要 API 级集成，部分 App 不支持 headless |

### 1.3 自由的代价

Headless 让你完全控制 SEO，但也意味着 **Shopify 帮你自动做的事现在全要自己来**:

- Shopify 自动生成 sitemap → 你得自己写
- Shopify 自动处理 canonical → 你得每个 route 自己设
- Shopify 自动生成 Product Schema → 你得自己构建 JSON-LD
- Shopify 自动处理分页的 `rel="next"` / `rel="prev"` → 你得自己实现
- Shopify Theme 自带响应式图片 → 你得用 `<Image>` 组件正确配置

**好消息是**：Liquid 方案的那些「先天不足」（URL 不可控、Blog 太弱、App 拖慢速度）在 Headless 方案里全部消失。你能建出一个 SEO 远强于 Liquid 的站——前提是你知道该做什么。

### 1.4 Hydrogen 架构速览 (Remix)

```
用户请求 → Oxygen/CDN Edge
              │
              ├─ Remix Loader (server.ts/loader)
              │   ├─ 调用 Shopify Storefront API
              │   ├─ 调用 Headless CMS API
              │   └─ 返回数据给组件
              │
              ├─ React 组件渲染 (SSR)
              │   ├─ <MetaFunction> → <head> 标签
              │   └─ 组件树 → HTML body
              │
              └─ 流式传输 HTML → 浏览器
                   └─ Hydration (客户端 React 接管)
```

对 SEO 关键的点:**Google 抓取到的是 SSR 输出的完整 HTML**，不需要 JS 渲染。但要注意:
- Streaming 可能导致部分内容在抓取时被截断
- 第三方 Headless CMS 内容必须过 SSR，不能纯客户端 fetch

---

## 二、Hydrogen 技术栈 SEO 基线

### 2.1 MetaFunction: 每个 Route 的 SEO 入口

Remix 的 `MetaFunction` 是设置所有 `<head>` 标签的地方。**每个 route 都要有**，不要只靠 root。

```tsx
// app/routes/products.$handle.tsx
import type { MetaFunction, LoaderFunctionArgs } from '@shopify/remix-oxygen';
import { useLoaderData } from '@remix-run/react';

export const loader = async ({ params, context }: LoaderFunctionArgs) => {
  const { product } = await context.storefront.query(PRODUCT_QUERY, {
    variables: { handle: params.handle },
  });
  if (!product) throw new Response('Not Found', { status: 404 });
  return { product };
};

export const meta: MetaFunction<typeof loader> = ({ data }) => {
  if (!data) {
    return [{ title: 'Product Not Found' }];
  }
  const { product } = data;

  return [
    { title: `${product.title} — ${product.productType} | ${shopName}` },
    { name: 'description', content: product.description?.slice(0, 155) },
    { tagName: 'link', rel: 'canonical', href: `https://yourshop.com/products/${product.handle}` },
    { name: 'robots', content: 'index, follow' },
    // OG tags
    { property: 'og:title', content: product.title },
    { property: 'og:description', content: product.description?.slice(0, 200) },
    { property: 'og:image', content: product.featuredImage?.url },
    { property: 'og:type', content: 'product' },
    // Twitter Card
    { name: 'twitter:card', content: 'summary_large_image' },
    { name: 'twitter:title', content: product.title },
    { name: 'twitter:image', content: product.featuredImage?.url },
  ];
};
```

### 2.2 全局 Meta 兜底 (root.tsx)

```tsx
// app/root.tsx
export const meta: MetaFunction = () => {
  return [
    { title: 'Your Shop Name' },
    { name: 'description', content: 'Your shop description — 150 chars max' },
    { tagName: 'link', rel: 'canonical', href: 'https://yourshop.com' },
    { property: 'og:site_name', content: 'Your Shop Name' },
    { name: 'twitter:site', content: '@yourhandle' },
  ];
};
```

### 2.3 流式 SSR 与爬虫兼容性

Hydrogen 默认使用 React 的 `renderToPipeableStream` 进行流式 SSR。Google 能处理流式 HTML，但有几个要点:

- **关键的 SEO 标签必须在 Suspense 边界之外渲染**（`<title>`, `<meta description>`, canonical, hreflang, JSON-LD）。这些如果被 Suspense 包裹，可能在第一帧 HTML 中丢失。
- **JSON-LD 不要放在 Suspense 里**。Google 解析 JSON-LD 时不一定等待 Suspense resolve。
- **内容正文优先 SSR**。产品描述、Blog 正文等信息型内容不要懒加载——让它们在第一帧 HTML 中直接出现。

```tsx
// ❌ 错误：SEO 关键内容被 Suspense 包裹
<Suspense fallback={<Skeleton />}>
  <ProductDescription /> {/* 首次 HTML 可能没有描述文字 */}
</Suspense>

// ✅ 正确：数据在 loader 中获取，组件不 suspense
export const loader = async ({ params, context }) => {
  const product = await context.storefront.query(...);
  return { product }; // loader resolve 后才会返回 HTML
};

export default function ProductPage() {
  const { product } = useLoaderData<typeof loader>();
  return <ProductDescription product={product} />; // 直接在 SSR HTML 中
}
```

### 2.4 JSON-LD 放置位置

JSON-LD 不要放在 `<head>` 标签内部，放在 `<body>` 最后或紧接在相关内容后也可以——Google 两种都认。但在 Remix 里更方便的是在 `root.tsx` 或每个 route 组件中渲染:

```tsx
// 在 route 组件中渲染 JSON-LD
export default function ProductPage() {
  const { product } = useLoaderData<typeof loader>();

  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'Product',
    name: product.title,
    // ...
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      {/* 页面其余部分 */}
    </>
  );
}
```

---

## 三、URL 结构与路由设计

### 3.1 路由设计原则

你不再被限制于 `/products/xxx`。你可以设计任何 URL 结构。但 **不要为了「好看」而牺牲 SEO 清晰度**。

**推荐方案：保持与 Shopify 一致的 URL 结构**

| 页面类型 | 推荐路径 | 原因 |
|---------|---------|------|
| 首页 | `/` | |
| 产品页 | `/products/{handle}` | 用户和搜索引擎都熟悉 |
| 集合页 | `/collections/{handle}` | 同上 |
| Blog 列表 | `/blog` | |
| Blog 文章 | `/blog/{slug}` | |
| 静态页 | `/pages/{handle}` | About, Contact 等 |
| 搜索 | `/search?q=...` | 参数化，不建独立路径 |

**为什么推荐保持 Shopify 熟悉的路径？**
- 如果你未来迁移（包括迁移回 Liquid），URL 不需要 301
- GSC 和 GA4 的 URL 分组更容易
- 用户行为习惯不需要改变

### 3.2 Remix 文件路由 → SEO URL 映射

```
app/routes/
├── _index.tsx              → /
├── products.$handle.tsx    → /products/{handle}
├── collections.$handle.tsx → /collections/{handle}
├── blog._index.tsx         → /blog
├── blog.$slug.tsx          → /blog/{slug}
├── pages.$handle.tsx       → /pages/{handle}
├── search.tsx              → /search?q=...
├── [sitemap.xml].tsx       → /sitemap.xml (resource route)
└── [robots.txt].tsx        → /robots.txt (resource route)
```

### 3.3 避免重复内容

Liquid 站最大的重复内容问题是同一产品可通过多个集合路径访问。在 Headless 方案里这个问题不存在——除非你自己制造。

**需要处理的场景:**

**a) 筛选参数:** `/collections/shirts?color=blue`

```tsx
// 所有筛选项的 canonical 指向清洁的集合 URL
export const meta: MetaFunction<typeof loader> = ({ data }) => {
  const baseUrl = `https://yourshop.com/collections/${data.collection.handle}`;
  return [
    { tagName: 'link', rel: 'canonical', href: baseUrl },
    // 筛选参数页面: 不让 Google 索引
    ...(data.hasFilters ? [{ name: 'robots', content: 'noindex, follow' }] : []),
  ];
};
```

**b) 排序参数:** `/collections/shirts?sort=price-asc` — 一律 canonical 到清洁 URL 或加 noindex。

**c) 分页参数:** `/collections/shirts?page=2`

理论上分页页应该被索引。但如果你只有不到 50 个产品在一个集合里，用「加载更多」代替分页更好——一页包含所有产品，不再需要分页 SEO 处理。

如果确实需要分页:

```tsx
// 分页页面需要 self-canonical + rel="prev"/"next"
export const meta: MetaFunction<typeof loader> = ({ data, location }) => {
  const { page, totalPages } = data;
  const baseUrl = `https://yourshop.com/collections/${data.collection.handle}`;
  const links = [
    { tagName: 'link', rel: 'canonical', href: `${baseUrl}?page=${page}` },
  ];
  if (page > 1) {
    links.push({ tagName: 'link', rel: 'prev', href: `${baseUrl}?page=${page - 1}` });
  }
  if (page < totalPages) {
    links.push({ tagName: 'link', rel: 'next', href: `${baseUrl}?page=${page + 1}` });
  }
  return links;
};
```

### 3.4 多币种/多语言的 URL 策略

```tsx
// app/routes/($locale).products.$handle.tsx
// /products/shirt          → 默认语言 + 默认币种
// /en-us/products/shirt    → 英语美国
// /fr-fr/products/chemise  → 法语法国
```

**要点:**
- 每个 locale 变体使用 `hreflang` 标注（见下方）
- 币种切换不要改变 URL——用 cookie/session 管理，URL 保持语言一致

---

## 四、程序化 Schema 管理 (JSON-LD)

### 4.1 为什么不用 Liquid 的方式

Liquid 方式是在 `theme.liquid` 中写 JSON-LD 模板，数据从 Liquid 对象注入。Headless 下没有 Liquid 对象——你有的是 Storefront API 返回的 JSON 数据和 CMS 返回的结构化字段。

### 4.2 Headless Shopify 必须的 Schema 清单

与 Liquid 站一致，9 种 Schema:

| Schema 类型 | 优先级 | 放置位置 | 数据来源 |
|------------|--------|---------|---------|
| `Organization` | 必须 | root.tsx (首页) | 硬编码或 Settings CMS |
| `WebSite` + `SearchAction` | 必须 | root.tsx (首页) | 硬编码 |
| `Product` + `Offer` | 必须 | 产品页 route | Storefront API |
| `BreadcrumbList` | 必须 | 所有页面 | 从 URL 路径推导 |
| `AggregateRating` | 重要 | 产品页 | Judge.me / Stamped.io API |
| `Article` | 有 Blog 时必须 | Blog 文章页 | Headless CMS |
| `CollectionPage` | 推荐 | 集合页 | Storefront API |
| `FAQPage` | 有条件推荐 | 产品/静态页 | Headless CMS |
| `LocalBusiness` | 有实体店时 | 全站或特定页 | 硬编码或 Settings CMS |

### 4.3 可复用的 JSON-LD 组件

```tsx
// app/components/seo/ProductJsonLd.tsx
interface ProductJsonLdProps {
  product: {
    title: string;
    description: string;
    handle: string;
    featuredImage?: { url: string; width: number; height: number };
    priceRange: { minVariantPrice: { amount: string; currencyCode: string } };
    variants: { nodes: Array<{ availableForSale: boolean; sku?: string }> };
    vendor: string;
  };
  shopName: string;
  rating?: { average: number; count: number };
}

export function ProductJsonLd({ product, shopName, rating }: ProductJsonLdProps) {
  const baseUrl = `https://yourshop.com/products/${product.handle}`;

  const jsonLd: any = {
    '@context': 'https://schema.org',
    '@type': 'Product',
    name: product.title,
    description: product.description?.slice(0, 500),
    url: baseUrl,
    image: product.featuredImage?.url,
    brand: { '@type': 'Brand', name: product.vendor },
    offers: {
      '@type': 'Offer',
      url: baseUrl,
      priceCurrency: product.priceRange.minVariantPrice.currencyCode,
      price: product.priceRange.minVariantPrice.amount,
      availability: product.variants.nodes.some((v) => v.availableForSale)
        ? 'https://schema.org/InStock'
        : 'https://schema.org/OutOfStock',
      itemCondition: 'https://schema.org/NewCondition',
    },
  };

  if (rating && rating.count > 0) {
    jsonLd.aggregateRating = {
      '@type': 'AggregateRating',
      ratingValue: rating.average,
      reviewCount: rating.count,
    };
  }

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
    />
  );
}
```

### 4.4 BreadcrumbList 通用组件

```tsx
// app/components/seo/BreadcrumbJsonLd.tsx
interface Crumb {
  name: string;
  path: string;
}

export function BreadcrumbJsonLd({ crumbs }: { crumbs: Crumb[] }) {
  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: crumbs.map((crumb, i) => ({
      '@type': 'ListItem',
      position: i + 1,
      name: crumb.name,
      item: `https://yourshop.com${crumb.path}`,
    })),
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
    />
  );
}
```

**在 routes 中使用 Breadcrumb:**

```tsx
// 产品页: Home > Products > {Product Title}
<BreadcrumbJsonLd
  crumbs={[
    { name: 'Home', path: '/' },
    { name: 'Products', path: '/collections/all' },
    { name: product.title, path: `/products/${product.handle}` },
  ]}
/>
```

### 4.5 Organization Schema (root.tsx)

```tsx
const organizationJsonLd = {
  '@context': 'https://schema.org',
  '@type': 'Organization',
  name: 'Your Shop Name',
  url: 'https://yourshop.com',
  logo: 'https://yourshop.com/logo.png',
  sameAs: [
    'https://instagram.com/yourhandle',
    'https://facebook.com/yourhandle',
  ],
  contactPoint: {
    '@type': 'ContactPoint',
    contactType: 'customer service',
    email: 'support@yourshop.com',
  },
};
```

### 4.6 与 Judge.me / Stamped.io 的评价集成

Judge.me 和 Stamped.io 提供 REST API。在 loader 中获取评价数据，传入 `ProductJsonLd`:

```tsx
export const loader = async ({ params, context }: LoaderFunctionArgs) => {
  const [productResponse, reviewsResponse] = await Promise.all([
    context.storefront.query(PRODUCT_QUERY, { variables: { handle: params.handle } }),
    fetch(`https://judge.me/api/v1/reviews?shop_domain=yourshop.myshopify.com&handle=${params.handle}`),
  ]);

  const reviews = await reviewsResponse.json();

  return {
    product: productResponse.product,
    rating: {
      average: reviews.review?.average_score || 0,
      count: reviews.review?.review_count || 0,
    },
  };
};
```

---

## 五、Sitemap 与 robots.txt

### 5.1 Sitemap 必须自己构建

Hydrogen 不自动生成 sitemap。你需要自己写一个 resource route。Hydrogen 官方去掉了内置 sitemap 生成器，需要手写或使用社区方案。

**方案 A: 手写 Remix resource route (推荐，最可控)**

```tsx
// app/routes/[sitemap.xml].tsx
import type { LoaderFunctionArgs } from '@shopify/remix-oxygen';

export const loader = async ({ context }: LoaderFunctionArgs) => {
  const baseUrl = 'https://yourshop.com';

  // 并行获取所有需要录入 sitemap 的数据
  const [{ products }, { collections }, { articles }] = await Promise.all([
    context.storefront.query(PRODUCTS_SITEMAP_QUERY),
    context.storefront.query(COLLECTIONS_SITEMAP_QUERY),
    getBlogPosts(context), // 从 Headless CMS 获取
  ]);

  const urls: string[] = [
    baseUrl,
    ...products.nodes.map((p: any) => `${baseUrl}/products/${p.handle}`),
    ...collections.nodes.map((c: any) => `${baseUrl}/collections/${c.handle}`),
    ...articles.map((a: any) => `${baseUrl}/blog/${a.slug}`),
    `${baseUrl}/pages/about`,
    `${baseUrl}/pages/contact`,
  ];

  const sitemap = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls
  .map(
    (url) => `  <url>
    <loc>${url}</loc>
    <changefreq>weekly</changefreq>
    <priority>${url === baseUrl ? '1.0' : url.includes('/products/') ? '0.8' : '0.6'}</priority>
  </url>`
  )
  .join('\n')}
</urlset>`;

  return new Response(sitemap, {
    headers: {
      'Content-Type': 'application/xml',
      'Cache-Control': 'public, max-age=3600',
    },
  });
};
```

**方案 B: 使用 `@shopify/hydrogen` 的 `generateSitemap`**
Hydrogen 早期版本有内置 sitemap 生成函数。如果已安装且版本支持，直接用。如果版本较新已移除，用方案 A。

### 5.2 多语言 Sitemap

如果有 `/en-us`, `/fr-fr` 等 locale 前缀，需要 sitemap index:

```tsx
// app/routes/[sitemap.xml].tsx
const sitemapIndex = `<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap>
    <loc>https://yourshop.com/sitemap-en-us.xml</loc>
  </sitemap>
  <sitemap>
    <loc>https://yourshop.com/sitemap-fr-fr.xml</loc>
  </sitemap>
</sitemapindex>`;
```

### 5.3 Robots.txt Resource Route

```tsx
// app/routes/[robots.txt].tsx
export const loader = () => {
  const robotText = `User-agent: *
Allow: /
Disallow: /search
Disallow: /account
Disallow: /cart
Disallow: /checkout

Sitemap: https://yourshop.com/sitemap.xml
`;

  return new Response(robotText, {
    headers: { 'Content-Type': 'text/plain' },
  });
};
```

### 5.4 验证与提交

1. 访问 `https://yourshop.com/sitemap.xml` 确认返回完整 XML
2. 访问 `https://yourshop.com/robots.txt` 确认格式正确
3. 在 GSC 中手动提交 sitemap URL
4. 后续每次有新页面发布时自动更新（Cache-Control 设短或发布时 purge CDN 缓存）

---

## 六、图片 SEO

### 6.1 Hydrogen `<Image>` 组件的 SEO 优势

Hydrogen 的 `<Image>` 组件基于 Remix 的 `<unpic>` 或 Shopify 的图片 CDN，自动提供:

- **响应式尺寸**: `srcSet` + `sizes` 自动生成
- **格式自动转换**: Oxygen CDN 的 `?fm=webp` 或 `?fm=avif` 参数
- **LQIP / BlurHash**: 占位符防止 CLS

### 6.2 产品图片的正确用法

```tsx
import { Image } from '@shopify/hydrogen';

export function ProductImage({ image, title }: { image: any; title: string }) {
  return (
    <Image
      data={image}
      alt={image.altText || title} // alt text 从 Shopify 数据自动映射
      loading="eager" // 首屏图用 eager，其余 lazy
      sizes="(min-width: 768px) 50vw, 100vw"
      aspectRatio="1/1"
    />
  );
}
```

### 6.3 Alt Text 管理策略

Headless 站的 alt text 管理比 Liquid 更好——因为你可以程序化规则批量处理:

```tsx
// 自动生成描述性 alt text 的 fallback 逻辑
function getProductAltText(product: Product): string {
  if (product.featuredImage?.altText) {
    return product.featuredImage.altText; // 信任 Shopify 的 alt
  }
  return `${product.title} - ${product.productType} by ${product.vendor}`;
  // 例: "Organic Baby Pajamas Blue - Sleepwear by LittleDream"
}
```

**最佳实践:**
- 在 Shopify Admin 上传产品图时就写好 Alt Text——这比后期补救容易
- 用 fallback 函数兜底未填 alt 的图片
- Logo 和装饰性图标使用 `alt=""` (空字符串,不是缺属性)

### 6.4 SEO 检查清单

- [ ] 所有产品图片有描述性 `alt` 属性（含品类关键词）
- [ ] 首屏图片 `loading="eager"`，其余 `loading="lazy"`
- [ ] 每个 `<Image>` 有 `aspectRatio` 或明确的 `width`/`height`——防止 CLS
- [ ] Oxygen CDN 的图片 URL 带有 `fm=webp` 参数自动转换格式
- [ ] OG 社交分享图 (`og:image`) 至少 1200×630

---

## 七、Headless CMS 内容策略

### 7.1 Shopify Blog 不存在了——怎么办

Headless 方案没有 Shopify 内置 Blog。你的网站内容是靠 **Headless CMS + Remix Loader + SSR** 这条管线产出的。选哪个 CMS 直接影响 SEO 灵活度:

| CMS | 适合场景 | SEO 优势 | SEO 注意点 |
|-----|---------|---------|-----------|
| **Sanity** | 内容驱动的电商站 | 自由定义 Schema，结构化内容可复用 | 需要自己设计内容模型 |
| **Contentful** | 需要强编辑体验 | 富文本 / 媒体管理成熟 | 价格随用量涨 |
| **Strapi** | 自建、开源 | 完全控制，数据在你自己服务器 | 需要自运维 |
| **Notion (as CMS)** | 小站、快速验证 | 零成本、编辑友好 | API 慢，不适合大站 |

### 7.2 CMS → Loader → Page 的数据管线

```
Sanity/Contentful (编辑写作)
      │
      │ GraphQL / REST API
      ▼
Remix Loader (server.ts/loader)
      │
      │ 返回数据
      ▼
React 组件 (SSR 渲染为 HTML)
      │
      │ 完整 HTML (含正文、标题、作者、日期)
      ▼
搜索引擎爬虫
```

**关键原则: 所有内容必须经过 SSR。** 如果你在客户端用 `useEffect` fetch Blog 内容，Google 抓不到正文——除非你确认 CMS 的数据在 loader 中获取。

### 7.3 正确的模式: Loader 中获取

```tsx
// app/routes/blog.$slug.tsx
export const loader = async ({ params, context }: LoaderFunctionArgs) => {
  // ✅ 在 loader 中获取——SSR 时执行，内容在 HTML 中
  const post = await sanityClient.fetch(`*[slug.current == $slug][0]`, {
    slug: params.slug,
  });
  if (!post) throw new Response('Not Found', { status: 404 });
  return { post };
};

export const meta: MetaFunction<typeof loader> = ({ data }) => {
  return [
    { title: `${data.post.title} | Blog` },
    { name: 'description', content: data.post.excerpt },
    { tagName: 'link', rel: 'canonical', href: `https://yourshop.com/blog/${data.post.slug.current}` },
    // Article Schema 也在这里？不——正文内容需要出现在页面中，Schema 在组件中
  ];
};

export default function BlogPost() {
  const { post } = useLoaderData<typeof loader>();
  return (
    <article>
      <h1>{post.title}</h1>
      <p>By {post.author.name} · {new Date(post.publishedAt).toLocaleDateString()}</p>
      <PortableText value={post.body} /> {/* Sanity 富文本渲染 */}
      <ArticleJsonLd post={post} />
    </article>
  );
}
```

### 7.4 E-E-A-T 信号输出

Headless CMS 给 E-E-A-T 建设带来了更好的灵活性——你可以设计专门的内容字段:

**Blog 文章的数据模型应包含:**

```
Article {
  title: string
  slug: string
  excerpt: string (用作 meta description)
  publishedAt: datetime
  updatedAt: datetime
  author: {
    name: string
    bio: string
    photo: url
    credentials: string (如 "CPSC certified儿童产品安全顾问")
  }
  body: portableText (正文)
  featuredImage: image
  category: string
  relatedProducts: reference[] (指向Shopify产品)
}
```

**在页面中渲染 E-E-A-T 信号:**

```tsx
<div className="author-box">
  <img src={post.author.photo} alt={post.author.name} />
  <strong>{post.author.name}</strong>
  <span>{post.author.credentials}</span>
  <p>{post.author.bio}</p>
</div>
<time dateTime={post.publishedAt}>
  Published: {new Date(post.publishedAt).toLocaleDateString()}
</time>
{post.updatedAt !== post.publishedAt && (
  <time dateTime={post.updatedAt}>
    Last updated: {new Date(post.updatedAt).toLocaleDateString()}
  </time>
)}
```

### 7.5 内容最少字数要求（同 Liquid 站）

- Blog 文章: 至少 1800 字
- 集合页描述: 至少 300 字（从 CMS 字段获取，渲染在集合页底部）
- 产品描述: 至少 300 字（从 Shopify Product.description 获取）

---

## 八、性能与 Core Web Vitals

### 8.1 Hydrogen 的性能优势

Hydrogen + Oxygen 的架构天然比 Liquid 快，因为:

- 没有安装 App 带来的 JS/CSS 膨胀
- Oxygen CDN 全球 100+ 边缘节点
- Remix 的并行 loader 数据获取
- React 的流式 SSR 提前输出首字节

但 headless 也引入了新问题:

### 8.2 Hydration 开销

SSR 出来的 HTML 在浏览器中要被 React "激活" (hydration)。如果页面组件树很复杂，hydration 时间 (TBT / INP) 会变长。

**减轻 hydration 开销:**

- **大段纯文本内容不要包装在交互组件中**——静态 HTML 不需要 hydration
- **`ClientOnly` 隔离**——把纯客户端交互的组件（购物车弹窗、搜索建议）包裹在 `ClientOnly` 中，不让它们在 SSR 时输出
- **产品详情页用 `defer` 加载非关键数据**——产品评价、推荐列表可以延迟获取，但产品标题、描述、价格、Schema 必须在首帧

### 8.3 用 CrUX 数据验证

Hydrogen 站没有「装了多少 App」的变量，但有「你写了多少 JS」的变量。唯一可靠的 CWV 数据来自真实用户:

```
Skill("claude-seo:seo-google")  // 获取 CrUX 真实用户 CWV 数据
```

在 Oxygen 部署后，每周至少查看一次 CrUX 报告，重点关注:
- **LCP**: 应该 < 2.5s（Hydrogen 站通常很容易达到）
- **INP**: 应该 < 200ms（交互延迟，关注购物车加购、筛选操作）
- **CLS**: 应该 < 0.1（关注图片加载、字体加载）

### 8.4 常见 CWV 杀手

| 问题 | 原因 | 修复 |
|------|------|------|
| LCP 高 | 首屏产品图加载慢 | `<Image loading="eager" fetchpriority="high">`, CDN 优化 |
| LCP 高 | Web font 阻塞渲染 | `font-display: swap`, 用 WOFF2 |
| CLS 高 | 图片无尺寸 | 所有 `<Image>` 有 `aspectRatio` |
| INP 高 | 过多的 useEffect | 减少不必要的状态更新 |
| TBT 高 | 大体积 JS bundle | Code splitting, lazy load 非关键组件 |

---

## 九、部署与监控

### 9.1 Oxygen 部署的 SEO 检查清单

Oxygen 负责托管你的 Hydrogen 站。部署前确认:

- [ ] 自定义域名已正确指向 Oxygen（SSL 证书自动生成）
- [ ] 主域名 301 重定向到首选版本（`yourshop.com` → `www.yourshop.com` 或反过来）
- [ ] HTTP → HTTPS 强制（Oxygen 默认处理）
- [ ] `/sitemap.xml` 可公开访问且返回完整 XML
- [ ] `/robots.txt` 可公开访问且包含 Sitemap 链接
- [ ] GSC 已验证（通过 DNS TXT 记录 或 HTML 文件上传到 `public/` 目录）
- [ ] 所有 `og:image` URL 使用绝对路径 (`https://...`)
- [ ] 部署 hook 或 CI 确保发布前运行 Lighthouse / PageSpeed 检查

### 9.2 自托管 (非 Oxygen) 的额外注意事项

如果你把 Hydrogen 部署在自己的服务器或 Vercel/Netlify:

- [ ] 确保 `Cache-Control` 头正确设置（静态资源长缓存，HTML 短缓存）
- [ ] CDN 配置: 全局 CDN (Cloudflare, Fastly 等) 对 CWV 影响很大
- [ ] 服务器位置离你的客户近 (如果不用 CDN)
- [ ] SSR 渲染性能监控（Node.js CPU/Memory）

### 9.3 SEO 漂移基线

```
Skill("claude-seo:seo-drift")
```

对核心页面建立基线（首页 + 3-5 个核心产品页 + Hub Blog 页）。每次代码发布后对比:
- Title / Meta Description 是否被意外修改
- Canonical 是否被改掉
- Schema 是否完整
- H1 是否还在
- robots meta 是否被改为 noindex

### 9.4 GSC + GA4 配置

- GSC: 同时提交 `https://yourshop.com` 和 `https://www.yourshop.com`（如果两个都能访问会出问题——Oxygen 应该自动 301）
- GA4: 在 `root.tsx` 中注入 GA4 script（用 `<Script>` 组件或直接放在 `<head>` 中）
- 确保 checkout 流程的跨域跟踪正确（Shopify checkout 在 `yourshop.myshopify.com` 域）

---

## 十、Headless Shopify 发布前检查清单

### 技术基础
- [ ] HTTPS 全站 + HTTP 自动 302/301
- [ ] 首选域名 (www / non-www) 统一
- [ ] GSC 已验证并提交 sitemap
- [ ] GA4 已注入并正常接收数据
- [ ] 404 页面返回 404 状态码（不是 200）
- [ ] 无 broken links（内部链接无 404）
- [ ] `/sitemap.xml` 和 `/robots.txt` 可公开访问

### 页面级 SEO
- [ ] 每个 route 有 `MetaFunction`（title + description + canonical + robots）
- [ ] 核心产品页手工写 title 和 description，不用自动模板
- [ ] 集合页有描述性文字内容（至少 300 字，从 CMS 管理）
- [ ] Blog 文章至少 1800 字，有作者信息和发布日期
- [ ] About 页完整（真名 + 真照片 + 真实故事）
- [ ] 隐私政策、退换货政策、联系页公开可访问
- [ ] 筛选/排序参数页 canonical 指向清洁 URL 或 noindex

### Schema
- [ ] Organization (root.tsx, 含 Logo 和联系信息)
- [ ] WebSite + SearchAction (root.tsx)
- [ ] Product + Offer (产品页, 价格 / 库存动态从 Storefront API 获取)
- [ ] AggregateRating (产品页, 从 Judge.me / Stamped.io API 获取)
- [ ] BreadcrumbList (全站通用组件)
- [ ] Article (Blog 文章页, 从 CMS 获取作者和日期)
- [ ] FAQPage (如有产品 FAQ 或 Blog FAQ)
- [ ] LocalBusiness (如有实体店)

### 图片
- [ ] 所有产品图有描述性 Alt Text
- [ ] 首屏图 `loading="eager" fetchpriority="high"`
- [ ] 所有 `<Image>` 有 `aspectRatio` 或固定尺寸——防止 CLS
- [ ] OG 社交分享图 (至少 1200×630, 所有核心页面)
- [ ] Logo 图有 `alt="店名"`, 装饰性图有 `alt=""`

### 性能
- [ ] LCP < 2.5s (通过 CrUX 或 PageSpeed Insights 验证)
- [ ] CLS < 0.1
- [ ] INP < 200ms
- [ ] 字体 `font-display: swap`
- [ ] 关键 JS bundle 经过 code splitting

### 内容
- [ ] 至少 3 个核心产品页有深度描述（300+ 字）
- [ ] 至少 1 个核心集合页有品类描述（300+ 字，放在产品列表下方）
- [ ] 至少 5 篇 Blog 文章已就绪（信息型，目标引流入站）
- [ ] About 页、Contact 页、Policy 页完整
- [ ] 每篇 Blog 含 2-3 个相关产品链接

---

## 十一、与 SEO Workbench 工作流对接

### 11.1 INIT 阶段的差异

Headless 项目的 INIT 阶段基线检查不同——没有 `theme.liquid`，没有 Shopify Theme 编辑器:

| Liquid 站 INIT 步骤 | Headless 站对应步骤 |
|---------------------|-------------------|
| 验证 GSC (通过 DNS / HTML 标签) | 同 |
| 提交 sitemap.xml | sitemap 是自己写的 resource route，验证返回 200 |
| 确认 Title 和 Meta Description 已填 | 检查 root.tsx 的 MetaFunction |
| 确认只有一个主域名 | 同，Oxygen 端配置 |
| 确认 address / phone / email 准确 | 同 |
| 检查 theme.liquid 没有硬编码 noindex | 检查 root.tsx 和每个 route 的 MetaFunction 没有硬编码 noindex |
| — (无 Liquid) | 额外: 确认 `/sitemap.xml` 和 `/robots.txt` resource route 存在 |
| — (无 Liquid) | 额外: 确认 404 页面返回 404 状态码 |

### 11.2 STRATEGY 阶段

**与 Liquid 站完全相同。** 关键词策略、话题集群、内容简报不受技术栈影响——你仍然是卖产品的 Shopify 店。

### 11.3 CONTENT_PRODUCTION 阶段

**产出目标变化:**
- Liquid 站: 产出草稿 → 手动粘贴到 Shopify Blog
- Headless 站: 产出草稿 → 手动录入 Headless CMS（Sanity / Contentful / Strapi）

SEO Machine 的 `/write` 产出不变——仍然写 Markdown 草稿。只是发布路径变成了 CMS。

### 11.4 QUALITY_REVIEW 阶段

**与 Liquid 站完全相同。** 页面审计、E-E-A-T 审计、语义缺口分析——这些是针对线上页面内容和排名的分析，与技术栈无关。

### 11.5 TECHNICAL_AUDIT 阶段

这是差异最大的阶段。Headless 项目的技术审计需要关注不同的点:

| Liquid 站检查项 | Headless 站检查项 |
|----------------|-----------------|
| 重复产品 URL（collection 路径）| 自定义路由是否引入了新的重复路径 |
| Tags 页面 noindex | 筛选/排序参数页面 canonical 正确性 |
| theme.liquid Schema 输出验证 | JSON-LD 组件输出验证（检查渲染后的 HTML） |
| App 拖慢页面速度 | JS bundle 大小、hydration 开销 |
| `rel="next"`/`rel="prev"` 检验 | 分页 SEO 是否正确实现 |
| Shopify 自动 sitemap 验证 | sitemap resource route 验证 |
| 图片格式 (WebP 转换) | 图片 CDN 格式转换 (`fm=webp`) 验证 |
| — | 额外: 流式 SSR 对爬虫兼容性检查 |
| — | 额外: Headless CMS 内容是否正常渲染在 SSR HTML 中 |

**调用方式:**

```
Skill("claude-seo:seo-technical")  // 对线上站做技术审计
```

在 prompt 中明确告诉 agent 这是 Headless/Hydrogen 站，让它关注上述差异点。

### 11.6 OFF_PAGE 与 MONITORING 阶段

**与 Liquid 站完全相同。** 外链策略和周期性监控与技术栈无关。

### 11.7 推荐工作流调整

如果使用 `/workflow:next` 驱动，当前 state.json 的 `project.type: "shopify"` 对 Headless 站不完全准确。建议在 INIT 阶段手动调整检查项。

理想情况下，未来 state.json 增加 `"shopify-hydrogen"` 类型——见下方「后续 TODO」。

---

## 十二、第1-6个月节奏 (Headless 版)

| 月份 | 核心工作 | 工具/命令 | 与 Liquid 的差异 |
|------|---------|----------|-----------------|
| **第1月** | 确定关键词战略；完成 Hydrogen SEO 基线（MetaFunction、canonical、Schema 组件）；写 About 页 + 3-5 篇 Blog | SuperSEO (keyword-deep-dive + cluster) + SEO Machine (write) | 多花时间在 SEO 组件开发上——这是 Liquid 不需要的 |
| **第2月** | 继续写 Blog 内容（目标 10 篇）；构建 Sitemap 和 robots.txt resource route；验证 Schema | SEO Machine (write) + Claude SEO (schema) | 需要自己写 sitemap/robots（Liquid 自动生成） |
| **第3月** | 启动外链建设；写商业调研型内容（Best X, X vs Y）；图片 SEO 优化 | SuperSEO (linkbuilding + content-brief) + Claude SEO (images) | 图片优化用 `<Image>` 组件，比 Liquid 更灵活 |
| **第4月** | 全站技术审计（headless 定制项）；修复 URL 问题；分析 GSC 数据 | Claude SEO (technical + google) + SuperSEO (page-audit) | 技术审计关注点不同（见第 11.5 节） |
| **第5月** | 表现不佳的页面做深度优化；E-E-A-T 内容补充；Headless CMS 内容管线优化 | SuperSEO (page-audit + semantic-gap + eeat-audit) + SEO Machine (write) | CMS 内容管线可能需要调整（如缓存策略） |
| **第6月** | 全站审计；外链审计；性能复查（CrUX）；决定下一阶段内容策略 | Claude SEO (audit + backlinks + google) + SuperSEO (content-brief) | 性能复查比 Liquid 站重要——hydration 问题可能在此暴露 |

---

## 十三、Headless Shopify 常见 SEO 错误

**错误1：忘记写 MetaFunction。**
某个 route 没有 `MetaFunction`，导致该页面的 title 是空或继承 root 的默认值。每个 route 都要有。

**错误2：JSON-LD 放在 Suspense 里。**
Google 不一定等 React Suspense resolve 才解析 JSON-LD。Schema 必须在首帧 HTML 中。

**错误3：Canonical 指向了带参数的 URL。**
`/products/shirt?color=blue` 的 canonical 忘了写 → Google 把它当独立 URL 索引。

**错误4：Sitemap 忘记更新。**
新增产品或 Blog 文章后，sitemap 没有包含新 URL。用短缓存 `Cache-Control` 或发布时 purge。

**错误5：CMS 内容不在 SSR 中。**
在 client-side `useEffect` 中 fetch Blog 内容 → Google 看到的是空壳。

**错误6：流式 SSR 导致的截断。**
产品描述或正文在 Suspense 边界之后 → 第一帧 HTML 缺少正文 → Google 可能判定为 Thin Content。

**错误7：图片没有 alt + 尺寸。**
Hydrogen `<Image>` 不会自动帮你填 alt。需要从产品数据显式传入。没有尺寸 → CLS 扣分。

**错误8：把所有页面都 index。**
搜索页、筛选页、购物车、账号页——这些不该被索引。每个 route 明确写 `robots: 'noindex, follow'` 或 `robots: 'noindex, nofollow'`。

**错误9：忽略 404 状态码。**
Headless 站容易出现所有路径返回 200（SPA 式的 catch-all route）。404 页面必须返回 404 状态码:

```tsx
// 在 loader 中
if (!product) {
  throw new Response('Not Found', { status: 404 });
}
```

---

## 与本系列其他教程的关系

- **通用新站 SEO 建设**: `从0到1新站SEO建设教程.md` — 非 Shopify 站或 CMS 站
- **传统 Shopify (Liquid)**: `Shopify从0到1-SEO建设进阶教程.md` — 使用 Shopify Online Store 2.0 / Liquid Theme
- **本教程 (Headless Shopify)**: `Shopify-Hydrogen-Headless-SEO指南.md` — Hydrogen + Oxygen 或 Headless 自托管
- **编写引擎**: `seo-workbench/CLAUDE.md` — 状态机工作流编排
