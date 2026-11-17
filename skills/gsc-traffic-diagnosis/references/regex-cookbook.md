# SEO 正则工具箱（GSC / RE2）

使用位置：GSC 效果 → 搜索结果 → 添加筛选 → 网页（Page）或查询（Query）→ 自定义（regex）。按配方选择匹配或不匹配模式。所有域名、品牌和年份均为示例。

## 运行规则

- GSC 使用 RE2，默认部分匹配、不区分大小写；完整匹配用 `^...$`。配方中的 `(?i)` 显式声明大小写行为，区分大小写用 `(?-i)`。不要粘贴 JavaScript 的 `/pattern/i` 外壳。
- GSC 网页字段是完整 URL，不是 pathname；域名中的点、品牌中的加号要转义。JSON 字符串中的反斜杠需再转义；后台输入使用下方原始 regex。
- RE2 不支持前瞻、后顾和反向引用。排除组用 **Doesn't match regex**；要同时包含 A、排除 B，不能用 `^(?!.*B).*A`。后台若不能表达同维度双条件，就导出后对同一行分别判断，不凭空拼接独立汇总。
- 生成品牌/URL OR 列表前先转义每个字面量，再用括号包住分支；域名路径边界、大小写、误匹配必须各测正反例。不要把空格加到 `a|b` 两侧；空分支会匹配空串。
- 普通 `\b` / `\w` 不能当中文分词器。互相重叠的意图组不要相加当独立总量；多词 AND 可在导出后逐条件筛选。
- 正则只分组文本，不能筛出“CTR < 2% 且位置 4–10”。数值条件在 GSC 排序/导出或现有统计产物中处理，显著性走现有流程。

## 配方

### 1. 博客目录分组

字段/模式：Page / Matches。

```regex
^https://(www\.)?example\.com/blogs?(/|[?#]|$)
```

匹配 blog 和 blogs 两种目录；不要用裸 blog 子串混入 blogger 或查询参数。

匹配：`https://example.com/blog/how-to`；不匹配：`https://example.com/blogger/a`。

### 2. Shopify 博客文章，排除博客首页

字段/模式：Page / Matches。

```regex
^https://(www\.)?example\.com/blogs/[^/?#]+/[^/?#]+/?([?#].*)?$
```

按实际 /blogs/博客handle/文章handle 结构筛选；不同平台路径须修改。

匹配：`https://example.com/blogs/news/setup`；不匹配：`https://example.com/blogs/news`。

### 3. 商品与集合页面

字段/模式：Page / Matches。

```regex
^https://(www\.)?example\.com/(products|collections)(/|[?#]|$)
```

适合与博客同窗比较；组间可能存在需求差异，不能直接当因果对照。

匹配：`https://example.com/products/desk`；不匹配：`https://example.com/products-old/desk`。

### 4. 少量精确 URL 合并观察

字段/模式：Page / Matches。

```regex
^https://example\.com/(products/desk|blogs/news/setup)/?$
```

只包含列出的路径和可选尾斜杠；参数版本在本配方中刻意排除。

匹配：`https://example.com/products/desk`；不匹配：`https://example.com/products/desk-pro`。

### 5. 品牌/拼写变体分组或排除

字段/模式：Query / Matches；非品牌用 Doesn’t match。

```regex
(?i)(^|[^a-z0-9])(acme\+tools|acme[ -]?tools|acmetols)($|[^a-z0-9])
```

示例品牌为 Acme+Tools；变体须来自实际品牌名或已观察查询。非品牌用后台不匹配模式，不写负向前瞻。ASCII 边界不适合直接处理中文品牌。

匹配：`Acme+Tools desk`；不匹配：`acmetoolsmith`。

### 6. 英文问题型查询

字段/模式：Query / Matches。

```regex
(?i)^(how|what|why|when|where|who|which|can|does|do|is|are)\b
```

匹配词只代表形式；how much 也可能有购买意图，仍需看 SERP。

匹配：`how to choose a desk`；不匹配：`show desk`。

### 7. 比较/评测/替代查询

字段/模式：Query / Matches。

```regex
(?i)\b(best|reviews?|vs\.?|versus|alternatives?|compare|comparison)\b
```

作为意图候选组；词形不是已验证的搜索意图。

匹配：`best desk`；不匹配：`preview desk`。

### 8. 价格和购买修饰词

字段/模式：Query / Matches。

```regex
(?i)\b(buy|price|cost|deal|discount|coupon|shipping)\b
```

不能据此推定转化或购买。

匹配：`desk price`；不匹配：`buyer desk`。

### 9. 至少五个空格分隔词

字段/模式：Query / Matches。

```regex
^\s*\S+(\s+\S+){4,}\s*$
```

这是空白分词长度筛选，非中文分词，也不是低竞争或高转化证明。

匹配：`how to choose a monitor arm`；不匹配：`best monitor arm`。

### 10. 中文问法与选型词

字段/模式：Query / Matches。

```regex
(怎么选|如何选择|哪个好|值得买吗|对比|评测|替代)
```

中文直接用短语；不要依赖 ASCII 的 \b 词边界。

匹配：`显示器支架怎么选`；不匹配：`桌子尺寸`。

### 11. 年份时效线索

字段/模式：Query / Matches。

```regex
(^|[^0-9])202[5-7]([^0-9]|$)
```

年份范围是示例，应随任务年份更新；有年份不等于内容已过期。

匹配：`best tools 2026`；不匹配：`20260 desk`。

### 12. 跟踪参数 URL

字段/模式：Page / Matches。

```regex
[?&](utm_[a-z0-9_]+|gclid|fbclid)=
```

GSC 常归并到 canonical，所以未匹配不能证明站点没有参数 URL；必要时查已有抓取和服务器证据。

匹配：`https://example.com/a?utm_source=x`；不匹配：`https://example.com/utm_source=x`。

### 13. 筛选/排序/分页参数

字段/模式：Page / Matches。

```regex
[?&](sort_by|filter\.[^=&#]+|page)=
```

仅找候选；存在参数不自动等于重复内容、抓取浪费或应 noindex。

匹配：`https://example.com/collections/desks?sort_by=price`；不匹配：`https://example.com/a?homepage=2`。

### 14. PDF/表格等文件 URL

字段/模式：Page / Matches。

```regex
(?i)\.(pdf|xlsx?|csv)([?#]|$)
```

文件扩展名分组，不替代响应 MIME、HTTP 或可索引性检查。

匹配：`https://example.com/manual.PDF`；不匹配：`https://example.com/a.pdf.html`。

## 验证与解释

[机器可读正反例](regex-cases.json) 与上述配方按 id 对应，可用于正则引擎匹配验证；非品牌配方先验证品牌命中，再在后台反选。用 RE2 或支持此语法子集的引擎检查，不用 Python/JavaScript 测试成功代替 RE2 兼容性验证。实际 GSC 数据的大小写、Unicode、URL 编码和覆盖情况仍须抽样确认。

筛选后保留同一日期、市场、设备和搜索类型。带 query 筛选的结果受匿名查询及返回行覆盖影响，不与未筛选属性总量直接相减声称“完整非品牌流量”。零命中只描述当前可观测范围。

规范依据：[GSC 高级过滤](https://support.google.com/webmasters/answer/17011165?hl=en)、[RE2 语法](https://github.com/google/re2/wiki/Syntax)。这套配方仅针对 GSC/本地筛选，不直接作为 GA4、robots.txt、nginx 或重定向规则使用。
