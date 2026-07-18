# SEO Workbench

[English](README.md) | 简体中文

一个本地优先的 SEO 工作台，用于技术审计、内容规划和可重复的证据采集。你可以使用命令行，让 AI 编程代理（agent）操作，也可以打开可选的浏览器界面。

![SEO Workbench 总览](docs/assets/workbench-overview.jpg)

上图来自真实项目。审计证据、工作流状态、技术栈结论、性能结果和工作文档保存在同一个项目中，不再散落在一次性报告里。

## 主要能力

| 领域 | 已包含的能力 |
| --- | --- |
| 网站证据 | 原始 HTML、跳转、元数据、robots.txt、Sitemap、代表路由和浏览器渲染检查 |
| 技术栈 | 类似 Wappalyzer 的识别结果，以及架构和 SEO 影响分析 |
| 性能 | 可重复的 Lighthouse 多次采样、CrUX 真实用户数据和 40 周历史 |
| Search Console | 只读采集搜索表现、URL Inspection 和 Sitemap 状态 |
| 变化追踪 | 比较 Raw、Technology、Lighthouse、CrUX 和 GSC 的可比快照 |
| SEO 工作流 | 战略、内容简报、内容生产、质量审查、技术审计、外链和持续监测 |
| 项目管理 | 每个网站使用独立的本地目录，私有运行数据不会进入 Git |

SEO Workbench 不绑定特定 agent。Codex、Claude Code 或其他编程 agent 都可以使用相同的 `./seo` 命令、项目文件和本地技能。关闭界面后，命令行仍然是完整的操作入口。

## 快速开始

```bash
git clone https://github.com/xolarvill/seo-workbench.git
cd seo-workbench
./setup.sh
```

创建项目并采集第一批证据：

```bash
./seo --project my-site init general \
  --name "My Site" --url "https://example.com"

./seo --project my-site evidence --rendered --technology --json
./seo --project my-site performance --json
```

打开工作台：

```bash
./seo --project my-site ui
```

界面只监听 `127.0.0.1`。它是可选的，并且与命令行使用同一套本地项目文件。

## 让 agent 操作项目

从仓库根目录启动你的编程 agent，并告诉它项目 ID。第一次可以直接提出这样的任务：

> 审计 `my-site` 项目，解释技术和性能问题，然后利用本地工作台制定一份内容 SEO 战略。

Agent 可以通过以下命令读取当前状态和下一步任务：

```bash
./seo --project my-site status --json
./seo --project my-site next --json
```

如果界面已经开启，agent 新增的审计文件和 Markdown 文档会自动显示在界面中。

## 工作台界面

浏览器界面包括项目切换、证据状态、审计操作、工作流进度、文件浏览，以及支持源码、分栏和预览模式的 Markdown 编辑器。

![SEO Workbench Markdown 编辑器](docs/assets/workbench-editor.jpg)

编辑器会在保存前检查文件版本。如果 agent 同时修改了同一份文档，界面会保留你的本地编辑，并提示比较或重新加载，不会直接覆盖任一版本。

<details>
<summary>手机布局</summary>

<p align="center">
  <img src="docs/assets/workbench-mobile.jpg" alt="SEO Workbench 手机界面" width="375">
</p>

</details>

## 常用命令

```bash
# 项目与工作流
./seo projects --json
./seo --project my-site status --json
./seo --project my-site next
./seo --project my-site step done

# 技术证据
./seo --project my-site evidence --rendered --json
./seo --project my-site technology --json
./seo --project my-site performance --json

# 配置完成后的 Google 证据
./seo --project my-site crux --json
./seo --project my-site gsc collect --json

# 比较最近的可比快照
./seo --project my-site audit-diff --json

# 环境与项目检查
./seo --project my-site validate --json
./seo --project my-site doctor --json
./setup.sh --check
```

完整参数可以通过 `./seo --help` 和 `./seo <command> --help` 查看。

## 本地项目结构

每个网站使用一个独立目录：

```text
projects/my-site/
├── state.json
├── context/
├── strategy/
├── content/
├── audits/
└── .runtime/
```

除了用于分发的 `projects/default/` 脚手架，其他项目目录都被 Git 忽略。凭据、Google 令牌、GSC 绑定、审计数据和工作文档默认只保存在本机，除非你主动导出。

## 可选的 Google 集成

CrUX 需要 Google API 密钥。GSC 支持桌面 OAuth 和服务账号（service account），只申请只读权限，不会提交 Sitemap，也不会请求索引。

配置步骤、认证方式、证据范围和状态含义请查看 [Google 集成说明](docs/google-integrations.md)。

## 安装要求

`./setup.sh` 会创建 Python 环境，安装锁定的 Python 和 Node 依赖，构建 Go 技术栈辅助程序和浏览器界面，并为渲染审计与 Lighthouse 查找 Chrome 或 Chromium。

目前只有 macOS 和 Homebrew 支持自动安装缺失的系统运行时。其他系统需要先准备：

- Git
- uv
- Python 3.11
- Go 1.25 或更新版本
- Node.js 24
- Chrome 或 Chromium

## 进一步阅读

- [Google 集成说明](docs/google-integrations.md)
- [独立工作台架构](docs/independent-workbench.md)
- [保留的 SEO 能力](docs/capability-preservation.md)
- [SEO 工具链协同工作流指南](docs/SEO工具链协同工作流指南.md)
- [Shopify 从 0 到 1 SEO 建设进阶教程](docs/Shopify从0到1-SEO建设进阶教程.md)
- [Shopify Hydrogen Headless SEO 指南](docs/Shopify-Hydrogen-Headless-SEO指南.md)

## 当前边界

- 工作台暂时没有内置定时任务或托管服务。
- 一个项目对应一个网站。不同网站或店铺应使用不同的项目目录。
- Lighthouse 实验室数据、CrUX 真实用户数据和 GSC 搜索数据始终作为独立证据使用。
- GSC 首次 OAuth 授权需要用户在浏览器中确认。
- 本地探针默认拒绝私网目标，但它不是针对恶意网站的完整沙箱。

## 鸣谢

SEO Workbench 保留并改造了以下项目中的有用思路和资料：

- [claude-seo](https://github.com/AgriciDaniel/claude-seo)
- [seomachine](https://github.com/TheCraigHewitt/seomachine)
- [superseo-skills](https://github.com/inhouseseo/superseo-skills)
- [wappalyzergo](https://github.com/projectdiscovery/wappalyzergo)
- [Lighthouse](https://github.com/GoogleChrome/lighthouse)

组件的具体授权和归属请查看仓库中的 skill 与第三方说明文件。

## 许可证

[MIT](LICENSE)
