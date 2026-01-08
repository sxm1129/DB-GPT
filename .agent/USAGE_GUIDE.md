# UI/UX Pro Max 使用指南

## 概述

UI/UX Pro Max 已经安装到你的 DB-GPT 项目中。当你在 Antigravity 中请求 UI/UX 相关工作时，Agent 会自动使用这个 workflow 来提供专业的设计建议和实现。

## 自动激活

Workflow 配置了 `auto_execution_mode: 3`，这意味着当你提到以下关键词时，Agent 会自动激活：

- **设计相关**：design, build, create, implement, review, fix, improve
- **UI/UX 相关**：界面、样式、配色、字体、布局、交互

## 使用方式

### 方式一：直接描述需求（推荐）

直接在 Antigravity 中描述你的 UI/UX 需求，Agent 会自动使用 UI/UX Pro Max 的能力：

```
重构聊天页面，使用现代化的 Glassmorphism 风格，配色要专业有科技感
```

```
优化首页的卡片组件，应用 SaaS 产品的设计风格，提升视觉层次
```

```
改造侧边栏导航，使用更现代的设计，添加平滑的过渡动画
```

### 方式二：明确指定使用 Workflow

如果需要明确指定，可以这样：

```
使用 UI/UX Pro Max workflow 来重构前端界面
```

```
请按照 UI/UX Pro Max 的设计指南来改造这个组件
```

## 重构前端的完整流程示例

### 示例 1：重构整个页面

**你的提示词：**
```
重构聊天页面（web/pages/chat/index.tsx），要求：
1. 使用现代化的 Glassmorphism 风格
2. 应用 SaaS 数据产品的配色方案
3. 使用专业的字体配对（Poppins + Open Sans）
4. 添加平滑的过渡动画
5. 优化响应式布局
6. 提升整体的视觉层次和设计感
```

**Agent 会做什么：**
1. 自动搜索相关的设计系统（style, color, typography）
2. 分析当前代码结构
3. 应用设计指南进行改造
4. 实现现代化的 UI 组件

### 示例 2：优化特定组件

**你的提示词：**
```
优化消息气泡组件，使用现代化的设计风格，添加微交互效果
```

**Agent 会做什么：**
1. 搜索消息组件的 UX 最佳实践
2. 应用动画和交互指南
3. 改进视觉设计

### 示例 3：整体设计系统升级

**你的提示词：**
```
对整个前端项目进行现代化改造：
- 应用 Glassmorphism + Minimalism 风格
- 统一使用 SaaS 配色方案
- 优化所有组件的视觉层次
- 添加专业的动画效果
- 确保响应式和可访问性
```

## 可用的设计域

Agent 可以搜索以下设计域来获取专业建议：

1. **product** - 产品类型推荐（SaaS, e-commerce, dashboard）
2. **style** - UI 风格（glassmorphism, minimalism, brutalism）
3. **typography** - 字体配对（Google Fonts）
4. **color** - 配色方案（按产品类型）
5. **landing** - 页面结构（如果适用）
6. **chart** - 图表推荐（如果适用）
7. **ux** - UX 最佳实践和反模式
8. **stack** - 技术栈特定指南（Next.js, React 等）

## 最佳实践提示词模板

### 模板 1：完整重构
```
重构 [页面/组件路径]，要求：
- 风格：[glassmorphism/minimalism/modern/professional]
- 配色：[saas/data analytics/tech]
- 字体：[modern professional/tech startup]
- 动画：[smooth transitions/micro-interactions]
- 响应式：[mobile-first/responsive]
```

### 模板 2：快速优化
```
优化 [组件名称]，应用现代化的设计风格，提升用户体验
```

### 模板 3：设计系统应用
```
将 UI/UX Pro Max 的设计系统应用到 [页面/组件]，确保：
- 视觉一致性
- 专业的设计感
- 良好的用户体验
- 响应式布局
```

## 实际使用示例

### 示例：重构聊天界面

```
请使用 UI/UX Pro Max 的能力重构聊天界面（web/pages/chat/index.tsx 及相关组件）：

1. 搜索适合聊天界面的设计风格和配色方案
2. 应用 Glassmorphism 效果到消息容器
3. 优化消息气泡的视觉设计
4. 添加平滑的发送动画
5. 改进输入框的设计
6. 确保暗色模式下的良好体验
7. 优化移动端响应式布局

要求：
- 现代化的专业设计
- 良好的视觉层次
- 流畅的交互体验
- 符合 SaaS 产品的审美标准
```

## 注意事项

1. **Python 环境**：确保已安装 Python 3.x（Agent 会自动检查）
2. **文件路径**：使用相对路径或绝对路径指定要改造的文件
3. **具体需求**：描述越具体，Agent 提供的方案越精准
4. **渐进式改造**：建议先改造单个页面/组件，验证效果后再扩展

## 验证 Workflow 是否工作

在 Antigravity 中尝试：

```
使用 UI/UX Pro Max 搜索适合数据仪表板的配色方案
```

Agent 应该会执行搜索命令并返回结果。

## 获取帮助

如果 Workflow 没有自动激活，可以：

1. 检查 `.agent/workflows/ui-ux-pro-max.md` 文件是否存在
2. 检查 `.shared/ui-ux-pro-max/` 目录是否存在
3. 确认 Python 3.x 已安装
4. 明确在提示词中提到 "UI/UX Pro Max" 或 "workflow"

---

**现在就开始使用吧！** 直接在 Antigravity 中描述你的 UI/UX 需求，Agent 会自动使用专业的设计系统来帮助你重构前端。


