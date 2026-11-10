# 项目素材库与文章配图

这条能力用于从项目既有飞书 Base 素材库挑选博客封面和正文图：保留素材来源、把附件转成可用于 Shopify 的 CDN 图片、再按文章字段验收。执行层用 Workbench 自有 Feishu gateway，不依赖任何运行中的 bot 或 sibling 仓库。

## 项目绑定

私有绑定放在项目自己的 `.runtime/` 下，不进仓库：

```text
projects/<id>/.runtime/integrations/asset-library.json
projects/<id>/.runtime/feishu/asset-library-profile.json
```

`integrations/asset-library.json` 的模板见 `templates/asset-library.json`：`profile` 是 Workbench 的项目内别名，`config_path` 必须是同项目 `.runtime/` 下的相对路径，跨项目路径和 symlink 会被拒绝。绑定文件与 profile 文件使用 `0600`。

`--profile` 仍是显式覆盖入口；`--config` 只能与显式 `--profile` 同时出现，避免"绑定里的 profile + 临时配置"这类含糊组合。

profile 复用 Feishu profile 结构，只保留素材所需的部分：

- `lark_cli_profile`：实际存在的 CLI profile，不等同于项目名；核对身份与资源可访问性后绑定，不切换全局 CLI profile。
- `identity`：`user` 或 `bot`。列表查询与附件下载使用绑定身份，不静默切换。
- Base 别名 `dcdb`，素材表别名 `ugc_current / ugc_historical / official_v3`。
- 字段别名 `contents_number / product / content_type / rating / notes / creator / contents / times_used / large_file_link / mmx`；`times_used` 是 Blog 渠道使用计数。

真实资源标识、字段映射和访问诊断留在私有项目里。迁移来的字段 ID 只是历史线索，恢复访问后必须用真实 `+field-list` 核实，不能把旧 ID 记成已验证。

## 一次文章配图

先在项目 pipeline 里明确 `product_anchor` 与 `feature_image_refs / inline_image_refs`。`feature` 对应 Shopify 博客的 Image 字段，正文 `<img>` 不会自动填充它。

```bash
./seo --project <id> content asset-candidates <item_id> --json
# 需要视觉描述时才执行；不依赖模型也能人工看图选择
./seo --project <id> content describe-candidates <item_id> --no-writeback --json
./seo --project <id> content assets <item_id> --json
./seo --project <id> content download-assets <item_id> --json
./seo --project <id> content upload-assets <item_id> --json
./seo --project <id> content apply-assets <item_id> --json
```

候选与下载是读取；上传会创建 Shopify 文件；apply 只改本地 pipeline。修改 Shopify 文章是独立动作，按当前任务授权执行，apply 的本地成功不等于后台已保存。

选图规则：候选按商品锚点、素材评级与 Blog 复用计数过滤；封面优先横向全景或工作台场景、主体清楚；正文图解释对应段落，封面与正文不反复用同一素材；caption/alt 描述实际画面，未核实的代际不写成新一代产品，商品图或客户布置不当作本次实测；选中素材必须来自候选或登记过的历史缓存，保存 table + record ID 与来源，不编造引用。

## 稳定获取与可恢复性

1. **实时来源**：先确认 CLI profile、身份、Base 权限、表与字段。附件走 `base +record-download-attachment`；临时下载 URL 不进入正文。
2. **本地缓存**：manifest 里有 `local_path` 不等于文件还在，执行层会确认文件存在且非空。缺失时重新下载；有已知 `source_table` 就按该表定位，不轮询无关表。
3. **CDN 交付**：已解析的 URL 可复用；已有 `shopify_file_id` 时先恢复等待结果，避免超时后重复 `fileCreate`。只有 READY 且有 URL 才算上传完成。
4. **来源状态**：权限失败返回 `failed`，部分源失败返回 `partial`，拒绝访问不当成空素材库；失败保留 `errors`，明确拒绝时停止继续探测同一 Base。
5. **显式缓存降级**：允许使用来源可追溯的本地或 Shopify 缓存，但要记录 `cached_only`、来源 manifest、查看结果和当前 live 状态。缓存成功不证明实时取数正常，使用计数与描述可能陈旧。

附件 adapter 取记录附件字段里的第一个文件；多附件要先明确目标，按 CLI 的 `--file-token` 契约处理。上传可能做技术尺寸优化，需要保留原文件时先留存原件，不能用加工后的字节 hash 冒充原始 hash。

## Manifest 与验收

`content/assets/<item_id>.json` 是本篇素材交付记录，至少保存 `rid / source_table / role / local_path / url / alt`，按实际步骤补 CDN ID、状态、尺寸、来源 manifest 与缓存标记。写稿 payload 的 `feature_image_rid` 要与 pipeline refs 一致，避免下次导入清掉选图引用。

Shopify 保存后回读文章 `image { url altText width height }`。草稿封面修改只提交 image，核对正文、tags、title/meta、handle 未被覆盖、`isPublished / publishedAt` 未变化；后台 draft 验收与公开主题验收分别记录。

回写飞书描述、评级或使用计数需要该具体动作的授权；封面保存不触发素材库回写或发布计数。

## 访问受限时

`91403: you don't have permission` 是资源访问失败：确认对应 Base 是否允许已绑定应用读取，联系资源所有者授权。不要反复重试、静默改身份或用重装 CLI 代替权限修复。授权变更后核实 live schema，再完整跑一次候选 → 附件 → CDN 验证；此前保持 blocked/未验证状态。

## 迁移边界

旧仓库的导出脚本与提示词只作流程来源（候选筛选、视觉匹配、封面/正文角色、附件获取、Shopify 交付）。旧仓库不参与执行，不复制其 API secret、自动写回、固定图片数量或自动裁切规则。
