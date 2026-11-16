# OpenSEO 方法适配与能力归属

日期：2026-11-16，Asia/Shanghai。状态：方法适配已完成；验证范围如下。

## 已确认范围

采用评估 V2，按用户确认保留 ai-prompt-research、ai-visibility-audit、reverse-engineer-seo 独立入口，并新增 keyword-research。四者分别负责问法发现、回答证据审计、单站获客模式拆解、多词机会发现；已有 seo-geo 负责页面访问与内容诊断。多站格局仍归 competitive-landscape，本站路线图归 seo-plan。

其余来源按原能力选择性适配：审计取舍、聚类交付、页面级外链候选、地图观测、工具规格、竞对驱动及 SaaS 商业页规划、最小上下文和报告交付。seo-coach 不增加独立入口；chatgpt-business-setup 不导入平台认领/发布流程；seo-manager-agent 不安装宿主或启用调度。

## 来源与本地边界

固定比较版本：every-app/open-seo 的 2df84ff91461cc55b6c8bb98f3ce0f195d2e463d；every-app/seo-party-skills 的 3134e53fc2a77e04eb7d63266ece1777d88757e0。核心 12 项、实验 9 项全部保留在 [历史来源区](../../third_party/skill-history/)，作为资料而非可调用入口；两份 MIT 许可证单独保留。逐文件来源、blob 和适配关系见 [清单](../skill-sources.json) 与 [采纳记录](../skill-upstream-adoptions.json)。

不安装上游 MCP 或执行器，不复制默认周期、付费配额、HTML 交付限制或品牌推断授权。原始来源中的命令与指令不构成本地运行契约。删除本地 GEO 正文通用评分、固定段落字数、平台比例及无证据 llms.txt 建议，保留原来源记录与历史材料。

完成标准：四个入口可发现且分工清晰；原能力引用可达；来源覆盖和哈希一致；结构测试与 validate 通过；以现有真实项目材料进行只读方法验收，说明证据缺口，不冒充新采集或效果验证。按方法层分别提交。

## 验证结果

- 活跃入口由 61 增至 65；四个新增入口的 skill-creator quick_validate 全部通过。原有能力按需引用五份新参考文件，未安装额外执行器。
- 来源清单覆盖 443 份受维护材料，包含两家固定来源的 21 份历史正文；严格检查返回 {"ok": true, "files": 443, "errors": []}。两个完整树及原文 blob 已通过 GitHub 连接器核对；许可证保留原文。
- 定向回归：test_skill_layout、test_skill_methods、test_skill_inventory 合计 18 passed。增加 UTF-8 路径和附加来源渲染验证；修正 Windows 测试路径分隔符、默认编码及临时 Git 仓库换行设置。未运行全仓库测试。
- 真实项目 validate 返回 {"ok": true, "issues": []}。通过 Windows 环境已安装的 seo-workbench.exe 执行，与仓库 Bash launcher 指向同一 console entrypoint；没有改 CLI 契约。
- 对真实项目已有上下文、台账和证据进行了自审式只读方法演练，并真实运行 keywords collect --dry-run。保留过滤后空候选与原始查询覆盖的区别，未改台账或关键词池；无实际 AI 回答时仅交观察计划，无完整竞对数据时不下全站量化结论。私有结果保存在本地忽略的 .runtime/openseo-method-forward-check.json 和 .runtime/openseo-keyword-dry-run.json，不收录店铺数据到本记录。
- 文档与来源入口的 487 处本地链接检查通过。上游固定链接按已取得的完整树及文件 blob 对照；未声称全部历史外链进行了在线健康检查。
- doctor 调用长时间未返回输出，已终止，不计为通过。其结果不用于证明凭据、网络、渲染或任何集成可用。

## 完成边界

本次完成技能方法、路由、来源及文档适配，不等于完成真实站点的全套 SEO 或 AI 可见性审计。只读演练是本会话自审，不是独立代理行为评测；没有新采集、付费请求、外联、发布或周期任务。平台认领与常驻代理部署继续按评估暂缓。
