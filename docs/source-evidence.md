# 反向沉淀依据（2026-10-12）

本次读取本机 agent-colab 与 trace（Agent Dev Suite）源码；没有修改它们。

- agent-colab/AGENTS.md：独立 Core/GUI/Skill/Shell 版本、共享 Core 调用边界、provider 可替换、制品公开读回验证。
- agent-colab/skills/AGENTS.md 与 colab/AGENTS.md：安装目标适配器、版本目录/稳定链接/receipt、完整入口验收、setup 单一升级权威、归档检查及外部用户状态。
- agent-colab/skills/colab/setup/colab-setup：componentVersions、缓存下载、平台生命周期；不是本产品已实现能力。
- trace/AGENTS.md、setup/SKILL.md、setup/AGENTS.md、setup/install.sh、setup/github.mjs：源码消费者分离、私有依赖准备、开发 checkout 拒绝升级、GitHub manifest/tag/hash 校验、staging 更新。
- trace/release/AGENTS.md、release/build.mjs：干净 commit 构建、allowlist、GitHub 制品及 sourceCommit 追踪。
- my_wiki/knowledge/skill-authoring.md：用户明确的模块 SKILL.md / 开发 AGENTS.md、完整动宾脚本名、Rust 常驻 runtime、完整分发约定；原文一并保存。

选择：当前产品只有单一 Python stdlib 制品，不照搬 Colab 的服务器、R2、Electron、业务 CRDT 或 Trace 的 Node/MCP 协议。多组件版本和 Rust runtime 为目标项目设计规则，当前工具不假装提供这些实现。
