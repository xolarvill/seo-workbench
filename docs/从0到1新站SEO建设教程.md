# 从 0 到 1 新站 SEO 建设教程

这篇教程适合尚未积累稳定搜索数据的新网站，不限定 CMS 或技术框架。自建 HTML、PHP 或其他普通站点的实现细节见 [自建普通网站 SEO 指南](自建普通网站SEO指南.md)，电商站请继续阅读对应平台教程。

本文沿用 [SEO 基础知识与证据模型](SEO基础知识与证据模型.md) 的判断规则。新站最重要的约束是证据少，很多 `no_data` 和空报表只是尚未积累数据，不能被解释成通过或失败。

## 新站先确定业务边界

创建页面前，写清楚四件事：

- 网站服务谁，用户处于什么地区、行业和采购阶段；
- 网站提供什么产品、服务或信息；
- 希望用户完成什么动作，如购买、询盘、预约、注册或下载；
- 团队能提供哪些第一方资料，如产品数据、方法、项目经验、案例和照片。

如果这些信息不清楚，关键词研究很容易变成一份与业务无关的流量词列表。

## 建立本地项目

```bash
./seo --project new-site init general \
  --name "New Site" \
  --url "https://example.com" \
  --description "面向谁，解决什么问题，主要转化是什么"
```

把品牌、受众和业务事实写入项目 `context/`。每个站点使用独立项目目录，测试站、客户站和自己的站不要混用同一份状态或 GSC 绑定。

检查下一步：

```bash
./seo --project new-site status --json
./seo --project new-site next --json
```

## 上线前需要哪些页面

新站不需要为了凑数量预先发布一批文章。先让用户和搜索引擎能够理解业务，并完成主要任务。

常见的最小页面集合包括：

- 首页，说明业务、受众、差异和主要入口；
- 产品、服务或解决方案页面，每个页面承担清楚的用户任务；
- 分类或导航页，把核心页面组织起来；
- About、Contact 和适用的政策页面；
- 能证明能力的案例、方法、规格、认证或实际过程；
- 用户确实需要的帮助内容。

页面数量取决于业务。如果只有一项服务，三四个扎实页面也可以上线；产品目录很大时，应先保证分类、产品数据和抓取路径完整。

## 设计信息架构

先从用户任务和业务对象建立页面地图，再研究关键词。一个页面通常对应一种主要意图和一个清楚的下一步。

```text
首页
├── 产品或服务分类
│   ├── 产品或服务详情
│   └── 规格、方案或案例
├── 使用和决策内容
└── 公司、联系和政策
```

重要页面要能通过普通链接访问。不要把全部产品藏在站内搜索、筛选组件或登录后页面里。URL 保持稳定、可读，避免同一内容同时存在多个参数、大小写或尾斜杠版本。

## 关键词研究从用户任务开始

让 agent 读取 `keyword-deep-dive` skill，逐个研究与业务直接相关的查询。判断机会时看：

- 当前搜索结果主要是什么页面类型；
- 查询是学习、比较、采购还是寻找特定品牌；
- 网站是否真的能满足这个意图；
- 现有结果有哪些信息缺口；
- 这个查询即使带来点击，是否可能产生业务结果；
- 团队是否有足够资料做出比摘要和改写更有价值的页面。

没有可靠关键词工具时，不要编造搜索量。可以根据结果竞争、GSC 后续反馈、销售问题和客户访谈建立优先级。

新站不必一律避开交易型查询。产品和服务页面本来就应承接交易或询盘意图，只是竞争激烈的泛词通常需要更长时间和更多站点信号。

## 内容简报说明要提供什么证据

使用 `content-brief` 时，简报至少包含：

- 目标受众和用户需要完成的决定；
- 页面类型及它在站内结构中的位置；
- 必须回答的问题和顺序；
- 需要业务方补充的一手资料；
- 哪些结论需要一手来源；
- 与已有页面的内部链接关系；
- 页面完成后的主要动作。

篇幅根据任务决定。不要用竞品平均字数加成，也不要把词频当成质量标准。

## 上线前技术基线

网站可以公开访问后采集第一份证据：

```bash
./seo --project new-site evidence --rendered --technology --json
./seo --project new-site performance --json
```

上线前重点确认：

- 主域名和 HTTPS 版本统一，重定向直接到最终 URL；
- 正常页面返回 200，不存在页面返回 404；
- robots.txt 没有误阻止正文和必要资源；
- 页面没有意外 `noindex`；
- canonical、内部链接和 Sitemap 使用同一套首选 URL；
- 原始或渲染 HTML 中有标题、正文和可抓取链接；
- 移动页面没有跳到错误路径或丢失主要内容；
- 图片有尺寸，首屏资源没有被不必要地延迟；
- 结构化数据与页面可见事实一致。

结构化数据按页面类型添加。普通企业站通常从 `Organization`、`BreadcrumbList` 和适用的 `Article` 开始，不需要为了“Schema 全覆盖”添加 Google 不支持或页面不具备的数据。

## Sitemap 和 GSC

Sitemap 只放希望被索引的 canonical URL，并保证这些 URL 返回 200。它帮助发现页面，不替代站内链接，也不保证索引。

验证 GSC property 后，可以配置 Workbench 的只读接入：

```bash
./seo --project new-site gsc auth \
  --profile default \
  --client-secret /path/to/client-secret.json

./seo --project new-site gsc properties --profile default --json
./seo --project new-site gsc bind \
  --profile default \
  --property "sc-domain:example.com"
```

首次 OAuth 需要用户在浏览器确认。Workbench 不提交 Sitemap，也不请求索引。少量重要新页面可以由站点所有者在 GSC 网页中的 live URL Inspection 手动请求重新抓取；多个页面通过 Sitemap 和正常链接发现。

## 新站没有 CrUX 或 GSC 数据很正常

```bash
./seo --project new-site crux --json
./seo --project new-site gsc collect --json
```

常见初期状态：

| 状态 | 解释 | 下一步 |
|---|---|---|
| CrUX `no_data` | 合格 Chrome 流量不足 | 用 Lighthouse 做实验室诊断，等待真实数据积累 |
| GSC 展示为 0 | 可能尚未收录，也可能尚未匹配查询 | 先检查索引和抓取证据，不据此判断内容失败 |
| Sitemap 已读取 | Google 能处理 Sitemap | 到 Page Indexing 或 URL Inspection 判断具体 URL |
| URL Inspection 无索引 | Google 当前索引中没有该 URL | 检查发现、抓取、canonical、内容和站点整体情况 |

不要每天根据小幅波动改标题和正文。Search Analytics 有处理延迟，新站样本也很小，应等到形成完整窗口再比较。

## 内容上线后的学习循环

每轮只处理有证据支持的问题：

1. 确认页面可访问、可抓取、可渲染并使用正确 canonical；
2. 查看 GSC 中页面和查询是否开始获得展示；
3. 判断搜索意图是否匹配，标题链接和摘要是否准确；
4. 结合销售、客服和站内行为补充用户真正缺少的信息；
5. 更新页面后保存新证据，等待足够窗口再比较。

GSC 中排在 5 到 15 名的查询有时是优化机会，但不是自动优先级。还要看查询意图、展示量、转化价值、页面是否已经满足需求，以及是否和另一个页面发生竞争。

## 新站的衡量框架

按阶段选择指标：

| 阶段 | 主要问题 | 可用证据 |
|---|---|---|
| 上线 | 页面能否被正常访问和理解 | raw、rendered、状态码、Sitemap |
| 发现 | Google 是否找到重要 URL | GSC Sitemap、URL Inspection、服务器日志 |
| 索引 | canonical 页面是否进入索引 | GSC URL Inspection、Page Indexing |
| 展示 | 哪些页面开始匹配查询 | GSC 页面、查询、设备和国家数据 |
| 点击 | 搜索展示是否准确吸引目标用户 | GSC CTR、实际 SERP、标题和摘要 |
| 业务 | 搜索访问是否产生询盘、注册或成交 | 自有分析、CRM、电商或表单数据 |

排名不是唯一目标。B2B 站可能从少量高意向查询获得询盘，内容站则更关注覆盖、回访和订阅。

## 何时建立审计基线

第一版稳定上线后保留 raw、rendered、technology 和 performance 快照。以后在这些事件前后复查：

- 域名、URL 或 CMS 迁移；
- 主题和全站模板更新；
- CDN、缓存、同意管理或分析脚本调整；
- 大批页面发布、删除或重定向；
- 自然搜索流量出现无法解释的变化。

```bash
./seo --project new-site audit-diff --json
```

## 上线检查清单

### 访问和索引

- [ ] 一个首选 HTTPS 主域名
- [ ] 正常页、重定向和错误页返回正确状态码
- [ ] robots.txt 可访问且未误阻止重要内容
- [ ] canonical、内部链接和 Sitemap 指向首选 URL
- [ ] 重要页面能从导航或正文链接到达
- [ ] 测试环境和预览域没有进入索引

### 页面和内容

- [ ] 每个页面有清楚、独特的标题和主要标题
- [ ] 页面解决一个明确用户任务
- [ ] 产品、服务、公司和政策信息准确一致
- [ ] 重要结论有一手资料或可靠来源
- [ ] 没有为达到字数而扩写的重复段落
- [ ] AI 辅助内容经过事实和编辑审核

### 体验和测量

- [ ] 移动端可以完成主要任务
- [ ] Lighthouse 没有明显的加载、布局和主线程故障
- [ ] GSC property 已验证
- [ ] Sitemap 已在 GSC 网页端提交并能被读取
- [ ] 业务转化有自己的测量方式
- [ ] 第一份 Workbench 审计快照已经保存

## 官方参考

- [Google SEO Starter Guide](https://developers.google.com/search/docs/fundamentals/seo-starter-guide)
- [Google 如何让新页面被重新抓取](https://developers.google.com/search/docs/crawling-indexing/ask-google-to-recrawl)
- [Google Sitemap 指南](https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview)
- [Google Search Console 入门](https://developers.google.com/search/docs/monitor-debug/search-console-start)
