# UI 帮助气泡（HelpTooltip）规范

统一用 `ui/src/components/HelpTooltip.tsx`（基于 shadcn `Tooltip` / Radix），**禁止**在 feature 页里复制本地实现或本地样式。所有帮助气泡必须走同一套可读性规则。

## 内容规则

1. **简短优先**：能用 1 句说完的，不要写 2 句。
2. **长内容结构化**：内容超过两句、或包含多个要点时，用「加粗引导句 + 无序列表」两级呈现：
   - `strong` = 一句话结论（读者不深入也能带走的核心）；
   - `ul > li` = 支撑点（需要细节时再看）。
3. **口径一致**：同一概念（例如"描述性不确定性、非因果"、"FDR 控制"、"`insufficient_data` 不是无效果"）在所有页面使用同一表述，避免 UI 提示与教程文档打架。

## 结构规则

```tsx
<HelpTooltip label="可访问名称">短句，或 <><strong>引导句</strong><ul><li>要点</li><li>要点</li></ul></></HelpTooltip>
```

- `label` 是 aria-label（`Help: {label}`），必填；
- 触发器是 `role="img"` + `tabIndex={0}` 的 24×24 span，Radix 负责 hover/focus 打开、Escape 关闭和碰撞避让；
- `align="center"` 用于卡片标题旁的触发器，让气泡以标题帮助图标为中心展开；`align="right"` 用于贴近右边缘的触发器（如工具栏按钮旁）；
- 触发器**可以放进 `<button>`**：公共样式显式 `text-align: left` 和 `font-weight: 400`，抵抗 button 默认居中和加粗继承，不要为此写页面局部覆盖。

## 样式规则（公共组件已固定）

- 尺寸统一 24×24px，图标 14px；
- 气泡：`text-align: left`、`max-width: 320px`、带边框和阴影；Radix 根据视口自动翻转对齐，不再手写移动端断点；
- 长内容排版：`strong` 块级加粗引导句 + `ul` 网格列表（项间距 5px、列表文字用 `--ink-muted`）；
- 容器裁剪：含气泡的父容器保持 `overflow: visible`（参考 Pages 的 `.sourceRail` / `.viewer` 与表格 `.tooltipHeader` 处理），否则气泡会被 `overflow: hidden` 卡在容器里；
- 需要动效时使用 `tw-animate-css`，不要恢复页面局部的 tooltip CSS。

## 验收

- 新页面/新组件需要帮助说明时，`import { HelpTooltip } from "../../components/HelpTooltip"`；
- 不要重新引入 `CircleHelp` 图标手写气泡，不要给气泡加页面局部 `text-align`；
- 长文本先尝试压缩为短句；确需展开时使用引导句 + 列表。
