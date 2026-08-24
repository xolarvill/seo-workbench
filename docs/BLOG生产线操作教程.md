# BLOG 生产线操作教程

本教程用于 Hexcal BLOG 的日常生产。其他项目可以复用同一套关键词、内容、Shopify 和 GSC 命令，只需替换项目 ID，并跳过没有配置的飞书步骤。SEO Workbench 负责 idea、关键词、状态、内容文件、发布记录与收录证据；飞书只在需要素材、评审或通知时接入，不是生产状态的主库。

## 1. 开工检查

```bash
./setup.sh --check
./seo --project hexcal validate --json
./seo --project hexcal doctor --json
./seo --project hexcal ui
```

在 UI 中打开 **Content**。Shopify 与 GSC 在 **Connections** 中配置；飞书 profile 保存在仓库根目录忽略提交的 `.runtime/profiles.json`，不要把密钥写进项目文档。

查看今天真正需要处理的工作：

```bash
./seo --project hexcal content ops --json
```

## 2. 由 Workbench 产生 idea

先在 UI 打开 **Keywords → Opportunity Pool**。这个页面联合关键词池、最新 GSC query、deep-dive、Content 队列和 Pages Portfolio，但不复制这些来源。Query 是只读搜索事实，Keyword 是策略对象，Cluster 汇总相关 keyword/query，Target URL 决定计划承接页面。GSC-only query 在首次 prioritize/hold/drop 或设置归属之前只是只读候选；exact-query 与 Cluster 聚合表现继续来自 Statistics/Portfolio，缺失值表示未观察到，不是零。

推荐闭环：

1. 按 Score、Volume、GSC impressions、intent 和 source 筛选，记录 decision；
2. 将关键词归入现有 cluster、同域 target URL 或现有 Content item；
3. 在 **Topic Map** 检查未归属、多个计划 URL、多个 Content item、同一 query 多 URL 竞争和没有内容承接的簇；
4. 对 prioritize 且缺少研究的关键词运行 **Agent deep dive**；已有文档直接打开，缺少时只复制 agent 请求，不创建空 Markdown；
5. 从 Content 完成写作和上线，再从 Pages/GSC 回看 measured 状态。

批量栏支持当前页或全部筛选结果，单次最多 1,000 条。写入采用文件 revision 和全有或全无校验：cluster、Content ID 或 URL 任一非法时整批不写，agent 或另一个 UI 会话已修改关键词池时返回冲突而不会覆盖。被修改的历史记录会保留 Feishu `source_record` 和其他未知字段。

关键词池应先来自本项目的研究和判断。需要继承飞书已有关键词或历史文章时再运行：

```bash
./seo --project hexcal content import-feishu --profile hexcal-seo --json
```

导入采用补充式合并：同 ID 的 Workbench 标题、关键词、状态、草稿和人工备注优先；飞书新增记录可以进入队列。

需要补充 Semrush 或 Google Ads 时继续使用本地文件采集，不接入第二个关键词主库：

```bash
./seo --project hexcal keywords collect \
  --semrush-xlsx semrush.xlsx \
  --google-ads-csv google-ads.csv --json
```

根据当前关键词池生成聚类任务：

```bash
./seo --project hexcal content cluster-brief --json
```

让当前 agent 按生成文件中的 `expected_output_schema` 和项目 `context/`、`strategy/` 资料完成 `clusters.json`，再导入：

```bash
./seo --project hexcal content import-clusters --from-file clusters.json --json
./seo --project hexcal content queue --status planned --json
```

SEO 负责人确认选题后，才进入写作：

```bash
./seo --project hexcal content status <item_id> ready_to_write \
  --note "topic approved by SEO owner" --json
```

## 3. 写作与素材

导出写作 brief：

```bash
./seo --project hexcal content brief <item_id> --json
```

写作者使用本项目的 `skills/content-brief`、`skills/write-content` 和 brief，不以飞书旧流程的 prompt 作为内容标准。

只有文章需要旧素材库图片时，才运行素材路线：

```bash
./seo --project hexcal content asset-candidates <item_id> --profile hexcal-seo --json
./seo --project hexcal content describe-candidates <item_id> --profile hexcal-seo --no-writeback --json
# 确认要把新描述回写飞书时：
./seo --project hexcal content describe-candidates <item_id> --profile hexcal-seo --confirm --json
./seo --project hexcal content download-assets <item_id> --profile hexcal-seo --json
./seo --project hexcal content upload-assets <item_id> --json
./seo --project hexcal content apply-assets <item_id> --json
```

草稿导入文件至少需要以下结构。`scheduled_at` 必须包含时区，导入后统一保存为 UTC：

```json
{
  "item_id": "example-topic",
  "qc_status": "review_ready",
  "article": {
    "title": "Article title",
    "slug": "article-slug",
    "meta_description": "Search result description",
    "target_keyword": "primary keyword",
    "scheduled_at": "2026-08-10T09:00:00+08:00",
    "draft_html": "<h2>Useful section</h2><p>Reviewed article body.</p>",
    "internal_links": []
  }
}
```

```bash
./seo --project hexcal content import-draft --from-file article.json --json
./seo --project hexcal content qc <item_id> --json
```

## 4. 人工审核与发布

修订意见可以直接写入 Workbench，也可以显式推送到飞书评审：

```bash
./seo --project hexcal content review-push <item_id> \
  --role seo_review --profile hexcal-seo --confirm --json
./seo --project hexcal content review-digest --profile hexcal-seo --json
```

飞书回复只生成建议，不自动改变状态。SEO 负责人最终确认：

```bash
./seo --project hexcal content status <item_id> approved \
  --note "human approved" --json
```

先检查 Shopify payload，再执行真实写入：

```bash
./seo --project hexcal content publish-dry-run <item_id> \
  --blog-id <blog_id> --json
./seo --project hexcal content publish <item_id> \
  --blog-id <blog_id> --confirm --json
```

新文章有 `scheduled_at` 时会创建 Shopify 排期；已有 `shopify_article_id` 时走更新。只有 Shopify 返回文章 ID、URL 和发布时间后，本地状态才变为 `scheduled`。QC 阻断项和未审批状态不能通过 `--allow-warnings` 绕过。

## 5. 收录检测与通知

普通 BLOG 不使用 Google Indexing API。发布时间到达后，由 Sitemap 发现和 GSC URL Inspection 判断：

```bash
./seo --project hexcal content index-queue --json
./seo --project hexcal gsc inspect --limit 10 --json
./seo --project hexcal content index-status \
  --notify-role seo --profile hexcal-seo --confirm --json
```

只有 GSC 返回已收录时才发送飞书消息。发送失败不会写入“已通知”标记，下次运行可以重试；成功后不会重复发送。同一 URL 长时间未收录会进入 `indexing_issue`，由 SEO 负责人检查 canonical、Sitemap、内容质量和站内链接。

## 6. 每日收工

```bash
./seo --project hexcal content ops --json
./seo --project hexcal content report --period daily --json
./seo --project hexcal validate --json
```

生产日的完成标准：没有未经人工确认的 Shopify/飞书写入；文章状态、排期和 live URL 可在 Content 查看；发布与 GSC 运行记录保存在 `audits/`；需要处理的问题显示在 `content ops`。

## 当前边界

- Workbench 不运行常驻 cron；Shopify 接收排期后负责在指定时间上线。
- GSC 与飞书检测由操作者或外部调度按日触发。
- 飞书导入是可选补充，不能替代 Workbench 的选题和人工审批。
- Keywords 只写本地决策，不发布内容、不修改站点、不执行重定向或索引提交。
- `discovered → researched → mapped → in_production → live → measured` 由现有 research、Content、Portfolio 和 GSC 事实自动推导，不允许人工改阶段。
