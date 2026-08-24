# Default Project Reports

项目级报告与决策记录统一存放在本目录，命名规范见仓库 `AGENTS.md`：

```
YYYYMMDD_<category>_<topic>.md
```

- 日期：`YYYYMMDD`（UTC，报告生成日）
- category：`tech` / `content` / `ops` / `decision` / `outcome`
- topic：短横线 slug，描述主题（如 `cable-hub-refresh`）

## 规则

- 报告必须包含：决策理由（rationale）、证据指针（evidence pointers，指向 `audits/` 下具体文件）、后续跟踪日期（follow-up dates）
- 内容草稿放 `content/drafts/`，报告只记录决策与理由，不承载草稿正文
- 每周工作记录统一遵循 `templates/weekly_work_done.md`（命名 `YYYY_week_WW_work_done.md`），分 `速览` / `实质工作` / `遗留工作` / `其他`（可选）四部分；`速览` 同时记录本周待完成与已确认遗留到下周的任务（完成打勾、未完成留空），`遗留工作` 只收本周内无法完成的任务（本周 to-do 不写入，下周开始时移入新周速览）
- 命名规范变更须同步更新仓库根目录 `AGENTS.md`，保证所有项目一致
