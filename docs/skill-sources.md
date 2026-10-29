# 本地 skills 来源与上游比对参考

本文件是技能来源维护入口，配套的 [skill-sources.json](skill-sources.json) 保存完整文件映射、内容指纹、本地历史和引用关系。最后核查：**2026-10-29（Asia/Shanghai）**。第 1 步建立来源基线；第 2、3 步已按[能力归属与目录迁移记录](20261029-skill-layout-migration.md)更新为 60 个一级入口。

第 4、5 步的[方法与运行适配记录](20261029-skill-methods-runtime-adaptation.md)保存了专业参考归属、失效执行引用的处理与验证。第 6、7、8 步见[写作与上游适配](20261029-skill-writing-upstream-adaptation.md)。

## 快速查询

- 查某个技能来自哪里：在下方入口表中找名称，打开固定版本的上游链接。
- 查 references、assets、许可证等配套文件：在 JSON 的 `files` 中按 `local_path` 查找。当前 408 个受维护文件均有记录；原材料与派生方法保持独立来源身份。
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

## 当前清点范围

| 来源 | 全部文件 | 活跃技能 | 专家原文 | 流程原文 | 与上游相同 | 与上游有差异 |
|---|---:|---:|---:|---:|---:|---:|
| superseo | 125 | 11 | 0 | 0 | 87 | 38 |
| claude-seo | 141 | 20 | 0 | 0 | 71 | 70 |
| seomachine | 93 | 24 | 11 | 24 | 64 | 29 |
| workbench | 49 | 5 | 0 | 0 | 不适用 | 不适用 |
| 合计 | **408** | **60** | **11** | **24** | **222** | **137** |

原有 364 个文件的来源 ID 全部保留。新增组合入口和适配参考分别登记为 Workbench 文件，并通过 composed_from 或 derived_from 关联原记录；历史专家与流程原文保留在 third_party/skill-history。

JSON 覆盖 skills/ 和 third_party/skill-history/ 的受维护文件，不含系统文件或店铺私有技能。指纹包括换行、路径和适配差异；different 只表示内容不同，不能全部解释为上游升级。

当前上游而本地尚无对应入口的技能：Claude SEO 的 `skills/seo-agentic/SKILL.md`。`seo-content-brief` 的旧页保留／加强／新增及业务相关性方法已归入现有 content-brief 的参考，来源单独登记；未新增竞争入口。JSON 的 `upstream_skill_entrypoints_not_mapped` 保留尚未归入的方法路径。

## 文件清单字段

| 字段 | 含义与更新方式 |
|---|---|
| `id` | 稳定记录 ID：来源 ID 加上游路径；原生文件使用首次登记路径。迁移本地目录时保留 ID |
| `local_path` / `path_history` | 当前路径和历次登记路径；移动时追加旧路径，保留一个当前文件 |
| `kind` / `capability` / `current_owner_path` | 文件类型、现有能力标签、当前唯一 SKILL.md 入口；独立专家和流程材料没有主入口时为 null。合并归属见迁移表 |
| `source_id` / `upstream_path` | 对应来源及其固定版本中的原文件位置；可与来源表拼接为 blob URL |
| `baseline_status` / `imported_upstream_commit` | 区分原生文件和未知原始导入基线；只有找到明确证据才能补原始版本 |
| `local_sha256` / `local_git_blob_sha` | 本次本地内容指纹；前者便于文件核对，后者便于与 GitHub 树比较 |
| `comparison_upstream_blob_sha` / `comparison_status` | 固定上游的文件指纹与相同／不同状态；原生文件使用 workbench_native |
| `first_local_record` / `last_local_change` | 保留首次来源记录，并结合 path_history 刷新最新已提交变更的 commit、日期、标题和当时路径 |
| `content_changed_since_first_local_record` | 当前内容与首次已提交内容是否不同；恢复首次内容后回到 false。null 表示尚无已提交基线；false 不代表导入时未经适配 |
| `workingtree_modified` | 当前文件内容是否不同于清点时 HEAD 中该路径的内容；未提交新增文件为 true，与最近已提交历史分开记录 |
| `semantic_review` | 原材料保留 not_assessed_by_inventory；新入口记录本轮范围路由适配。内容指纹不代替方法质量审阅 |
| `original_kind` / `composed_from` | 原文件迁移前的类型，以及新组合入口引用的原记录 ID；保留正文的来源记录不被新入口覆盖 |
| `derived_from` / `adapted_by` | Workbench 适配参考与保留原文之间的双向来源关联；专业方法整理的逐项决定见 skill-method-adaptations.json |
| `maintenance_status` | active 表示当前技能材料，historical_source 表示供来源比对的原文；两者分开检查运行引用 |
| `declared_attribution` | 文件头已有的更细来源、许可证与同步日期，保留原声明的证据类型 |

新增组合入口的 first/last record 以 introduced_in_current_change 标记，commit 为 null；可用新路径的 Git 历史追溯引入提交，后续刷新时补入实际 SHA。

来源级 `comparison_ref`、`tree_sha`、`reviewed_on`、许可证位置由所有文件共享。`local_snapshot_commit` 记录清点前的本地 HEAD，清点结果及文档本身由此次 docs commit 留痕。

## 引用关系与适配线索

当前登记 776 处字面路径引用：Markdown 链接目标，以及指定前缀的无空白反引号路径。每条保存来源文件、行号、原始目标、解析位置和状态。它用于后续修复定位，不执行其中的命令。

| 状态 | 解释 |
|---|---|
| resolved_local | 按记录的路径解析规则在本地存在 |
| missing_literal_target | 字面目标在本地不存在；需结合上下文判断是否是原仓库布局、示例或实际缺件 |
| upstream_runtime_reference | 指向原插件根目录、原脚本或 `.claude` 环境，本地没有相应路径 |
| project_context_reference | 当前项目的 context、strategy、audits 等动态资料引用，不能按仓库根目录的存在性判断 |
| template_reference | 含占位符或通配符，需要具体任务参数 |
| route_or_example | 以 `/` 开头的站内路由或示例，未当作磁盘路径 |

完整数量保存在 JSON 的 `summary.dependencies_by_status`。第 5 步已将活跃技能里的失效工具指南、旧脚本和来源布局引用适配为本地方法；历史原文保持原样。使用 `check --strict-active` 检查活跃材料，历史原文中的旧环境引用留作来源证据。

扫描器检查字面 Markdown／行内路径，并补查脚本、代理和模板文件引用，包括 fenced 命令中的路径；不解析完整 Markdown AST 或任意 shell。运行指令的可用性另经正文审阅、本地 CLI help 核对和按需调用抽样。FLOW 许可声明及固定上游来源保留；本地 lock 记录适配后的文件指纹。

已知本地适配线索可从以下位置恢复：

- 核心 SuperSEO 方法：当前 reader-experience-review 接入、事实依据、非机械字数／密度规则；参见[复审报告](20261029-local-skills-review.md)。
- Claude SEO 核心入口：技术采集、证据资格、字段性能数据与当前结构化数据规则；结合 AGENTS 和对应文件的本地 Git 差异阅读。
- Workbench 原生方法：project-context、headless-precheck、reader-experience-review 没有对应的外部上游正文。
- 每文件的实际本地变更可由 JSON 的 commit 指针恢复，不把“与上游不同”统一归类为本地补丁。

本轮按条目吸收和未采用的决定见 [skill-upstream-adoptions.json](skill-upstream-adoptions.json) 与[实施记录](20261029-skill-writing-upstream-adaptation.md)。每项保留固定 SHA、实际读取的上游文件 blob、落点与本地适配，不把单项采用视为整包升级。

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
    ['git', 'ls-files', '-z', 'skills', 'third_party/skill-history']).decode().split('\0')))
recorded = {row['local_path'] for row in inventory['files']}
assert len(recorded) == len(inventory['files']), 'duplicate local paths'
assert recorded == tracked, 'tracked file coverage changed'
for row in inventory['files']:
    digest = hashlib.sha256(Path(row['local_path']).read_bytes()).hexdigest()
    assert digest == row['local_sha256'], row['local_path']
print(f'{len(recorded)} files: coverage and SHA-256 verified')
PY
```

以下表覆盖 60 个当前入口、11 份专家方法、24 份流程文档和六份历史合并入口及一份新增 brief 适配参考。原始路径与当前路径也可在 skill-layout-migration.json 中交叉查询；其余配套文件逐项见 JSON。

## 本地清单维护

在仓库根目录使用项目 venv：

```bash
.venv/bin/python scripts/skill_inventory.py refresh
.venv/bin/python scripts/skill_inventory.py check
```

refresh 更新当前指纹、字面引用、汇总和下方表格，保留原始来源 ID 与上游版本。来自 skill-method-adaptations.json 的派生参考会按明确关系登记；其他新增 Workbench 文件须显式提供 `--register-workbench` 路径。未登记、缺失或被忽略的材料会使操作失败。

check 不写文件。运行引用修复后，可用 `check --strict-active` 检查当前技能中的缺失路径与不可用运行依赖；历史原文仍保留当时环境，不被当作当前执行契约。

## 入口与上游文件映射

### superseo / skill（11）

| 当前文件 | 固定版本中的上游路径／派生来源 | 内容比对 | 本地首次记录 |
|---|---|---|---|
| [skills/content-brief/SKILL.md](../skills/content-brief/SKILL.md) | [skills/content-brief/SKILL.md](https://github.com/inhouseseo/superseo-skills/blob/9cf22cc065a294bf0077ea6af6b4ea0eb7f89cdc/skills/content-brief/SKILL.md) | 有差异 | `05a9340` |
| [skills/eeat-audit/SKILL.md](../skills/eeat-audit/SKILL.md) | [skills/eeat-audit/SKILL.md](https://github.com/inhouseseo/superseo-skills/blob/9cf22cc065a294bf0077ea6af6b4ea0eb7f89cdc/skills/eeat-audit/SKILL.md) | 有差异 | `45c60ef` |
| [skills/expert-interview/SKILL.md](../skills/expert-interview/SKILL.md) | [skills/expert-interview/SKILL.md](https://github.com/inhouseseo/superseo-skills/blob/9cf22cc065a294bf0077ea6af6b4ea0eb7f89cdc/skills/expert-interview/SKILL.md) | 有差异 | `f0116d2` |
| [skills/featured-snippet-optimizer/SKILL.md](../skills/featured-snippet-optimizer/SKILL.md) | [skills/featured-snippet-optimizer/SKILL.md](https://github.com/inhouseseo/superseo-skills/blob/9cf22cc065a294bf0077ea6af6b4ea0eb7f89cdc/skills/featured-snippet-optimizer/SKILL.md) | 有差异 | `f0116d2` |
| [skills/improve-content/SKILL.md](../skills/improve-content/SKILL.md) | [skills/improve-content/SKILL.md](https://github.com/inhouseseo/superseo-skills/blob/9cf22cc065a294bf0077ea6af6b4ea0eb7f89cdc/skills/improve-content/SKILL.md) | 有差异 | `f0116d2` |
| [skills/keyword-deep-dive/SKILL.md](../skills/keyword-deep-dive/SKILL.md) | [skills/keyword-deep-dive/SKILL.md](https://github.com/inhouseseo/superseo-skills/blob/9cf22cc065a294bf0077ea6af6b4ea0eb7f89cdc/skills/keyword-deep-dive/SKILL.md) | 有差异 | `05a9340` |
| [skills/linkbuilding/SKILL.md](../skills/linkbuilding/SKILL.md) | [skills/linkbuilding/SKILL.md](https://github.com/inhouseseo/superseo-skills/blob/9cf22cc065a294bf0077ea6af6b4ea0eb7f89cdc/skills/linkbuilding/SKILL.md) | 有差异 | `45c60ef` |
| [skills/page-audit/SKILL.md](../skills/page-audit/SKILL.md) | [skills/page-audit/SKILL.md](https://github.com/inhouseseo/superseo-skills/blob/9cf22cc065a294bf0077ea6af6b4ea0eb7f89cdc/skills/page-audit/SKILL.md) | 有差异 | `d08f066` |
| [skills/semantic-gap-analysis/SKILL.md](../skills/semantic-gap-analysis/SKILL.md) | [skills/semantic-gap-analysis/SKILL.md](https://github.com/inhouseseo/superseo-skills/blob/9cf22cc065a294bf0077ea6af6b4ea0eb7f89cdc/skills/semantic-gap-analysis/SKILL.md) | 有差异 | `45c60ef` |
| [skills/topic-cluster-planning/SKILL.md](../skills/topic-cluster-planning/SKILL.md) | [skills/topic-cluster-planning/SKILL.md](https://github.com/inhouseseo/superseo-skills/blob/9cf22cc065a294bf0077ea6af6b4ea0eb7f89cdc/skills/topic-cluster-planning/SKILL.md) | 有差异 | `45c60ef` |
| [skills/write-content/SKILL.md](../skills/write-content/SKILL.md) | [skills/write-content/SKILL.md](https://github.com/inhouseseo/superseo-skills/blob/9cf22cc065a294bf0077ea6af6b4ea0eb7f89cdc/skills/write-content/SKILL.md) | 有差异 | `d08f066` |

### claude-seo / skill（20）

| 当前文件 | 固定版本中的上游路径／派生来源 | 内容比对 | 本地首次记录 |
|---|---|---|---|
| [skills/backlinks/SKILL.md](../skills/backlinks/SKILL.md) | [skills/seo-backlinks/SKILL.md](https://github.com/AgriciDaniel/claude-seo/blob/6be93f45064ffbadced572b5d5c95f55fd263af0/skills/seo-backlinks/SKILL.md) | 有差异 | `45c60ef` |
| [skills/drift/SKILL.md](../skills/drift/SKILL.md) | [skills/seo-drift/SKILL.md](https://github.com/AgriciDaniel/claude-seo/blob/6be93f45064ffbadced572b5d5c95f55fd263af0/skills/seo-drift/SKILL.md) | 有差异 | `45c60ef` |
| [skills/images/SKILL.md](../skills/images/SKILL.md) | [skills/seo-images/SKILL.md](https://github.com/AgriciDaniel/claude-seo/blob/6be93f45064ffbadced572b5d5c95f55fd263af0/skills/seo-images/SKILL.md) | 有差异 | `45c60ef` |
| [skills/schema/SKILL.md](../skills/schema/SKILL.md) | [skills/seo-schema/SKILL.md](https://github.com/AgriciDaniel/claude-seo/blob/6be93f45064ffbadced572b5d5c95f55fd263af0/skills/seo-schema/SKILL.md) | 有差异 | `d08f066` |
| [skills/seo-cluster/SKILL.md](../skills/seo-cluster/SKILL.md) | [skills/seo-cluster/SKILL.md](https://github.com/AgriciDaniel/claude-seo/blob/6be93f45064ffbadced572b5d5c95f55fd263af0/skills/seo-cluster/SKILL.md) | 有差异 | `f0116d2` |
| [skills/seo-competitor-pages/SKILL.md](../skills/seo-competitor-pages/SKILL.md) | [skills/seo-competitor-pages/SKILL.md](https://github.com/AgriciDaniel/claude-seo/blob/6be93f45064ffbadced572b5d5c95f55fd263af0/skills/seo-competitor-pages/SKILL.md) | 有差异 | `f0116d2` |
| [skills/seo-content/SKILL.md](../skills/seo-content/SKILL.md) | [skills/seo-content/SKILL.md](https://github.com/AgriciDaniel/claude-seo/blob/6be93f45064ffbadced572b5d5c95f55fd263af0/skills/seo-content/SKILL.md) | 有差异 | `f0116d2` |
| [skills/seo-dataforseo/SKILL.md](../skills/seo-dataforseo/SKILL.md) | [skills/seo-dataforseo/SKILL.md](https://github.com/AgriciDaniel/claude-seo/blob/6be93f45064ffbadced572b5d5c95f55fd263af0/skills/seo-dataforseo/SKILL.md) | 有差异 | `f0116d2` |
| [skills/seo-ecommerce/SKILL.md](../skills/seo-ecommerce/SKILL.md) | [skills/seo-ecommerce/SKILL.md](https://github.com/AgriciDaniel/claude-seo/blob/6be93f45064ffbadced572b5d5c95f55fd263af0/skills/seo-ecommerce/SKILL.md) | 有差异 | `f0116d2` |
| [skills/seo-flow/SKILL.md](../skills/seo-flow/SKILL.md) | [skills/seo-flow/SKILL.md](https://github.com/AgriciDaniel/claude-seo/blob/6be93f45064ffbadced572b5d5c95f55fd263af0/skills/seo-flow/SKILL.md) | 有差异 | `f0116d2` |
| [skills/seo-geo/SKILL.md](../skills/seo-geo/SKILL.md) | [skills/seo-geo/SKILL.md](https://github.com/AgriciDaniel/claude-seo/blob/6be93f45064ffbadced572b5d5c95f55fd263af0/skills/seo-geo/SKILL.md) | 有差异 | `f0116d2` |
| [skills/seo-google/SKILL.md](../skills/seo-google/SKILL.md) | [skills/seo-google/SKILL.md](https://github.com/AgriciDaniel/claude-seo/blob/6be93f45064ffbadced572b5d5c95f55fd263af0/skills/seo-google/SKILL.md) | 有差异 | `f0116d2` |
| [skills/seo-hreflang/SKILL.md](../skills/seo-hreflang/SKILL.md) | [skills/seo-hreflang/SKILL.md](https://github.com/AgriciDaniel/claude-seo/blob/6be93f45064ffbadced572b5d5c95f55fd263af0/skills/seo-hreflang/SKILL.md) | 有差异 | `f0116d2` |
| [skills/seo-image-gen/SKILL.md](../skills/seo-image-gen/SKILL.md) | [skills/seo-image-gen/SKILL.md](https://github.com/AgriciDaniel/claude-seo/blob/6be93f45064ffbadced572b5d5c95f55fd263af0/skills/seo-image-gen/SKILL.md) | 有差异 | `f0116d2` |
| [skills/seo-local/SKILL.md](../skills/seo-local/SKILL.md) | [skills/seo-local/SKILL.md](https://github.com/AgriciDaniel/claude-seo/blob/6be93f45064ffbadced572b5d5c95f55fd263af0/skills/seo-local/SKILL.md) | 有差异 | `f0116d2` |
| [skills/seo-maps/SKILL.md](../skills/seo-maps/SKILL.md) | [skills/seo-maps/SKILL.md](https://github.com/AgriciDaniel/claude-seo/blob/6be93f45064ffbadced572b5d5c95f55fd263af0/skills/seo-maps/SKILL.md) | 有差异 | `f0116d2` |
| [skills/seo-plan/SKILL.md](../skills/seo-plan/SKILL.md) | [skills/seo-plan/SKILL.md](https://github.com/AgriciDaniel/claude-seo/blob/6be93f45064ffbadced572b5d5c95f55fd263af0/skills/seo-plan/SKILL.md) | 有差异 | `f0116d2` |
| [skills/seo-sxo/SKILL.md](../skills/seo-sxo/SKILL.md) | [skills/seo-sxo/SKILL.md](https://github.com/AgriciDaniel/claude-seo/blob/6be93f45064ffbadced572b5d5c95f55fd263af0/skills/seo-sxo/SKILL.md) | 有差异 | `f0116d2` |
| [skills/sitemap/SKILL.md](../skills/sitemap/SKILL.md) | [skills/seo-sitemap/SKILL.md](https://github.com/AgriciDaniel/claude-seo/blob/6be93f45064ffbadced572b5d5c95f55fd263af0/skills/seo-sitemap/SKILL.md) | 有差异 | `45c60ef` |
| [skills/technical-audit/SKILL.md](../skills/technical-audit/SKILL.md) | [skills/seo-technical/SKILL.md](https://github.com/AgriciDaniel/claude-seo/blob/6be93f45064ffbadced572b5d5c95f55fd263af0/skills/seo-technical/SKILL.md) | 有差异 | `05a9340` |

### seomachine / skill（24）

| 当前文件 | 固定版本中的上游路径／派生来源 | 内容比对 | 本地首次记录 |
|---|---|---|---|
| [skills/ab-test-setup/SKILL.md](../skills/ab-test-setup/SKILL.md) | [.claude/skills/ab-test-setup/SKILL.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/skills/ab-test-setup/SKILL.md) | 有差异 | `f0116d2` |
| [skills/analytics-tracking/SKILL.md](../skills/analytics-tracking/SKILL.md) | [.claude/skills/analytics-tracking/SKILL.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/skills/analytics-tracking/SKILL.md) | 有差异 | `f0116d2` |
| [skills/competitor-alternatives/SKILL.md](../skills/competitor-alternatives/SKILL.md) | [.claude/skills/competitor-alternatives/SKILL.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/skills/competitor-alternatives/SKILL.md) | 有差异 | `f0116d2` |
| [skills/content-strategy/SKILL.md](../skills/content-strategy/SKILL.md) | [.claude/skills/content-strategy/SKILL.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/skills/content-strategy/SKILL.md) | 有差异 | `f0116d2` |
| [skills/copy-editing/SKILL.md](../skills/copy-editing/SKILL.md) | [.claude/skills/copy-editing/SKILL.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/skills/copy-editing/SKILL.md) | 有差异 | `f0116d2` |
| [skills/copywriting/SKILL.md](../skills/copywriting/SKILL.md) | [.claude/skills/copywriting/SKILL.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/skills/copywriting/SKILL.md) | 有差异 | `f0116d2` |
| [skills/email-sequence/SKILL.md](../skills/email-sequence/SKILL.md) | [.claude/skills/email-sequence/SKILL.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/skills/email-sequence/SKILL.md) | 有差异 | `f0116d2` |
| [skills/form-cro/SKILL.md](../skills/form-cro/SKILL.md) | [.claude/skills/form-cro/SKILL.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/skills/form-cro/SKILL.md) | 有差异 | `f0116d2` |
| [skills/free-tool-strategy/SKILL.md](../skills/free-tool-strategy/SKILL.md) | [.claude/skills/free-tool-strategy/SKILL.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/skills/free-tool-strategy/SKILL.md) | 有差异 | `f0116d2` |
| [skills/growth-lead/SKILL.md](../skills/growth-lead/SKILL.md) | [.claude/skills/growth-lead/SKILL.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/skills/growth-lead/SKILL.md) | 相同 | `f0116d2` |
| [skills/launch-strategy/SKILL.md](../skills/launch-strategy/SKILL.md) | [.claude/skills/launch-strategy/SKILL.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/skills/launch-strategy/SKILL.md) | 有差异 | `f0116d2` |
| [skills/marketing-ideas/SKILL.md](../skills/marketing-ideas/SKILL.md) | [.claude/skills/marketing-ideas/SKILL.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/skills/marketing-ideas/SKILL.md) | 有差异 | `f0116d2` |
| [skills/marketing-psychology/SKILL.md](../skills/marketing-psychology/SKILL.md) | [.claude/skills/marketing-psychology/SKILL.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/skills/marketing-psychology/SKILL.md) | 有差异 | `f0116d2` |
| [skills/onboarding-cro/SKILL.md](../skills/onboarding-cro/SKILL.md) | [.claude/skills/onboarding-cro/SKILL.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/skills/onboarding-cro/SKILL.md) | 有差异 | `f0116d2` |
| [skills/page-cro/SKILL.md](../skills/page-cro/SKILL.md) | [.claude/skills/page-cro/SKILL.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/skills/page-cro/SKILL.md) | 有差异 | `f0116d2` |
| [skills/paid-ads/SKILL.md](../skills/paid-ads/SKILL.md) | [.claude/skills/paid-ads/SKILL.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/skills/paid-ads/SKILL.md) | 有差异 | `f0116d2` |
| [skills/paywall-upgrade-cro/SKILL.md](../skills/paywall-upgrade-cro/SKILL.md) | [.claude/skills/paywall-upgrade-cro/SKILL.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/skills/paywall-upgrade-cro/SKILL.md) | 有差异 | `f0116d2` |
| [skills/popup-cro/SKILL.md](../skills/popup-cro/SKILL.md) | [.claude/skills/popup-cro/SKILL.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/skills/popup-cro/SKILL.md) | 有差异 | `f0116d2` |
| [skills/pricing-strategy/SKILL.md](../skills/pricing-strategy/SKILL.md) | [.claude/skills/pricing-strategy/SKILL.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/skills/pricing-strategy/SKILL.md) | 有差异 | `f0116d2` |
| [skills/product-marketing-context/SKILL.md](../skills/product-marketing-context/SKILL.md) | [.claude/skills/product-marketing-context/SKILL.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/skills/product-marketing-context/SKILL.md) | 有差异 | `f0116d2` |
| [skills/programmatic-seo/SKILL.md](../skills/programmatic-seo/SKILL.md) | [.claude/skills/programmatic-seo/SKILL.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/skills/programmatic-seo/SKILL.md) | 有差异 | `f0116d2` |
| [skills/referral-program/SKILL.md](../skills/referral-program/SKILL.md) | [.claude/skills/referral-program/SKILL.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/skills/referral-program/SKILL.md) | 有差异 | `f0116d2` |
| [skills/signup-flow-cro/SKILL.md](../skills/signup-flow-cro/SKILL.md) | [.claude/skills/signup-flow-cro/SKILL.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/skills/signup-flow-cro/SKILL.md) | 有差异 | `f0116d2` |
| [skills/social-content/SKILL.md](../skills/social-content/SKILL.md) | [.claude/skills/social-content/SKILL.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/skills/social-content/SKILL.md) | 有差异 | `f0116d2` |

### workbench / skill（5）

| 当前文件 | 固定版本中的上游路径／派生来源 | 内容比对 | 本地首次记录 |
|---|---|---|---|
| [skills/headless-precheck/SKILL.md](../skills/headless-precheck/SKILL.md) | Workbench 本地方法 | 本地方法 | `45c60ef` |
| [skills/project-context/SKILL.md](../skills/project-context/SKILL.md) | Workbench 本地方法 | 本地方法 | `4146d19` |
| [skills/reader-experience-review/SKILL.md](../skills/reader-experience-review/SKILL.md) | Workbench 本地方法 | 本地方法 | `aff4dea` |
| [skills/seo/SKILL.md](../skills/seo/SKILL.md) | claude-seo:skills/seo/SKILL.md | 本地方法 | `75eab47` |
| [skills/site-audit/SKILL.md](../skills/site-audit/SKILL.md) | claude-seo:skills/seo-audit/SKILL.md；seomachine:.claude/skills/seo-audit/SKILL.md | 本地方法 | `75eab47` |

### seomachine / specialist_reference（11）

| 当前文件 | 固定版本中的上游路径／派生来源 | 内容比对 | 本地首次记录 |
|---|---|---|---|
| [third_party/skill-history/seomachine/agents/cluster-strategist.md](../third_party/skill-history/seomachine/agents/cluster-strategist.md) | [.claude/agents/cluster-strategist.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/agents/cluster-strategist.md) | 相同 | `f0116d2` |
| [third_party/skill-history/seomachine/agents/content-analyzer.md](../third_party/skill-history/seomachine/agents/content-analyzer.md) | [.claude/agents/content-analyzer.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/agents/content-analyzer.md) | 相同 | `f0116d2` |
| [third_party/skill-history/seomachine/agents/cro-analyst.md](../third_party/skill-history/seomachine/agents/cro-analyst.md) | [.claude/agents/cro-analyst.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/agents/cro-analyst.md) | 相同 | `f0116d2` |
| [third_party/skill-history/seomachine/agents/editor.md](../third_party/skill-history/seomachine/agents/editor.md) | [.claude/agents/editor.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/agents/editor.md) | 相同 | `f0116d2` |
| [third_party/skill-history/seomachine/agents/headline-generator.md](../third_party/skill-history/seomachine/agents/headline-generator.md) | [.claude/agents/headline-generator.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/agents/headline-generator.md) | 相同 | `f0116d2` |
| [third_party/skill-history/seomachine/agents/internal-linker.md](../third_party/skill-history/seomachine/agents/internal-linker.md) | [.claude/agents/internal-linker.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/agents/internal-linker.md) | 相同 | `f0116d2` |
| [third_party/skill-history/seomachine/agents/keyword-mapper.md](../third_party/skill-history/seomachine/agents/keyword-mapper.md) | [.claude/agents/keyword-mapper.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/agents/keyword-mapper.md) | 相同 | `f0116d2` |
| [third_party/skill-history/seomachine/agents/landing-page-optimizer.md](../third_party/skill-history/seomachine/agents/landing-page-optimizer.md) | [.claude/agents/landing-page-optimizer.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/agents/landing-page-optimizer.md) | 相同 | `f0116d2` |
| [third_party/skill-history/seomachine/agents/meta-creator.md](../third_party/skill-history/seomachine/agents/meta-creator.md) | [.claude/agents/meta-creator.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/agents/meta-creator.md) | 相同 | `f0116d2` |
| [third_party/skill-history/seomachine/agents/performance.md](../third_party/skill-history/seomachine/agents/performance.md) | [.claude/agents/performance.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/agents/performance.md) | 相同 | `f0116d2` |
| [third_party/skill-history/seomachine/agents/seo-optimizer.md](../third_party/skill-history/seomachine/agents/seo-optimizer.md) | [.claude/agents/seo-optimizer.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/agents/seo-optimizer.md) | 相同 | `f0116d2` |

### seomachine / workflow_reference（24）

| 当前文件 | 固定版本中的上游路径／派生来源 | 内容比对 | 本地首次记录 |
|---|---|---|---|
| [third_party/skill-history/seomachine/commands/analyze-existing.md](../third_party/skill-history/seomachine/commands/analyze-existing.md) | [.claude/commands/analyze-existing.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/commands/analyze-existing.md) | 相同 | `f0116d2` |
| [third_party/skill-history/seomachine/commands/article.md](../third_party/skill-history/seomachine/commands/article.md) | [.claude/commands/article.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/commands/article.md) | 相同 | `f0116d2` |
| [third_party/skill-history/seomachine/commands/cluster.md](../third_party/skill-history/seomachine/commands/cluster.md) | [.claude/commands/cluster.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/commands/cluster.md) | 相同 | `f0116d2` |
| [third_party/skill-history/seomachine/commands/content-calendar.md](../third_party/skill-history/seomachine/commands/content-calendar.md) | [.claude/commands/content-calendar.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/commands/content-calendar.md) | 相同 | `f0116d2` |
| [third_party/skill-history/seomachine/commands/landing-audit.md](../third_party/skill-history/seomachine/commands/landing-audit.md) | [.claude/commands/landing-audit.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/commands/landing-audit.md) | 相同 | `f0116d2` |
| [third_party/skill-history/seomachine/commands/landing-competitor.md](../third_party/skill-history/seomachine/commands/landing-competitor.md) | [.claude/commands/landing-competitor.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/commands/landing-competitor.md) | 相同 | `f0116d2` |
| [third_party/skill-history/seomachine/commands/landing-publish.md](../third_party/skill-history/seomachine/commands/landing-publish.md) | [.claude/commands/landing-publish.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/commands/landing-publish.md) | 相同 | `f0116d2` |
| [third_party/skill-history/seomachine/commands/landing-research.md](../third_party/skill-history/seomachine/commands/landing-research.md) | [.claude/commands/landing-research.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/commands/landing-research.md) | 相同 | `f0116d2` |
| [third_party/skill-history/seomachine/commands/landing-write.md](../third_party/skill-history/seomachine/commands/landing-write.md) | [.claude/commands/landing-write.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/commands/landing-write.md) | 相同 | `f0116d2` |
| [third_party/skill-history/seomachine/commands/optimize.md](../third_party/skill-history/seomachine/commands/optimize.md) | [.claude/commands/optimize.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/commands/optimize.md) | 相同 | `f0116d2` |
| [third_party/skill-history/seomachine/commands/performance-review.md](../third_party/skill-history/seomachine/commands/performance-review.md) | [.claude/commands/performance-review.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/commands/performance-review.md) | 相同 | `f0116d2` |
| [third_party/skill-history/seomachine/commands/priorities.md](../third_party/skill-history/seomachine/commands/priorities.md) | [.claude/commands/priorities.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/commands/priorities.md) | 相同 | `f0116d2` |
| [third_party/skill-history/seomachine/commands/publish-draft.md](../third_party/skill-history/seomachine/commands/publish-draft.md) | [.claude/commands/publish-draft.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/commands/publish-draft.md) | 相同 | `f0116d2` |
| [third_party/skill-history/seomachine/commands/repurpose.md](../third_party/skill-history/seomachine/commands/repurpose.md) | [.claude/commands/repurpose.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/commands/repurpose.md) | 有差异 | `f0116d2` |
| [third_party/skill-history/seomachine/commands/research-ai-citations.md](../third_party/skill-history/seomachine/commands/research-ai-citations.md) | [.claude/commands/research-ai-citations.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/commands/research-ai-citations.md) | 相同 | `f0116d2` |
| [third_party/skill-history/seomachine/commands/research-gaps.md](../third_party/skill-history/seomachine/commands/research-gaps.md) | [.claude/commands/research-gaps.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/commands/research-gaps.md) | 相同 | `f0116d2` |
| [third_party/skill-history/seomachine/commands/research-performance.md](../third_party/skill-history/seomachine/commands/research-performance.md) | [.claude/commands/research-performance.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/commands/research-performance.md) | 相同 | `f0116d2` |
| [third_party/skill-history/seomachine/commands/research-serp.md](../third_party/skill-history/seomachine/commands/research-serp.md) | [.claude/commands/research-serp.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/commands/research-serp.md) | 相同 | `f0116d2` |
| [third_party/skill-history/seomachine/commands/research-topics.md](../third_party/skill-history/seomachine/commands/research-topics.md) | [.claude/commands/research-topics.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/commands/research-topics.md) | 相同 | `f0116d2` |
| [third_party/skill-history/seomachine/commands/research-trending.md](../third_party/skill-history/seomachine/commands/research-trending.md) | [.claude/commands/research-trending.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/commands/research-trending.md) | 相同 | `f0116d2` |
| [third_party/skill-history/seomachine/commands/research.md](../third_party/skill-history/seomachine/commands/research.md) | [.claude/commands/research.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/commands/research.md) | 相同 | `f0116d2` |
| [third_party/skill-history/seomachine/commands/rewrite.md](../third_party/skill-history/seomachine/commands/rewrite.md) | [.claude/commands/rewrite.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/commands/rewrite.md) | 相同 | `f0116d2` |
| [third_party/skill-history/seomachine/commands/scrub.md](../third_party/skill-history/seomachine/commands/scrub.md) | [.claude/commands/scrub.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/commands/scrub.md) | 相同 | `f0116d2` |
| [third_party/skill-history/seomachine/commands/write.md](../third_party/skill-history/seomachine/commands/write.md) | [.claude/commands/write.md](https://github.com/TheCraigHewitt/seomachine/blob/120e7b46dc07c98382cd4f68ac5b6515ab9f2604/.claude/commands/write.md) | 相同 | `f0116d2` |

### workbench / reference（41）

| 当前文件 | 固定版本中的上游路径／派生来源 | 内容比对 | 本地首次记录 |
|---|---|---|---|
| [skills/analytics-tracking/references/provider-inputs.md](../skills/analytics-tracking/references/provider-inputs.md) | Workbench 本地方法 | 本地方法 | `b4c5142` |
| [skills/content-strategy/references/calendar-planning.md](../skills/content-strategy/references/calendar-planning.md) | seomachine:.claude/commands/content-calendar.md | 本地方法 | `08d0679` |
| [skills/content-strategy/references/topic-opportunities.md](../skills/content-strategy/references/topic-opportunities.md) | seomachine:.claude/commands/research-topics.md | 本地方法 | `08d0679` |
| [skills/content-strategy/references/trend-research.md](../skills/content-strategy/references/trend-research.md) | seomachine:.claude/commands/research-trending.md | 本地方法 | `08d0679` |
| [skills/content-strategy/references/work-priorities.md](../skills/content-strategy/references/work-priorities.md) | seomachine:.claude/commands/priorities.md | 本地方法 | `08d0679` |
| [skills/copy-editing/references/article-editing.md](../skills/copy-editing/references/article-editing.md) | seomachine:.claude/agents/editor.md | 本地方法 | `08d0679` |
| [skills/copywriting/references/headline-options.md](../skills/copywriting/references/headline-options.md) | seomachine:.claude/agents/headline-generator.md | 本地方法 | `08d0679` |
| [skills/copywriting/references/landing-page-draft.md](../skills/copywriting/references/landing-page-draft.md) | seomachine:.claude/commands/landing-write.md | 本地方法 | `08d0679` |
| [skills/copywriting/references/landing-page-handoff.md](../skills/copywriting/references/landing-page-handoff.md) | seomachine:.claude/commands/landing-publish.md | 本地方法 | `08d0679` |
| [skills/drift/references/content-performance-review.md](../skills/drift/references/content-performance-review.md) | seomachine:.claude/agents/performance.md | 本地方法 | `08d0679` |
| [skills/drift/references/content-performance-workflow.md](../skills/drift/references/content-performance-workflow.md) | seomachine:.claude/commands/performance-review.md | 本地方法 | `08d0679` |
| [skills/drift/references/performance-priorities.md](../skills/drift/references/performance-priorities.md) | seomachine:.claude/commands/research-performance.md | 本地方法 | `08d0679` |
| [skills/email-sequence/references/provider-inputs.md](../skills/email-sequence/references/provider-inputs.md) | Workbench 本地方法 | 本地方法 | `b4c5142` |
| [skills/improve-content/references/optimization-workflow.md](../skills/improve-content/references/optimization-workflow.md) | seomachine:.claude/commands/optimize.md | 本地方法 | `08d0679` |
| [skills/improve-content/references/refresh-workflow.md](../skills/improve-content/references/refresh-workflow.md) | seomachine:.claude/commands/rewrite.md | 本地方法 | `08d0679` |
| [skills/improve-content/references/seo-editing.md](../skills/improve-content/references/seo-editing.md) | seomachine:.claude/agents/seo-optimizer.md | 本地方法 | `08d0679` |
| [skills/keyword-deep-dive/references/keyword-placement-review.md](../skills/keyword-deep-dive/references/keyword-placement-review.md) | seomachine:.claude/agents/keyword-mapper.md | 本地方法 | `08d0679` |
| [skills/keyword-deep-dive/references/research-workflow.md](../skills/keyword-deep-dive/references/research-workflow.md) | seomachine:.claude/commands/research.md | 本地方法 | `08d0679` |
| [skills/keyword-deep-dive/references/serp-review.md](../skills/keyword-deep-dive/references/serp-review.md) | seomachine:.claude/commands/research-serp.md | 本地方法 | `08d0679` |
| [skills/page-audit/references/content-assessment.md](../skills/page-audit/references/content-assessment.md) | seomachine:.claude/agents/content-analyzer.md | 本地方法 | `08d0679` |
| [skills/page-audit/references/existing-page-review.md](../skills/page-audit/references/existing-page-review.md) | seomachine:.claude/commands/analyze-existing.md | 本地方法 | `08d0679` |
| [skills/page-audit/references/metadata-writing.md](../skills/page-audit/references/metadata-writing.md) | seomachine:.claude/agents/meta-creator.md | 本地方法 | `08d0679` |
| [skills/page-cro/references/conversion-analysis.md](../skills/page-cro/references/conversion-analysis.md) | seomachine:.claude/agents/cro-analyst.md | 本地方法 | `08d0679` |
| [skills/page-cro/references/landing-audit.md](../skills/page-cro/references/landing-audit.md) | seomachine:.claude/commands/landing-audit.md | 本地方法 | `08d0679` |
| [skills/page-cro/references/landing-competitor-review.md](../skills/page-cro/references/landing-competitor-review.md) | seomachine:.claude/commands/landing-competitor.md | 本地方法 | `08d0679` |
| [skills/page-cro/references/landing-page-review.md](../skills/page-cro/references/landing-page-review.md) | seomachine:.claude/agents/landing-page-optimizer.md | 本地方法 | `08d0679` |
| [skills/page-cro/references/landing-research.md](../skills/page-cro/references/landing-research.md) | seomachine:.claude/commands/landing-research.md | 本地方法 | `08d0679` |
| [skills/paid-ads/references/provider-inputs.md](../skills/paid-ads/references/provider-inputs.md) | Workbench 本地方法 | 本地方法 | `b4c5142` |
| [skills/reader-experience-review/references/calibration.md](../skills/reader-experience-review/references/calibration.md) | Workbench 本地方法 | 本地方法 | `aff4dea` |
| [skills/referral-program/references/provider-inputs.md](../skills/referral-program/references/provider-inputs.md) | Workbench 本地方法 | 本地方法 | `b4c5142` |
| [skills/schema/references/search-eligibility.md](../skills/schema/references/search-eligibility.md) | Workbench 本地方法 | 本地方法 | 本轮新增 |
| [skills/semantic-gap-analysis/references/research-gap-workflow.md](../skills/semantic-gap-analysis/references/research-gap-workflow.md) | seomachine:.claude/commands/research-gaps.md | 本地方法 | `08d0679` |
| [skills/seo-geo/references/citation-research.md](../skills/seo-geo/references/citation-research.md) | seomachine:.claude/commands/research-ai-citations.md | 本地方法 | `08d0679` |
| [skills/seo/references/workbench-operations.md](../skills/seo/references/workbench-operations.md) | Workbench 本地方法 | 本地方法 | `b4c5142` |
| [skills/social-content/references/content-repurposing.md](../skills/social-content/references/content-repurposing.md) | seomachine:.claude/commands/repurpose.md | 本地方法 | `08d0679` |
| [skills/topic-cluster-planning/references/cluster-review.md](../skills/topic-cluster-planning/references/cluster-review.md) | seomachine:.claude/agents/cluster-strategist.md | 本地方法 | `08d0679` |
| [skills/topic-cluster-planning/references/cluster-workflow.md](../skills/topic-cluster-planning/references/cluster-workflow.md) | seomachine:.claude/commands/cluster.md | 本地方法 | `08d0679` |
| [skills/topic-cluster-planning/references/internal-link-review.md](../skills/topic-cluster-planning/references/internal-link-review.md) | seomachine:.claude/agents/internal-linker.md | 本地方法 | `08d0679` |
| [skills/write-content/references/article-workflow.md](../skills/write-content/references/article-workflow.md) | seomachine:.claude/commands/article.md | 本地方法 | `08d0679` |
| [skills/write-content/references/draft-handoff.md](../skills/write-content/references/draft-handoff.md) | seomachine:.claude/commands/publish-draft.md | 本地方法 | `08d0679` |
| [skills/write-content/references/drafting-workflow.md](../skills/write-content/references/drafting-workflow.md) | seomachine:.claude/commands/write.md | 本地方法 | `08d0679` |

### 归入参考的来源方法

| 当前文件 | 来源 ID |
|---|---|
| [skills/content-brief/references/existing-page-scope.md](../skills/content-brief/references/existing-page-scope.md) | `claude-seo:skills/seo-content-brief/SKILL.md` |
| [skills/page-audit/references/claude-seo/single-page-checks.md](../skills/page-audit/references/claude-seo/single-page-checks.md) | `claude-seo:skills/seo-page/SKILL.md` |
| [skills/programmatic-seo/references/claude-seo/technical-planning.md](../skills/programmatic-seo/references/claude-seo/technical-planning.md) | `claude-seo:skills/seo-programmatic/SKILL.md` |
| [skills/schema/references/implementation/guide.md](../skills/schema/references/implementation/guide.md) | `seomachine:.claude/skills/schema-markup/SKILL.md` |
| [skills/seo/references/upstream-orchestration.md](../skills/seo/references/upstream-orchestration.md) | `claude-seo:skills/seo/SKILL.md` |
| [skills/site-audit/references/claude-seo-audit.md](../skills/site-audit/references/claude-seo-audit.md) | `claude-seo:skills/seo-audit/SKILL.md` |
| [skills/site-audit/references/seo-machine-audit.md](../skills/site-audit/references/seo-machine-audit.md) | `seomachine:.claude/skills/seo-audit/SKILL.md` |
