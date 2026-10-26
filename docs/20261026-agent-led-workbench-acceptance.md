# Agent主导工作与next退役验收

日期：2026-10-26。范围：仓库入口、本地方法发现、CLI／UI任务调度退役、教程同步。设计：[Agent按目标选择本地SEO方法](agent-skill-routing-design.md)。本记录属于仓库改造，不登记为店铺业务工作。

## 实施结果

1. AGENTS与Claude适配入口要求agent主动从当前目标、项目上下文、产物和证据选择方法；技能索引给任务入口及三来源材料位置，不构成调用白名单或固定顺序。
2. 移除 `next` CLI命令、cmd_next及UI next契约；旧步骤描述更名为step_reference，仅作历史参考。status提供skill_index，保留旧phase／step投影，但不输出next指令。
3. 原Plan入口改为Methods，保留原URL。地图不依赖当前阶段或阶段顺序隐藏内建能力，不突出当前步骤、不提供Start／Mark done／Skip；首页不再宣布Workflow complete或下一步。
4. 原项目phase／step／history保留，手动维护CLI和HTTP接口暂作兼容。测试确认读取status与workspace不改写旧state。维护旧阶段时不再生成Run next等提示。
5. README、安装完成提示、项目上下文技能及操作教程已更新；原始诊断明确标记为历史观察。

这是有意的接口变更：调用 `next` 退出码为2；CLI status.next、HTTP workspace.next及前端NextContract已删除。依赖这些字段的外部脚本应改为读取具体工作区和产物，不应重新复制阶段调度器。

## 回归验证

先添加并运行三项回归测试，旧实现全部失败：next仍被接受、status仍给出next、workspace仍给出next。完成改造后通过。

实际运行的测试与检查：

```bash
.venv/bin/python -m pytest \
  tests/test_state_workflow.py tests/test_ui.py \
  tests/test_keyword_workspace.py tests/test_content_briefs.py \
  tests/test_content_clusters.py tests/test_content_drafts.py \
  tests/test_content_publish.py tests/test_content_review_push.py \
  tests/test_content_review_digest.py -q
npm run ui:typecheck
npm run ui:test
npm run ui:build
bash -n setup.sh
git diff --check
```

- Python相关状态、API与内容链路：110 passed。随后简化旧阶段维护的重复赋值，再跑state/workflow测试：21 passed。
- 前端：10个测试文件、79项通过；类型检查与构建通过。
- 运行项目validate返回ok=true，缺少可选browser evidence目录仅warning。此检查不等于专业流程或所有历史审计健康。
- 本地文档链接及技能索引目标检查通过。
- 架构复核未发现可行动问题；兼容数据、旧接口消费者与能力地图不受阶段限制已纳入检查。

构建保留现有大chunk提醒，测试运行有Node localStorage实验性提醒；均未作为此次改造引入的缺陷，也未为清除提醒扩大修改范围。

## 浏览器验证

Browser插件不可用，使用项目venv中的Playwright及仓库匹配浏览器，沿用shared workload lease与managed_browser诊断／清理。测试服务只绑定loopback，使用临时合成项目；未连接或改写真实店铺。

- 桌面1440×1000与手机390×844分别通过；手机同时配置移动UA与触屏。
- 首页没有Next action或Workflow complete；进入Methods后可见内容与技术能力，无步骤完成按钮。
- 从地图进入Keywords成功；两种视口均无整页横向溢出，无页面／控制台错误，截图已检查。
- 初次浏览器启动受到macOS沙箱进程权限阻止，保留诊断后使用获准的同一匹配浏览器完成检查，未切换用户日用Chrome。
- 测试脚本的network-idle等待不适用于持续事件流，后改DOM-ready；URL断言适配项目query与hash组合后完成导航验收。这些是测试等待条件调整，不是网站故障证据。

截图和浏览器诊断仅保留在本地临时测试目录，不将本机路径、会话ID或项目私有资料写入公共仓库。

## 独立会话行为抽样

未继承本聊天的agent接受两个只读场景，提示中未点名技能。它实际读取AGENTS、技能索引与相关正文：

- 对已有文章的局部技术说明审读，选择reader-experience-review及校准参考；保留有依据的谨慎说明，不启动全文重写或市场研究。
- 对已有brief但SERP范围未确认、旧阶段已勾完的话题群续接，选择topic-cluster-planning、content-brief和keyword-deep-dive核查方法；先恢复owner、日期、范围和证据，不把阶段完成当成研究完成。

场景没有提供具体文章和业务材料，因此只验收自主选读、范围控制和接续判断，不声称完成真实SEO任务。这个改造后样本也不是随机对照，不能据此量化改善幅度或保证所有未来会话遵循。下一次真实SEO工作仍应检查实际产物与证据。

## 交付边界

本轮没有新增自动任务分类器、全局调用日志或通用任务库，也未宣称全部保留模块已逐项认证。三来源方法可以按需查阅；发现旧脚本、固定密度／字数等冲突时遵循现行Workbench规则，需要适配则单独留痕。

公共改动按层提交并同步个人main与公司工作分支，最终返回公司分支。具体提交由Git历史记录；不将店铺运行文件带入开源版本。需要回滚时revert对应提交，保留项目状态和证据。
