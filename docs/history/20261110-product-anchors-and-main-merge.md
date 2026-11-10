# 商品锚点外置与 main 分支整合

## 结论

店铺品牌数据不再内置在工作台包内：商品目录改由项目自己的 `context/product-anchors.json` 提供，关键词品牌排除改由项目名与站点主机名推导。此前保留在 `content_assets.py`、`content_briefs.py`、`keywords.py` 的 Hexcal 常量已全部删除。分支随后并入 `origin/main`，采纳其新增的工作契约（`How to work`、`Definition of done`）与 `ui-local-surface.md` 文档，`CLAUDE.md` 改为 `@AGENTS.md` 导入。

## 方法与覆盖

- 新增 `seo_workbench/product_anchors.py`：`load_product_anchors(project_dir)` 读取可选文件 `context/product-anchors.json`，格式为 `{"<anchor>": [{"title": "...", "handle": "..."}]}`；文件缺失或条目缺字段时按空处理，不报错。
- `content_assets.py`：删除 `ANCHOR_PRODUCTS`、`_require_hexcal_project` 及其三处调用；`_allowed_products(project_dir, record)` 改为从项目锚点取标题集合；`MMX_PROMPT` 改为通用措辞。
- `content_briefs.py`：删除 `PRODUCT_LINKS`；`_product_links` 从项目锚点生成 `{title, live_url}`，不再要求项目名为特定值。
- `keywords.py`：删除 `HEXCAL_BRAND_PATTERN` / `HEXCAL_COMPETITOR_PATTERN`；新增 `brand_exclusion_patterns(project_dir)`，用项目名与站点主机名构造品牌正则。
- 测试：`tests/test_keywords.py` 改本地中性图案并新增两条推导测试；`tests/test_content_assets.py` 用 `context/product-anchors.json` fixture 替换适配器断言，并新增锚点读取测试；`tests/test_content_briefs.py` 用 anchors fixture 保持三条商品链接断言。
- 文档：`docs/guides/BLOG生产线操作教程.md` 增补锚点文件契约；`docs/history/20261110-docs-hierarchy-and-hexcal-removal.md` 的边界与后续改为最终状态。
- 合并 `origin/main`（含 `docs: give AGENTS.md a working contract and sectioned rules` 等四个提交）：`AGENTS.md` 保留本分支的任务路由结构，同时吸收 `How to work` 与 `Definition of done` 两节；`CLAUDE.md` 改为 `@AGENTS.md`；main 新增的 `docs/ui-local-surface.md` 移入 `docs/reference/` 并在 `docs/README.md` 与 AGENTS 路由表登记。

## 证据

- `PYTHONUTF8=1 .venv/Scripts/python.exe -m pytest tests/test_content_assets.py tests/test_content_briefs.py tests/test_keywords.py tests/test_content_publish.py tests/test_metadata_ops.py tests/test_feishu_notify.py tests/test_content_ops.py tests/test_content_quality.py tests/test_content_drafts.py tests/test_content_clusters.py tests/test_content_review_push.py tests/test_content_review_digest.py -q` → 81 passed, 3 failed。
- 三个失败均为既有 Windows 路径分隔符断言（`content/assets/...` vs `content\assets\...`），在干净 HEAD worktree 同样失败。
- `PYTHONUTF8=1 .venv/Scripts/python.exe -m seo_workbench --project neational validate --json` → `{"ok": true, "issues": []}`。

## 边界

- 测试文件中仍有以 `Hexcal` 作为示例项目名与示例域名的 fixture，它们不构成商品目录数据，未在本次一并替换。
- 合并后 `AGENTS.md` 的 `Definition of done` 以精简条目保留，不重复 main 原文的逐任务长列表；判定标准不变。
- 关键词品牌排除改为按项目名与主机名推导后，不再包含竞品品牌列表；竞品排除目前只依赖数据源的通用噪声规则。

## 后续

- 2026-11-17 前：确认是否需要在项目上下文里声明竞品品牌排除，若需要，在 `context/product-anchors.json` 之外新增独立文件并补测试。
- 下一次接触 content brief 或素材路线的任务时，验证真实项目的 `context/product-anchors.json` 是否已按本契约建立。
