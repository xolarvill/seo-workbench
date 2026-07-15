# SEO Workbench

基于社区开源项目而创建的SEO工作流，覆盖全链路：初始审计 → 战略规划 → 内容生产 → 质量审查 → 技术审计 → 外链建设 → 持续监控。

---
Todo:
- [X] tech stack recognization: wappalyzergo integration
- [X] laboratory test: Lighthouse 本地多次采样与代表结果
- [ ] real UX: CrUX接入
- [X] 多店铺管理
- [X] 审计diff
- [ ] GSC接入
- [ ] cli improvement: 重写cli方式
- [ ] docs: readme重写
- [ ] 定时功能

---

## 快速开始

```bash
git clone https://github.com/xolarvill/seo-workbench.git
cd seo-workbench
./setup.sh
codex # 使用任意agent
```

`setup.sh` 是安装入口，不只是环境检查。它会安装或配置 Python 3.11、Go helper、Node 24 LTS、锁定版本的 Lighthouse 和浏览器运行时。机器已有 Google Chrome/Chromium 时会直接复用，否则安装项目本地 Chromium。macOS 自动安装系统依赖时需要 Homebrew。Go 模块下载会在官方代理不可用时回退到 `goproxy.cn` 和 direct，可用 `SEO_WORKBENCH_GOPROXY` 覆盖代理链。

```bash
./setup.sh --check   # 只验证，不安装
./setup.sh --yes     # 非交互安装，适合 agent/CI
./setup.sh --local-browser  # 安装 Playwright 固定版本 Chromium，适合基准对比
```

## 技术栈与性能证据

```bash
env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench technology --json
env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench performance --json
env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench performance --runs 1 --form-factor desktop --json
env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench evidence --performance --json
```

性能分析固定使用 Lighthouse 13.4.0。默认对项目首页顺序运行 5 次，至少 3 次有效才生成代表结果，并保留每次完整 LHR、代表 JSON、HTML 报告、运行环境和波动范围。默认网络边界会逐连接解析并拒绝私网地址，写盘前还会脱敏 URL 中的凭据和敏感查询值：

```text
projects/default/audits/performance/performance-*/run-*.json
projects/default/audits/performance/performance-*/representative.json
projects/default/audits/performance/performance-*/report.html
projects/default/audits/performance/performance-*/summary.json
projects/default/audits/performance/latest.json
```

单次运行适合烟测，不适合趋势结论。跨时间比较应保持相同 form factor、Lighthouse、浏览器版本和机器环境；报告会记录 `browser_version`，其中 `high_variance` 为真时不应直接判定回归。需要严格固定浏览器时，先运行 `./setup.sh --local-browser`。

## 多店铺管理

每家店铺使用一个独立目录，不需要数据库或中央配置：

```text
projects/
├── default/
├── wildone/
└── another-store/
```

```bash
# 初始化和选择店铺
env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench \
  --project wildone init shopify --name "Wild One" --url "https://example.com"

# 列出所有含 state.json 的店铺
env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench projects --json

# 后续命令使用同一个店铺 id
env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench --project wildone status --json
```

`--project wildone` 等价于 `--project-dir projects/wildone`。店铺 id 只允许小写字母、数字和连字符；现有 `projects/default` 行为保持不变。

## 审计 Diff

默认将当前店铺每种审计的最新不可变记录，与 URL、设备、运行配置和工具版本一致的最近基线比较：

```bash
env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench \
  --project wildone audit-diff --json
```

结果写入：

```text
projects/wildone/audits/diffs/audit-diff-<timestamp>.json
projects/wildone/audits/diffs/latest.json
```

Raw diff 覆盖状态码、跳转、title/meta/canonical/robots、H1、Schema、图片、链接和采集错误；Technology diff 覆盖技术新增、移除与版本；Performance diff 覆盖性能分数和核心指标中位数。Performance 只有在 Lighthouse、form factor、浏览器、有效运行数、波动和 benchmark 环境可比时才会标记回归或改善。

显式比较仅支持单一类型，并且两个文件必须属于当前店铺：

```bash
env UV_CACHE_DIR=.uv-cache uv run --frozen --python 3.11 python -m seo_workbench \
  --project wildone audit-diff --kind performance \
  --from projects/wildone/audits/performance/old/summary.json \
  --to projects/wildone/audits/performance/new/summary.json --json
```

## 已知限制

- **无自动发布。** `/write` 产出草稿后需手动发布（WordPress 除外）。Headless CMS 的自动发布管线不在当前 scope。
- **单项目单站点。** 可以管理多个店铺，但每个 `projects/<id>` 仍对应一个站点；单个项目内的多站点/多语言 SEO 不在此版本覆盖。
- **Lighthouse 是实验室数据。** 当前没有接入 CrUX/PageSpeed field data，也没有定时调度或 LHCI Server。
- **本地探针不是完整的恶意网站沙箱。** Lighthouse 流量会经过私网过滤代理，但它不能替代操作系统或容器隔离；`--allow-private` 只用于明确可信的开发或内网站点。

## Credit

- [claude-seo](https://github.com/AgriciDaniel/claude-seo)
- [seomachine](https://github.com/TheCraigHewitt/seomachine)
- [superseo-skills](https://github.com/inhouseseo/superseo-skills)
- [wappalyzergo](https://github.com/projectdiscovery/wappalyzergo)
- [lighthouse](https://github.com/GoogleChrome/lighthouse)
