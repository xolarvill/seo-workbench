# 本地 skills 来源与上游比对参考

本文件是技能来源维护入口，配套的 [skill-sources.json](skill-sources.json) 保存完整文件映射、内容指纹、本地历史和引用关系。最后核查：**2026-10-29（Asia/Shanghai）**。本轮对应[技能复审](20261029-local-skills-review.md)之后的第 1 步：建立清单；目录、正文和技能映射保持现状。

## 快速查询

- 查某个技能来自哪里：在下方入口表中找名称，打开固定版本的上游链接。
- 查 references、assets、许可证等配套文件：在 JSON 的 `files` 中按 `local_path` 查找。所有 364 个 Git 跟踪文件均有记录。
- 查本地何时修改：查看 `first_local_record`、`last_local_change`，再用 Git 读取对应文件差异。
- 查旧工具路径和断开的引用：在 JSON 的 `dependencies` 中按 `from_path` 或 `target` 查询。后续修复应更新这里的状态。
- 查升级范围：比较同一来源的 `comparison_ref` 与新提交，按本文后面的步骤审阅。

来源表、入口表和 JSON 是同一次清点的两种视图。目录迁移后应同步更新 `local_path`、`current_owner_path` 和本文件的链接，保留 `id`、`upstream_path` 及 `path_history` 中的旧路径。

## 来源及固定版本

| 来源 ID | 原仓库 | 本次比较版本 | 固定提交 | 仓库根许可证 |
|---|---|---|---|---|
| superseo | [inhouseseo/superseo-skills](https://github.com/inhouseseo/superseo-skills) | v0.2.1，2026-09-03 | [`9cf22cc`](https://github.com/inhouseseo/superseo-skills/commit/9cf22cc065a294bf0077ea6af6b4ea0eb7f89cdc) | Apache-2.0，保留 NOTICE |
| claude-seo | [AgriciDaniel/claude-seo](https://github.com/AgriciDaniel/claude-seo) | v2.5.0，2026-10-22 | [`6be93f4`](https://github.com/AgriciDaniel/claude-seo/commit/6be93f45064ffbadced572b5d5c95f55fd263af0) | MIT |
| seomachine | [TheCraigHewitt/seomachine](https://github.com/TheCraigHewitt/seomachine) | 默认分支快照，2026-10-23 | [`120e7b4`](https://github.com/TheCraigHewitt/seomachine/commit/120e7b46dc07c98382cd4f68ac5b6515ab9f2604) | MIT |
| workbench | 本仓库 | 当前本地记录 | 见 JSON 的 `local_snapshot_commit` | 本仓库原生文件 |

本轮经 GitHub 连接器读取三家的完整递归树（均未截断）及默认分支提交，三个固定提交仍是本次观察到的默认分支 HEAD。今后更新以记录的日期和固定提交为准；仓库首页随时可能继续变化。

原始导入时的上游提交尚无可确认的记录，统一保存为 `baseline_unknown`，`imported_upstream_commit` 为 null。`comparison_ref` 是这次比对的上游版本，**不表示该版本已被整套导入**。本地首次记录的 Git commit 也不能代替原始上游版本。

许可证原文与归属见 [third_party/NOTICE.md](../third_party/NOTICE.md)。JSON 的 `local_license_paths` 指向本地保留文件。部分 FLOW 参考材料自带 `AgriciDaniel/flow`、`CC BY 4.0` 和同步日期声明；43 个文件的这类声明已保存在 `declared_attribution` 中。维护时保留这层来源，不能仅套用外层仓库的 MIT 标记。这里只登记文件已有声明，未把声明中的同步日期推断为已核实的原始提交。

## 本轮清点范围

| 来源 | 全部跟踪文件 | 技能正文 | 专家方法 | 流程文档 | 与固定上游逐字节相同 | 与固定上游有差异 |
|---|---:|---:|---:|---:|---:|---:|
| SuperSEO | 125 | 11 | 0 | 0 | 108 | 17 |
| Claude SEO | 140 | 24 | 0 | 0 | 40 | 100 |
| SEO Machine | 93 | 26 | 11 | 24 | 92 | 1 |
| Workbench | 6 | 3 | 0 | 0 | 不适用 | 不适用 |
| 合计 | **364** | **64** | **11** | **24** | **240** | **118** |

全部文件还包括 235 份 references、9 份 assets、19 份许可证、1 份索引和 1 份 agent metadata。这里采用文件类型的互斥计数；专家方法和流程文档不重复计入 references。

JSON 仅覆盖 `git ls-files skills`，不包含未跟踪文件、系统文件或店铺私有技能。逐字节比对使用本地 Git blob SHA 与固定上游树的 blob SHA；包括换行差异。`different` 只表示内容不同，未据此判定哪一份更正确，或哪些差异属于本地适配。

当前上游而本地尚无对应入口的技能：Claude SEO 的 `skills/seo-agentic/SKILL.md` 和 `skills/seo-content-brief/SKILL.md`。JSON 的 `upstream_skill_entrypoints_not_mapped` 保留这些路径；是否新建入口或吸收进既有方法由后续步骤决定。

## 文件清单字段

| 字段 | 含义与更新方式 |
|---|---|
| `id` | 稳定记录 ID：来源 ID 加上游路径；原生文件使用首次登记路径。迁移本地目录时保留 ID |
| `local_path` / `path_history` | 当前路径和历次登记路径；移动时追加旧路径，保留一个当前文件 |
| `kind` / `capability` / `current_owner_path` | 文件类型、现有能力标签、当前 SKILL.md 入口；独立专家和流程材料没有主入口时为 null。标签记录现状，不预先决定第 2 步的合并归属 |
| `source_id` / `upstream_path` | 对应来源及其固定版本中的原文件位置；可与来源表拼接为 blob URL |
| `baseline_status` / `imported_upstream_commit` | 区分原生文件和未知原始导入基线；只有找到明确证据才能补原始版本 |
| `local_sha256` / `local_git_blob_sha` | 本次本地内容指纹；前者便于文件核对，后者便于与 GitHub 树比较 |
| `comparison_upstream_blob_sha` / `comparison_status` | 固定上游的文件指纹与相同／不同状态；原生文件使用 workbench_native |
| `first_local_record` / `last_local_change` | 当前路径在本分支历史中最早和最新的变更记录，包含 commit、日期与标题；格式或文件模式变更也可能产生记录 |
| `content_changed_since_first_local_record` | 当前内容与最早本地记录的内容是否不同；false 不代表导入时未经适配 |
| `semantic_review` | 本清点统一为 not_assessed_by_inventory；内容指纹检查不代替方法质量审阅，既有专业诊断见复审报告 |
| `declared_attribution` | 文件头已有的更细来源、许可证与同步日期，保留原声明的证据类型 |

来源级 `comparison_ref`、`tree_sha`、`reviewed_on`、许可证位置由所有文件共享。`local_snapshot_commit` 记录清点前的本地 HEAD，清点结果及文档本身由此次 docs commit 留痕。

## 引用关系与适配线索

本轮登记 432 处字面路径引用：Markdown 链接目标，以及指定前缀的无空白反引号路径。每条保存来源文件、行号、原始目标、解析位置和状态。它用于后续修复定位，不执行其中的命令。

| 状态 | 解释 |
|---|---|
| resolved_local | 按记录的路径解析规则在本地存在 |
| missing_literal_target | 字面目标在本地不存在；需结合上下文判断是否是原仓库布局、示例或实际缺件 |
| upstream_runtime_reference | 指向原插件根目录、原脚本或 `.claude` 环境，本地没有相应路径 |
| project_context_reference | 当前项目的 context、strategy、audits 等动态资料引用，不能按仓库根目录的存在性判断 |
| template_reference | 含占位符或通配符，需要具体任务参数 |
| route_or_example | 以 `/` 开头的站内路由或示例，未当作磁盘路径 |

完整数量保存在 JSON 的 `summary.dependencies_by_status`。`missing_literal_target` 是候选清单，不能把总数当作已确认故障数。先前确认的 4 个营销技能、25 处 `../../tools/...` 引用可以直接在这里定位。

扫描器不解析完整 Markdown AST、裸写路径、所有 shell 命令或跨段落语义；这次清点不承诺完整执行依赖图。后续引用修复仍需阅读正文上下文，尤其是 FLOW 的原来源路径和 Claude SEO 共享参考文件。

已知本地适配线索可从以下位置恢复：

- 核心 SuperSEO 方法：当前 reader-experience-review 接入、事实依据、非机械字数／密度规则；参见[复审报告](20261029-local-skills-review.md)。
- Claude SEO 核心入口：技术采集、证据资格、字段性能数据与当前结构化数据规则；结合 AGENTS 和对应文件的本地 Git 差异阅读。
- Workbench 原生方法：project-context、headless-precheck、reader-experience-review 没有对应的外部上游正文。
- 每文件的实际本地变更可由 JSON 的 commit 指针恢复，不把“与上游不同”统一归类为本地补丁。

## 以后如何比对上游更新

1. **先检查本地漂移。** 确认当前路径、内容指纹和本地修改；保留已批准规则。目录迁移应先更新路径历史再继续比较。
2. **固定新上游提交。** 读取来源表仓库的新 HEAD 或发布 tag，记录完整 SHA、版本和核查日期；使用固定 SHA 读取 changelog、完整文件树和需要审阅的正文。
3. **区分两种差异。** 比较旧 `comparison_ref` 与新提交，得到上游新增／修改／删除；再比较已登记的固定上游与当前本地内容，识别待判读差异。原始导入基线未知时不要把比较版本当作自动三方合并基线。
4. **逐项选择吸收。** 对照本地 Git 历史、当前证据规则和质量标准决定合入内容。新增参考文件、路径和运行依赖一起审查，保留原归属和许可证。目录与名称不再决定方法优先级。
5. **记录采用与保留。** 在本次变更文档写明吸收的条目、保留的本地适配、未采用内容及理由。比较过的新版本和已吸收的内容分别记录，不将核查版本写成整包升级完成。
6. **更新清单并验证。** 刷新本地指纹、上游 blob SHA、引用关系、日期、文件增删和本页入口表。修改工作流或技能映射时再运行项目 validate 与相关回归；各层单独提交。

可以通过 GitHub 连接器读取 `https://api.github.com/repos/<owner>/<repo>/git/trees/<sha>?recursive=1`，确认 `truncated=false` 后使用。既有上游内容可按 JSON 的路径和固定 SHA 重取，不依赖这次核查的临时文件。

查一个文件的当前清单记录，在仓库根目录运行：

```bash
.venv/bin/python - <<'PY'
import json
from pathlib import Path

inventory = json.loads(Path('docs/skill-sources.json').read_text())
record = next(row for row in inventory['files']
              if row['local_path'] == 'skills/write-content/SKILL.md')
print(json.dumps(record, ensure_ascii=False, indent=2))
PY
```

核对清单覆盖和本地内容指纹：

```bash
.venv/bin/python - <<'PY'
import hashlib
import json
from pathlib import Path
import subprocess

inventory = json.loads(Path('docs/skill-sources.json').read_text())
tracked = set(filter(None, subprocess.check_output(
    ['git', 'ls-files', '-z', 'skills']).decode().split('\0')))
recorded = {row['local_path'] for row in inventory['files']}
assert len(recorded) == len(inventory['files']), 'duplicate local paths'
assert recorded == tracked, 'tracked file coverage changed'
for row in inventory['files']:
    digest = hashlib.sha256(Path(row['local_path']).read_bytes()).hexdigest()
    assert digest == row['local_sha256'], row['local_path']
print(f'{len(recorded)} files: coverage and SHA-256 verified')
PY
```

以下入口表覆盖 64 个技能正文、11 份专家方法和 24 份流程文档。其余配套文件的逐项映射在 JSON 中。

## 入口与上游文件映射

### superseo / skill（11）

| 当前文件 | 固定版本中的上游路径 | 内容比对 | 本地首次记录 |
|---|---|---|---|
| [skills/content-brief/SKILL.md](../skills/content-brief/SKILL.md) | [skills/content-brief/SKILL.md](https://github.com/inhouseseo/superseo-skills/blob/9cf22cc065a294bf0077ea6af6b4ea0eb7f89cdc/skills/content-brief/SKILL.md) | 有差异 | `05a9340` |
| [skills/eeat-audit/SKILL.md](../skills/eeat-audit/SKILL.md) | [skills/eeat-audit/SKILL.md](https://github.com/inhouseseo/superseo-skills/blob/9cf22cc065a294bf0077ea6af6b4ea0eb7f89cdc/skills/eeat-audit/SKILL.md) | 有差异 | `45c60ef` |
| [skills/expert-interview/SKILL.md](../skills/expert-interview/SKILL.md) | [skills/expert-interview/SKILL.md](https://github.com/inhouseseo/superseo-skills/blob/9cf22cc065a294bf0077ea6af6b4ea0eb7f89cdc/skills/expert-interview/SKILL.md) | 相同 | `f0116d2` |
| [skills/featured-snippet-optimizer/SKILL.md](../skills/featured-snippet-optimizer/SKILL.md) | [skills/featured-snippet-optimizer/SKILL.md](https://github.com/inhouseseo/superseo-skills/blob/9cf22cc065a294bf0077ea6af6b4ea0eb7f89cdc/skills/featured-snippet-optimizer/SKILL.md) | 有差异 | `f0116d2` |
| [skills/improve-content/SKILL.md](../skills/improve-content/SKILL.md) | [skills/improve-content/SKILL.md](https://github.com/inhouseseo/superseo-skills/blob/9cf22cc065a294bf0077ea6af6b4ea0eb7f89cdc/skills/improve-content/SKILL.md) | 有差异 | `f0116d2` |
| [skills/keyword-deep-dive/SKILL.md](../skills/keyword-deep-dive/SKILL.md) | [skills/keyword-deep-dive/SKILL.md](https://github.com/inhouseseo/superseo-skills/blob/9cf22cc065a294bf0077ea6af6b4ea0eb7f89cdc/skills/keyword-deep-dive/SKILL.md) | 有差异 | `05a9340` |
| [skills/linkbuilding/SKILL.md](../skills/linkbuilding/SKILL.md) | [skills/linkbuilding/SKILL.md](https://github.com/inhouseseo/superseo-skills/blob/9cf22cc065a294bf0077ea6af6b4ea0eb7f89cdc/skills/linkbuilding/SKILL.md) | 有差异 | `45c60ef` |
| [skills/page-audit/SKILL.md](../skills/page-audit/SKILL.md) | [skills/page-audit/SKILL.md](https://github.com/inhouseseo/superseo-skills/blob/9cf22cc065a294bf0077ea6af6b4ea0eb7f89cdc/skills/page-audit/SKILL.md) | 有差异 | `d08f066` |
| [skills/semantic-gap-analysis/SKILL.md](../skills/semantic-gap-analysis/SKILL.md) | [skills/semantic-gap-analysis/SKILL.md](https://github.com/inhouseseo/superseo-skills/blob/9cf22cc065a294bf0077ea6af6b4ea0eb7f89cdc/skills/semantic-gap-analysis/SKILL.md) | 有差异 | `45c60ef` |
| [skills/topic-cluster-planning/SKILL.md](../skills/topic-cluster-planning/SKILL.md) | [skills/topic-cluster-planning/SKILL.md](https://github.com/inhouseseo/superseo-skills/blob/9cf22cc065a294bf0077ea6af6b4ea0eb7f89cdc/skills/topic-cluster-planning/SKILL.md) | 有差异 | `45c60ef` |
| [skills/write-content/SKILL.md](../skills/write-content/SKILL.md) | [skills/write-content/SKILL.md](https://github.com/inhouseseo/superseo-skills/blob/9cf22cc065a294bf0077ea6af6b4ea0eb7f89cdc/skills/write-content/SKILL.md) | 有差异 | `d08f066` |

### claude-seo / skill（24）

| 当前文件 | 固定版本中的上游路径 | 内容比对 | 本地首次记录 |
|---|---|---|---|
| [skills/backlinks/SKILL.md](../skills/backlinks/SKILL.md) | [skills/seo-backlinks/SKILL.md](https://github.com/AgriciDaniel/claude-seo/blob/6be93f45064ffbadced572b5d5c95f55fd263af0/skills/seo-backlinks/SKILL.md) | 有差异 | `45c60ef` |
| [skills/claude-seo-extra/seo-audit/SKILL.md](../skills/claude-seo-extra/seo-audit/SKILL.md) | [skills/seo-audit/SKILL.md](https://github.com/AgriciDaniel/claude-seo/blob/6be93f45064ffbadced572b5d5c95f55fd263af0/skills/seo-audit/SKILL.md) | 有差异 | `f0116d2` |
| [skills/claude-seo-extra/seo-cluster/SKILL.md](../skills/claude-seo-extra/seo-cluster/SKILL.md) | [skills/seo-cluster/SKILL.md](https://github.com/AgriciDaniel/claude-seo/blob/6be93f45064ffbadced572b5d5c95f55fd263af0/skills/seo-cluster/SKILL.md) | 有差异 | `f0116d2` |
| [skills/claude-seo-extra/seo-competitor-pages/SKILL.md](../skills/claude-seo-extra/seo-competitor-pages/SKILL.md) | [skills/seo-competitor-pages/SKILL.md](https://github.com/AgriciDaniel/claude-seo/blob/6be93f45064ffbadced572b5d5c95f55fd263af0/skills/seo-competitor-pages/SKILL.md) | 有差异 | `f0116d2` |
| [skills/claude-seo-extra/seo-content/SKILL.md](../skills/claude-seo-extra/seo-content/SKILL.md) | [skills/seo-content/SKILL.md](https://github.com/AgriciDaniel/claude-seo/blob/6be93f45064ffbadced572b5d5c95f55fd263af0/skills/seo-content/SKILL.md) | 有差异 | `f0116d2` |
| [skills/claude-seo-extra/seo-dataforseo/SKILL.md](../skills/claude-seo-extra/seo-dataforseo/SKILL.md) | [skills/seo-dataforseo/SKILL.md](https://github.com/AgriciDaniel/claude-seo/blob/6be93f45064ffbadced572b5d5c95f55fd263af0/skills/seo-dataforseo/SKILL.md) | 有差异 | `f0116d2` |
| [skills/claude-seo-extra/seo-ecommerce/SKILL.md](../skills/claude-seo-extra/seo-ecommerce/SKILL.md) | [skills/seo-ecommerce/SKILL.md](https://github.com/AgriciDaniel/claude-seo/blob/6be93f45064ffbadced572b5d5c95f55fd263af0/skills/seo-ecommerce/SKILL.md) | 有差异 | `f0116d2` |
| [skills/claude-seo-extra/seo-flow/SKILL.md](../skills/claude-seo-extra/seo-flow/SKILL.md) | [skills/seo-flow/SKILL.md](https://github.com/AgriciDaniel/claude-seo/blob/6be93f45064ffbadced572b5d5c95f55fd263af0/skills/seo-flow/SKILL.md) | 有差异 | `f0116d2` |
| [skills/claude-seo-extra/seo-geo/SKILL.md](../skills/claude-seo-extra/seo-geo/SKILL.md) | [skills/seo-geo/SKILL.md](https://github.com/AgriciDaniel/claude-seo/blob/6be93f45064ffbadced572b5d5c95f55fd263af0/skills/seo-geo/SKILL.md) | 有差异 | `f0116d2` |
| [skills/claude-seo-extra/seo-google/SKILL.md](../skills/claude-seo-extra/seo-google/SKILL.md) | [skills/seo-google/SKILL.md](https://github.com/AgriciDaniel/claude-seo/blob/6be93f45064ffbadced572b5d5c95f55fd263af0/skills/seo-google/SKILL.md) | 有差异 | `f0116d2` |
| [skills/claude-seo-extra/seo-hreflang/SKILL.md](../skills/claude-seo-extra/seo-hreflang/SKILL.md) | [skills/seo-hreflang/SKILL.md](https://github.com/AgriciDaniel/claude-seo/blob/6be93f45064ffbadced572b5d5c95f55fd263af0/skills/seo-hreflang/SKILL.md) | 有差异 | `f0116d2` |
| [skills/claude-seo-extra/seo-image-gen/SKILL.md](../skills/claude-seo-extra/seo-image-gen/SKILL.md) | [skills/seo-image-gen/SKILL.md](https://github.com/AgriciDaniel/claude-seo/blob/6be93f45064ffbadced572b5d5c95f55fd263af0/skills/seo-image-gen/SKILL.md) | 有差异 | `f0116d2` |
| [skills/claude-seo-extra/seo-local/SKILL.md](../skills/claude-seo-extra/seo-local/SKILL.md) | [skills/seo-local/SKILL.md](https://github.com/AgriciDaniel/claude-seo/blob/6be93f45064ffbadced572b5d5c95f55fd263af0/skills/seo-local/SKILL.md) | 有差异 | `f0116d2` |
| [skills/claude-seo-extra/seo-maps/SKILL.md](../skills/claude-seo-extra/seo-maps/SKILL.md) | [skills/seo-maps/SKILL.md](https://github.com/AgriciDaniel/claude-seo/blob/6be93f45064ffbadced572b5d5c95f55fd263af0/skills/seo-maps/SKILL.md) | 有差异 | `f0116d2` |
| [skills/claude-seo-extra/seo-page/SKILL.md](../skills/claude-seo-extra/seo-page/SKILL.md) | [skills/seo-page/SKILL.md](https://github.com/AgriciDaniel/claude-seo/blob/6be93f45064ffbadced572b5d5c95f55fd263af0/skills/seo-page/SKILL.md) | 有差异 | `f0116d2` |
| [skills/claude-seo-extra/seo-plan/SKILL.md](../skills/claude-seo-extra/seo-plan/SKILL.md) | [skills/seo-plan/SKILL.md](https://github.com/AgriciDaniel/claude-seo/blob/6be93f45064ffbadced572b5d5c95f55fd263af0/skills/seo-plan/SKILL.md) | 有差异 | `f0116d2` |
| [skills/claude-seo-extra/seo-programmatic/SKILL.md](../skills/claude-seo-extra/seo-programmatic/SKILL.md) | [skills/seo-programmatic/SKILL.md](https://github.com/AgriciDaniel/claude-seo/blob/6be93f45064ffbadced572b5d5c95f55fd263af0/skills/seo-programmatic/SKILL.md) | 有差异 | `f0116d2` |
| [skills/claude-seo-extra/seo-sxo/SKILL.md](../skills/claude-seo-extra/seo-sxo/SKILL.md) | [skills/seo-sxo/SKILL.md](https://github.com/AgriciDaniel/claude-seo/blob/6be93f45064ffbadced572b5d5c95f55fd263af0/skills/seo-sxo/SKILL.md) | 有差异 | `f0116d2` |
| [skills/claude-seo-extra/seo/SKILL.md](../skills/claude-seo-extra/seo/SKILL.md) | [skills/seo/SKILL.md](https://github.com/AgriciDaniel/claude-seo/blob/6be93f45064ffbadced572b5d5c95f55fd263af0/skills/seo/SKILL.md) | 有差异 | `f0116d2` |
| [skills/drift/SKILL.md](../skills/drift/SKILL.md) | [skills/seo-drift/SKILL.md](https://github.com/AgriciDaniel/claude-seo/blob/6be93f45064ffbadced572b5d5c95f55fd263af0/skills/seo-drift/SKILL.md) | 有差异 | `45c60ef` |
| [skills/images/SKILL.md](../skills/images/SKILL.md) | [skills/seo-images/SKILL.md](https://github.com/AgriciDaniel/claude-seo/blob/6be93f45064ffbadced572b5d5c95f55fd263af0/skills/seo-images/SKILL.md) | 有差异 | `45c60ef` |
| [skills/schema/SKILL.md](../skills/schema/SKILL.md) | [skills/seo-schema/SKILL.md](https://github.com/AgriciDaniel/claude-seo/blob/6be93f45064ffbadced572b5d5c95f55fd263af0/skills/seo-schema/SKILL.md) | 有差异 | `d08f066` |
| [skills/sitemap/SKILL.md](../skills/sitemap/SKILL.md) | [skills/seo-sitemap/SKILL.md](https://github.com/AgriciDaniel/claude-seo/blob/6be93f45064ffbadced572b5d5c95f55fd263af0/skills/seo-sitemap/SKILL.md) | 有差异 | `45c60ef` |
| [skills/technical-audit/SKILL.md](../skills/technical-audit/SKILL.md) | [skills/seo-technical/SKILL.md](https://github.com/AgriciDaniel/claude-seo/blob/6be93f45064ffbadced572b5d5c95f55fd263af0/skills/seo-technical/SKILL.md) | 有差异 | `05a9340` |

### seomachine / skill（26）

| 当前文件 | 固定版本中的上游路径 | 内容比对 | 本地首次记录 |
|---|---|---|---|
| [skills/seo-machine-pipeline/skills/ab-test-setup/SKILL.md](../skills/seo-machine-pipeline/skills/ab-test-setup/SKILL.md) | [.claude/skills/ab-test-setup/SKILL.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/skills/ab-test-setup/SKILL.md) | 相同 | `f0116d2` |
| [skills/seo-machine-pipeline/skills/analytics-tracking/SKILL.md](../skills/seo-machine-pipeline/skills/analytics-tracking/SKILL.md) | [.claude/skills/analytics-tracking/SKILL.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/skills/analytics-tracking/SKILL.md) | 相同 | `f0116d2` |
| [skills/seo-machine-pipeline/skills/competitor-alternatives/SKILL.md](../skills/seo-machine-pipeline/skills/competitor-alternatives/SKILL.md) | [.claude/skills/competitor-alternatives/SKILL.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/skills/competitor-alternatives/SKILL.md) | 相同 | `f0116d2` |
| [skills/seo-machine-pipeline/skills/content-strategy/SKILL.md](../skills/seo-machine-pipeline/skills/content-strategy/SKILL.md) | [.claude/skills/content-strategy/SKILL.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/skills/content-strategy/SKILL.md) | 相同 | `f0116d2` |
| [skills/seo-machine-pipeline/skills/copy-editing/SKILL.md](../skills/seo-machine-pipeline/skills/copy-editing/SKILL.md) | [.claude/skills/copy-editing/SKILL.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/skills/copy-editing/SKILL.md) | 相同 | `f0116d2` |
| [skills/seo-machine-pipeline/skills/copywriting/SKILL.md](../skills/seo-machine-pipeline/skills/copywriting/SKILL.md) | [.claude/skills/copywriting/SKILL.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/skills/copywriting/SKILL.md) | 相同 | `f0116d2` |
| [skills/seo-machine-pipeline/skills/email-sequence/SKILL.md](../skills/seo-machine-pipeline/skills/email-sequence/SKILL.md) | [.claude/skills/email-sequence/SKILL.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/skills/email-sequence/SKILL.md) | 相同 | `f0116d2` |
| [skills/seo-machine-pipeline/skills/form-cro/SKILL.md](../skills/seo-machine-pipeline/skills/form-cro/SKILL.md) | [.claude/skills/form-cro/SKILL.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/skills/form-cro/SKILL.md) | 相同 | `f0116d2` |
| [skills/seo-machine-pipeline/skills/free-tool-strategy/SKILL.md](../skills/seo-machine-pipeline/skills/free-tool-strategy/SKILL.md) | [.claude/skills/free-tool-strategy/SKILL.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/skills/free-tool-strategy/SKILL.md) | 相同 | `f0116d2` |
| [skills/seo-machine-pipeline/skills/growth-lead-SKILL.md](../skills/seo-machine-pipeline/skills/growth-lead-SKILL.md) | [.claude/skills/growth-lead/SKILL.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/skills/growth-lead/SKILL.md) | 相同 | `f0116d2` |
| [skills/seo-machine-pipeline/skills/launch-strategy/SKILL.md](../skills/seo-machine-pipeline/skills/launch-strategy/SKILL.md) | [.claude/skills/launch-strategy/SKILL.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/skills/launch-strategy/SKILL.md) | 相同 | `f0116d2` |
| [skills/seo-machine-pipeline/skills/marketing-ideas/SKILL.md](../skills/seo-machine-pipeline/skills/marketing-ideas/SKILL.md) | [.claude/skills/marketing-ideas/SKILL.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/skills/marketing-ideas/SKILL.md) | 相同 | `f0116d2` |
| [skills/seo-machine-pipeline/skills/marketing-psychology/SKILL.md](../skills/seo-machine-pipeline/skills/marketing-psychology/SKILL.md) | [.claude/skills/marketing-psychology/SKILL.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/skills/marketing-psychology/SKILL.md) | 相同 | `f0116d2` |
| [skills/seo-machine-pipeline/skills/onboarding-cro/SKILL.md](../skills/seo-machine-pipeline/skills/onboarding-cro/SKILL.md) | [.claude/skills/onboarding-cro/SKILL.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/skills/onboarding-cro/SKILL.md) | 相同 | `f0116d2` |
| [skills/seo-machine-pipeline/skills/page-cro/SKILL.md](../skills/seo-machine-pipeline/skills/page-cro/SKILL.md) | [.claude/skills/page-cro/SKILL.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/skills/page-cro/SKILL.md) | 相同 | `f0116d2` |
| [skills/seo-machine-pipeline/skills/paid-ads/SKILL.md](../skills/seo-machine-pipeline/skills/paid-ads/SKILL.md) | [.claude/skills/paid-ads/SKILL.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/skills/paid-ads/SKILL.md) | 相同 | `f0116d2` |
| [skills/seo-machine-pipeline/skills/paywall-upgrade-cro/SKILL.md](../skills/seo-machine-pipeline/skills/paywall-upgrade-cro/SKILL.md) | [.claude/skills/paywall-upgrade-cro/SKILL.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/skills/paywall-upgrade-cro/SKILL.md) | 相同 | `f0116d2` |
| [skills/seo-machine-pipeline/skills/popup-cro/SKILL.md](../skills/seo-machine-pipeline/skills/popup-cro/SKILL.md) | [.claude/skills/popup-cro/SKILL.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/skills/popup-cro/SKILL.md) | 相同 | `f0116d2` |
| [skills/seo-machine-pipeline/skills/pricing-strategy/SKILL.md](../skills/seo-machine-pipeline/skills/pricing-strategy/SKILL.md) | [.claude/skills/pricing-strategy/SKILL.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/skills/pricing-strategy/SKILL.md) | 相同 | `f0116d2` |
| [skills/seo-machine-pipeline/skills/product-marketing-context/SKILL.md](../skills/seo-machine-pipeline/skills/product-marketing-context/SKILL.md) | [.claude/skills/product-marketing-context/SKILL.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/skills/product-marketing-context/SKILL.md) | 相同 | `f0116d2` |
| [skills/seo-machine-pipeline/skills/programmatic-seo/SKILL.md](../skills/seo-machine-pipeline/skills/programmatic-seo/SKILL.md) | [.claude/skills/programmatic-seo/SKILL.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/skills/programmatic-seo/SKILL.md) | 相同 | `f0116d2` |
| [skills/seo-machine-pipeline/skills/referral-program/SKILL.md](../skills/seo-machine-pipeline/skills/referral-program/SKILL.md) | [.claude/skills/referral-program/SKILL.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/skills/referral-program/SKILL.md) | 相同 | `f0116d2` |
| [skills/seo-machine-pipeline/skills/schema-markup/SKILL.md](../skills/seo-machine-pipeline/skills/schema-markup/SKILL.md) | [.claude/skills/schema-markup/SKILL.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/skills/schema-markup/SKILL.md) | 相同 | `f0116d2` |
| [skills/seo-machine-pipeline/skills/seo-audit/SKILL.md](../skills/seo-machine-pipeline/skills/seo-audit/SKILL.md) | [.claude/skills/seo-audit/SKILL.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/skills/seo-audit/SKILL.md) | 相同 | `f0116d2` |
| [skills/seo-machine-pipeline/skills/signup-flow-cro/SKILL.md](../skills/seo-machine-pipeline/skills/signup-flow-cro/SKILL.md) | [.claude/skills/signup-flow-cro/SKILL.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/skills/signup-flow-cro/SKILL.md) | 相同 | `f0116d2` |
| [skills/seo-machine-pipeline/skills/social-content/SKILL.md](../skills/seo-machine-pipeline/skills/social-content/SKILL.md) | [.claude/skills/social-content/SKILL.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/skills/social-content/SKILL.md) | 相同 | `f0116d2` |

### workbench / skill（3）

| 当前文件 | 固定版本中的上游路径 | 内容比对 | 本地首次记录 |
|---|---|---|---|
| [skills/headless-precheck/SKILL.md](../skills/headless-precheck/SKILL.md) | Workbench 本地方法 | 本地方法 | `45c60ef` |
| [skills/project-context/SKILL.md](../skills/project-context/SKILL.md) | Workbench 本地方法 | 本地方法 | `4146d19` |
| [skills/reader-experience-review/SKILL.md](../skills/reader-experience-review/SKILL.md) | Workbench 本地方法 | 本地方法 | `aff4dea` |

### seomachine / specialist_reference（11）

| 当前文件 | 固定版本中的上游路径 | 内容比对 | 本地首次记录 |
|---|---|---|---|
| [skills/seo-machine-pipeline/agents/cluster-strategist.md](../skills/seo-machine-pipeline/agents/cluster-strategist.md) | [.claude/agents/cluster-strategist.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/agents/cluster-strategist.md) | 相同 | `f0116d2` |
| [skills/seo-machine-pipeline/agents/content-analyzer.md](../skills/seo-machine-pipeline/agents/content-analyzer.md) | [.claude/agents/content-analyzer.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/agents/content-analyzer.md) | 相同 | `f0116d2` |
| [skills/seo-machine-pipeline/agents/cro-analyst.md](../skills/seo-machine-pipeline/agents/cro-analyst.md) | [.claude/agents/cro-analyst.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/agents/cro-analyst.md) | 相同 | `f0116d2` |
| [skills/seo-machine-pipeline/agents/editor.md](../skills/seo-machine-pipeline/agents/editor.md) | [.claude/agents/editor.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/agents/editor.md) | 相同 | `f0116d2` |
| [skills/seo-machine-pipeline/agents/headline-generator.md](../skills/seo-machine-pipeline/agents/headline-generator.md) | [.claude/agents/headline-generator.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/agents/headline-generator.md) | 相同 | `f0116d2` |
| [skills/seo-machine-pipeline/agents/internal-linker.md](../skills/seo-machine-pipeline/agents/internal-linker.md) | [.claude/agents/internal-linker.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/agents/internal-linker.md) | 相同 | `f0116d2` |
| [skills/seo-machine-pipeline/agents/keyword-mapper.md](../skills/seo-machine-pipeline/agents/keyword-mapper.md) | [.claude/agents/keyword-mapper.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/agents/keyword-mapper.md) | 相同 | `f0116d2` |
| [skills/seo-machine-pipeline/agents/landing-page-optimizer.md](../skills/seo-machine-pipeline/agents/landing-page-optimizer.md) | [.claude/agents/landing-page-optimizer.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/agents/landing-page-optimizer.md) | 相同 | `f0116d2` |
| [skills/seo-machine-pipeline/agents/meta-creator.md](../skills/seo-machine-pipeline/agents/meta-creator.md) | [.claude/agents/meta-creator.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/agents/meta-creator.md) | 相同 | `f0116d2` |
| [skills/seo-machine-pipeline/agents/performance.md](../skills/seo-machine-pipeline/agents/performance.md) | [.claude/agents/performance.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/agents/performance.md) | 相同 | `f0116d2` |
| [skills/seo-machine-pipeline/agents/seo-optimizer.md](../skills/seo-machine-pipeline/agents/seo-optimizer.md) | [.claude/agents/seo-optimizer.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/agents/seo-optimizer.md) | 相同 | `f0116d2` |

### seomachine / workflow_reference（24）

| 当前文件 | 固定版本中的上游路径 | 内容比对 | 本地首次记录 |
|---|---|---|---|
| [skills/seo-machine-pipeline/commands/analyze-existing.md](../skills/seo-machine-pipeline/commands/analyze-existing.md) | [.claude/commands/analyze-existing.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/commands/analyze-existing.md) | 相同 | `f0116d2` |
| [skills/seo-machine-pipeline/commands/article.md](../skills/seo-machine-pipeline/commands/article.md) | [.claude/commands/article.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/commands/article.md) | 相同 | `f0116d2` |
| [skills/seo-machine-pipeline/commands/cluster.md](../skills/seo-machine-pipeline/commands/cluster.md) | [.claude/commands/cluster.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/commands/cluster.md) | 相同 | `f0116d2` |
| [skills/seo-machine-pipeline/commands/content-calendar.md](../skills/seo-machine-pipeline/commands/content-calendar.md) | [.claude/commands/content-calendar.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/commands/content-calendar.md) | 相同 | `f0116d2` |
| [skills/seo-machine-pipeline/commands/landing-audit.md](../skills/seo-machine-pipeline/commands/landing-audit.md) | [.claude/commands/landing-audit.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/commands/landing-audit.md) | 相同 | `f0116d2` |
| [skills/seo-machine-pipeline/commands/landing-competitor.md](../skills/seo-machine-pipeline/commands/landing-competitor.md) | [.claude/commands/landing-competitor.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/commands/landing-competitor.md) | 相同 | `f0116d2` |
| [skills/seo-machine-pipeline/commands/landing-publish.md](../skills/seo-machine-pipeline/commands/landing-publish.md) | [.claude/commands/landing-publish.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/commands/landing-publish.md) | 相同 | `f0116d2` |
| [skills/seo-machine-pipeline/commands/landing-research.md](../skills/seo-machine-pipeline/commands/landing-research.md) | [.claude/commands/landing-research.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/commands/landing-research.md) | 相同 | `f0116d2` |
| [skills/seo-machine-pipeline/commands/landing-write.md](../skills/seo-machine-pipeline/commands/landing-write.md) | [.claude/commands/landing-write.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/commands/landing-write.md) | 相同 | `f0116d2` |
| [skills/seo-machine-pipeline/commands/optimize.md](../skills/seo-machine-pipeline/commands/optimize.md) | [.claude/commands/optimize.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/commands/optimize.md) | 相同 | `f0116d2` |
| [skills/seo-machine-pipeline/commands/performance-review.md](../skills/seo-machine-pipeline/commands/performance-review.md) | [.claude/commands/performance-review.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/commands/performance-review.md) | 相同 | `f0116d2` |
| [skills/seo-machine-pipeline/commands/priorities.md](../skills/seo-machine-pipeline/commands/priorities.md) | [.claude/commands/priorities.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/commands/priorities.md) | 相同 | `f0116d2` |
| [skills/seo-machine-pipeline/commands/publish-draft.md](../skills/seo-machine-pipeline/commands/publish-draft.md) | [.claude/commands/publish-draft.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/commands/publish-draft.md) | 相同 | `f0116d2` |
| [skills/seo-machine-pipeline/commands/repurpose.md](../skills/seo-machine-pipeline/commands/repurpose.md) | [.claude/commands/repurpose.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/commands/repurpose.md) | 有差异 | `f0116d2` |
| [skills/seo-machine-pipeline/commands/research-ai-citations.md](../skills/seo-machine-pipeline/commands/research-ai-citations.md) | [.claude/commands/research-ai-citations.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/commands/research-ai-citations.md) | 相同 | `f0116d2` |
| [skills/seo-machine-pipeline/commands/research-gaps.md](../skills/seo-machine-pipeline/commands/research-gaps.md) | [.claude/commands/research-gaps.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/commands/research-gaps.md) | 相同 | `f0116d2` |
| [skills/seo-machine-pipeline/commands/research-performance.md](../skills/seo-machine-pipeline/commands/research-performance.md) | [.claude/commands/research-performance.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/commands/research-performance.md) | 相同 | `f0116d2` |
| [skills/seo-machine-pipeline/commands/research-serp.md](../skills/seo-machine-pipeline/commands/research-serp.md) | [.claude/commands/research-serp.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/commands/research-serp.md) | 相同 | `f0116d2` |
| [skills/seo-machine-pipeline/commands/research-topics.md](../skills/seo-machine-pipeline/commands/research-topics.md) | [.claude/commands/research-topics.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/commands/research-topics.md) | 相同 | `f0116d2` |
| [skills/seo-machine-pipeline/commands/research-trending.md](../skills/seo-machine-pipeline/commands/research-trending.md) | [.claude/commands/research-trending.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/commands/research-trending.md) | 相同 | `f0116d2` |
| [skills/seo-machine-pipeline/commands/research.md](../skills/seo-machine-pipeline/commands/research.md) | [.claude/commands/research.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/commands/research.md) | 相同 | `f0116d2` |
| [skills/seo-machine-pipeline/commands/rewrite.md](../skills/seo-machine-pipeline/commands/rewrite.md) | [.claude/commands/rewrite.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/commands/rewrite.md) | 相同 | `f0116d2` |
| [skills/seo-machine-pipeline/commands/scrub.md](../skills/seo-machine-pipeline/commands/scrub.md) | [.claude/commands/scrub.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/commands/scrub.md) | 相同 | `f0116d2` |
| [skills/seo-machine-pipeline/commands/write.md](../skills/seo-machine-pipeline/commands/write.md) | [.claude/commands/write.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/commands/write.md) | 相同 | `f0116d2` |
