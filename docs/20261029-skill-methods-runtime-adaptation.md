# 专家方法整理与运行引用适配

日期：2026-10-29（Asia/Shanghai）。范围：已批准计划第 4、5 步。第 2、3 步见[能力归属和目录迁移](20261029-skill-layout-migration.md)，来源与历史见[来源参考](skill-sources.md)。

## 第 4 步：方法归属与来源保存

原有 11 份专家材料与 24 份流程文档逐项登记在 [skill-method-adaptations.json](skill-method-adaptations.json)。其中 34 份整理为当前能力的按需参考，scrub 仅保留历史。

- 编辑、内容审阅、元数据、SEO 编辑、内链、关键词分布、集群、标题、转化与表现方法分别挂在对应的主入口下。
- 研究、brief 到写作、旧文更新、内容日历、落地页和再利用流程改成输入、专业判断和交付物的参考；不复制原环境的命令执行链。
- 发布流程整理为当前平台的交付准备和状态核对，保留 WordPress 原文作为来源，不暗示 Workbench 已安装 WordPress 执行器。
- 每份适配参考记录使用条件、主入口和历史原文；清单通过 derived_from／adapted_by 保留双向关联。原文内容指纹单独核对。
- scrub 的字符处理和水印主张不构成阅读质量标准，不设置新的自动清理环节。后续写作标准改造独立进行。

主入口仍为 60 个；这一步只接入参考材料，不创建并列执行器、任务调度器或另一个状态数据库。

本层校验：`tests/test_skill_layout.py`、`tests/test_skill_methods.py`、`tests/test_skill_inventory.py` 共 11 项通过；来源清单覆盖 401 个文件，35 份历史原文的 SHA-256 保全检查通过。另增加本地维护脚本，刷新和检查指纹、来源关联及路径关系，不依赖临时脚本或外部服务。

## 第 5 步：运行与引用适配

本节在第 5 步完成时登记逐项处理、验证和剩余边界。

## 验证方法

使用项目 venv 运行结构与专业方法归属回归；来源清点脚本只读取本地文本、文件指纹和 Git 记录，不执行来源材料里的命令。

```bash
.venv/bin/python scripts/skill_inventory.py check
.venv/bin/python -m pytest tests/test_skill_layout.py tests/test_skill_methods.py -q
```

两个步骤分别 commit，保留可回滚记录；未运行外部采集、发布或消息发送。
