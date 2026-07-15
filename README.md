# SEO Workbench

基于社区开源项目而创建的SEO工作流，覆盖全链路：初始审计 → 战略规划 → 内容生产 → 质量审查 → 技术审计 → 外链建设 → 持续监控。

---
Todo:
- [X] tech stack recognization: wappalyzergo integration
- [ ] laboratorical test: lighthouse调度，lhci
- [ ] real UX: CrUX接入
- [ ] 审计diff
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

## 已知限制

- **无自动发布。** `/write` 产出草稿后需手动发布（WordPress 除外）。Headless CMS 的自动发布管线不在当前 scope。
- **单站点假设。** 当前工作流假设一个项目对应一个站点。多站点/多语言 SEO 不在此版本覆盖。

## Credit

- [claude-seo](https://github.com/AgriciDaniel/claude-seo)
- [seomachine](https://github.com/TheCraigHewitt/seomachine)
- [superseo-skills](https://github.com/inhouseseo/superseo-skills)
- [wappalyzergo](https://github.com/projectdiscovery/wappalyzergo)
- [lighthouse](https://github.com/GoogleChrome/lighthouse)
