# Docs 分层与 Hexcal 导入链路移除

日期：2026-11-10（Asia/Shanghai）

## 结论

`docs/` 从平铺 34 份文件改为按用途分三层：`guides/` 面向读者的教程、`reference/` 代理和操作者必须遵守的运行契约、`history/` 带日期的验收与决策记录；根目录只保留索引 `README.md` 和生成的技能溯源 `skill-sources.md`，`design/` 不动。AGENTS.md 因此按任务指向新路径，并新增一句项目记录归属规则：项目报告、上下文、策略、内容与审计留在 `projects/<id>/`，根 `docs/` 只放仓库级文档。

同时移除 Hexcal 单店铺的飞书工作簿导入链路（`import-hexcal`、`import-feishu`、网关同步模块、profile 模板及其测试），保留飞书报告通知、review push 和 digest。共享 profile fixture 改为中性的 `seo-profile` 实例。

## 方法与覆盖

- 移动：`git mv` 保留历史，10 份教程进 `guides/`，12 份运行契约进 `reference/`，10 份带日期记录进 `history/`。
- 链接重写：脚本遍历 AGENTS.md、README.md、`docs/**`、`skills/**` 的相对链接，把 `docs/<file>` 与裸文件名改到新位置；`docs/skill-sources.md` 的 history 链接单列修正。
- 代码侧同步：`seo_workbench/ui.py` 的 `TUTORIALS` 11 条 `filename` 加子目录前缀，`tests/test_ui.py` fixture 与断言、`ui/src/test/components.test.tsx` 的 `source` 同步；`seo_workbench/keyword_workspace.py` 的 `KEYWORD_CONTEXT_POLICY` 与 `tests/test_keyword_workspace.py` 断言改到 `docs/reference/keyword-context-maintenance.md`。
- 溯源清单：`docs/skill-sources.json` 只更新受影响的 6 个文件指纹与 15 条依赖行；`scripts/skill_inventory.py` 修复 Windows 下 `resolved_path` 产出反斜杠且不折叠 `..` 的问题（改为先 `as_posix()` 再 `normpath`）。
- 教程正文：`docs/guides/BLOG生产线操作教程.md` 去掉已退役的 `content import-feishu` 命令块与 `hexcal` 品牌名，改为通用 `my-store` / `blog-profile` 示例。

## 证据

- `git log --oneline`：`b0dc26a` 移除导入链路、`11deeab` docs 分层、`69de487` AGENTS 项目记录归属、`53b2f2d` 依赖路径修复，本条记录随其后提交。
- 链接检查：全仓 394 个 Markdown，剩余 8 处"断链"全部是站点路由与 API 参数示例（`/alternatives/*`、`/email-deliverability`、`around:5000,LAT,LNG`、`SOUTH,WEST,NORTH,EAST`），非文档断链。
- `PYTHONUTF8=1 .venv/Scripts/python.exe scripts/skill_inventory.py check` → `{"ok": true, "files": 409, "errors": []}`。
- `PYTHONUTF8=1 .venv/Scripts/python.exe -m seo_workbench --project neational validate --json` → `{"ok": true, "issues": []}`。
- 测试：`tests/test_ui.py -k "tutorial or markdown_api"` 4 passed / 1 failed（`test_markdown_api_serves_project_local_images` 在干净 HEAD worktree 同样失败，Windows 绝对路径处理）；`tests/test_keyword_workspace.py`、`tests/test_content_assets.py`、`tests/test_content_review_push.py`、`tests/test_content_review_digest.py`、`tests/test_feishu_notify.py`、`tests/test_state_workflow.py` 合计 58 passed / 7 failed，失败均为既有的 symlink 权限（`WinError 1314`）、`0600` 模式与路径分隔符问题。

## 边界

- 保留 `seo_workbench/content_assets.py` 的 `ANCHOR_PRODUCTS`、`MMX_PROMPT` 与 `_require_hexcal_project`，`content_briefs.py` 的 `PRODUCT_LINKS`，`keywords.py` 的 `HEXCAL_BRAND_PATTERN` / `HEXCAL_COMPETITOR_PATTERN`（仅在项目名为 `hexcal` 时启用）。这些是真实店铺的内容与关键词数据，不属于导入链路残留；删除会改变 content brief 与关键词采集结果，需单独决策。
- UI 的 TypeScript 测试未运行（本机无 `node_modules`），本次 TSX 改动仅为删除一个按钮与一处 profile 名。
- 测试失败清单按本机 Windows 环境记录；未在 Linux CI 复跑。
- `docs/design/` 未纳入三层结构，仍保留在根下。

## 后续

- 决策 Hexcal 品牌数据（`content_assets.py`、`content_briefs.py`、`keywords.py`）去留：若保留，建议补一条"店铺专属数据按项目隔离"的说明；若移除，需同步 content brief 与关键词测试。
- 在 Linux CI 复跑上述测试，确认 8 个失败项确为 Windows 环境差异。
- 如需再拆分 `docs/reference/`，按"集成 / 统计 / UI"三组评估，避免再次平铺。
