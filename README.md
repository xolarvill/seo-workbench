# SEO Workbench

基于社区开源项目而创建的SEO工作流，覆盖全链路：初始审计 → 战略规划 → 内容生产 → 质量审查 → 技术审计 → 外链建设 → 持续监控。

---
Todo:
- [X] tech stack recognization: wappalyzergo integration
- [X] laboratory test: Lighthouse 本地多次采样与代表结果
- [X] real UX: CrUX 当前值与 40 周历史
- [X] 多店铺管理
- [X] 审计diff
- [X] GSC 只读接入
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

安装完成后的日常入口是 `./seo`。激活 `.venv` 后也可直接使用 `seo-workbench`；`python -m seo_workbench` 仅保留为兼容与诊断入口。

`setup.sh` 是安装入口，不只是环境检查。它会安装或配置 Python 3.11、Go 快速指纹 helper、balanced Wappalyzer、Google OAuth 支持、Node 24 LTS、锁定版本的 Lighthouse、开发验收依赖和浏览器运行时。机器已有 Google Chrome/Chromium 时会直接复用，否则安装项目本地 Chromium。macOS 自动安装系统依赖时需要 Homebrew。Go 模块下载会在官方代理不可用时回退到 `goproxy.cn` 和 direct，可用 `SEO_WORKBENCH_GOPROXY` 覆盖代理链。

```bash
./setup.sh --check   # 只验证，不安装
./setup.sh --yes     # 非交互安装，适合 agent/CI
./setup.sh --local-browser  # 安装 Playwright 固定版本 Chromium，适合基准对比
```

## 技术栈与性能证据

```bash
./seo technology --json
./seo technology --scan-mode fast --json
./seo performance --json
./seo performance --runs 1 --form-factor desktop --json
./seo evidence --performance --json
./seo crux --json
./seo gsc collect --json
./seo evidence --crux --gsc --json
./seo evidence --rendered --crawl-limit 5 --json
```

`technology` 默认用 balanced Wappalyzer 检查页面、脚本、robots 和 DNS，并对明确的 `vue-vendor`、`swiper-vendor`、分析标签 URL 等资源信号做可追溯 fallback；已有 rendered evidence 时还会合并真实 DOM、网络请求和不同 UA 的最终 URL。`--scan-mode fast` 使用可复现的 Go headers/cookies/raw-HTML 指纹。零检测只表示本次证据未命中，不会被解释为技术或标签一定不存在。

项目级 `evidence` 默认从 raw/rendered 内链中抽取最多 5 个同源代表路由，排除静态资源、敏感查询参数和同模板重复 URL，用于发现 SPA 空壳与跨路由重复元数据。`--crawl-limit 0` 可恢复严格单 URL；上限为 20，不是通用爬虫。

性能分析固定使用 Lighthouse 13.4.0。默认对项目首页顺序运行 5 次，至少 3 次有效才生成代表结果，并保留每次完整 LHR、代表 JSON、HTML 报告、运行环境、波动范围、requested/final URL 和跨运行跳转一致性。默认网络边界会逐连接解析并拒绝私网地址，写盘前还会脱敏 URL 中的凭据和敏感查询值：

```text
projects/default/audits/performance/performance-*/run-*.json
projects/default/audits/performance/performance-*/representative.json
projects/default/audits/performance/performance-*/report.html
projects/default/audits/performance/performance-*/summary.json
projects/default/audits/performance/latest.json
```

单次运行适合烟测，不适合趋势结论。跨时间比较应保持相同 requested/final URL、form factor、Lighthouse、浏览器版本和机器环境；报告会记录 `browser_version`，其中 `high_variance` 为真或最终 URL 不一致时不应直接判定回归。需要严格固定浏览器时，先运行 `./setup.sh --local-browser`。

### CrUX 真实用户数据

CrUX 与 Lighthouse 独立保存。默认查询页面的 aggregate、mobile、desktop 当前 28 天滚动数据和 40 周历史；页面样本不足时回退到 origin 并显式记录范围，站点流量不足时返回 `no_data`，不会伪造成 Lighthouse 结果。

```bash
export SEO_WORKBENCH_CRUX_API_KEY="your-key"
./seo \
  --project wildone crux --json

# 指定页面或单一设备
./seo \
  --project wildone crux --url https://example.com/products/item --form-factor mobile --json
```

API key 也可保存为 `.runtime/google/crux-api-key`，文件不得是 symlink。证据写入 `projects/<id>/audits/crux/`；`latest.json` 是稳定指针。

### Google Search Console

GSC 是只读集成。首次使用需要在 Google Cloud 启用 Search Console API、创建 Desktop OAuth client，然后由用户完成一次浏览器授权：

```bash
./seo \
  --project wildone gsc auth --client-secret /path/to/oauth-client.json

./seo \
  --project wildone gsc properties --json

./seo \
  --project wildone gsc bind --property sc-domain:example.com --json

./seo \
  --project wildone gsc collect --json
```

`gsc collect` 包含完整 28 天与前 28 天 Search Analytics、Sitemap 状态，以及最多 10 个代表 URL 的 Google 索引版本检查。它不是 live URL test，也不会提交 Sitemap 或请求索引。无界面自动化可用 `gsc auth --service-account /path/to/account.json`，但必须先把该 service account 加入对应 GSC property。

OAuth client、token、service account 和项目绑定位于 `.runtime/`；GSC 审计数据使用 `0600` 权限并被 Git 忽略。完整配置和状态语义见 [Google integrations](docs/google-integrations.md)。

## 多店铺管理

每家店铺使用一个独立目录，不需要数据库或中央配置。版本库只跟踪 `projects/default/` 脚手架；其他 `projects/<id>/` 默认由 `.gitignore` 排除，只保留在本机：

```text
projects/
├── default/
├── wildone/
└── another-store/
```

```bash
# 初始化和选择店铺
./seo \
  --project wildone init shopify --name "Wild One" --url "https://example.com"

# 列出所有含 state.json 的店铺
./seo projects --json

# 后续命令使用同一个店铺 id
./seo --project wildone status --json
```

`--project wildone` 等价于 `--project-dir projects/wildone`。店铺 id 只允许小写字母、数字和连字符；现有 `projects/default` 行为保持不变。

## 审计 Diff

默认将当前店铺每种审计的最新不可变记录，与 URL、设备、运行配置和工具版本一致的最近基线比较：

```bash
./seo \
  --project wildone audit-diff --json
```

结果写入：

```text
projects/wildone/audits/diffs/audit-diff-<timestamp>.json
projects/wildone/audits/diffs/latest.json
```

Raw diff 覆盖状态码、跳转、title/meta/canonical/robots、H1、Schema、图片、链接和采集错误；Technology diff 覆盖技术新增、移除与版本；Performance diff 覆盖性能分数和核心指标中位数；CrUX diff 覆盖同范围、同设备的 p75 与 CWV 等级；GSC diff 覆盖同 property、同时间窗口的搜索表现、索引状态和 Sitemap 错误。任何可比性门槛不满足时都只记录 change，不标记回归或改善。

显式比较仅支持单一类型，并且两个文件必须属于当前店铺：

```bash
./seo \
  --project wildone audit-diff --kind performance \
  --from projects/wildone/audits/performance/old/summary.json \
  --to projects/wildone/audits/performance/new/summary.json --json
```

## 已知限制

- **无自动发布。** `/write` 产出草稿后需手动发布（WordPress 除外）。Headless CMS 的自动发布管线不在当前 scope。
- **单项目单站点。** 可以管理多个店铺，但每个 `projects/<id>` 仍对应一个站点；单个项目内的多站点/多语言 SEO 不在此版本覆盖。
- **Lighthouse 与 CrUX 不能互相替代。** Lighthouse 是受控实验室数据；CrUX 是满足流量门槛的 Chrome 聚合数据。当前没有定时调度或 LHCI Server。
- **GSC URL Inspection 不是实时测试。** API 返回 Google 索引中的版本，且受 property 配额限制；工作台默认每次最多检查 10 个代表 URL。
- **本地探针不是完整的恶意网站沙箱。** Lighthouse 流量会经过私网过滤代理，但它不能替代操作系统或容器隔离；loopback、RFC1918、link-local 与 CGNAT 默认拒绝。`198.18.0.0/15` 只作为透明代理 fake-IP 范围放行；`--allow-private` 仍只用于明确可信的开发或内网站点。

## Credit

- [claude-seo](https://github.com/AgriciDaniel/claude-seo)
- [seomachine](https://github.com/TheCraigHewitt/seomachine)
- [superseo-skills](https://github.com/inhouseseo/superseo-skills)
- [wappalyzergo](https://github.com/projectdiscovery/wappalyzergo)
- [lighthouse](https://github.com/GoogleChrome/lighthouse)
