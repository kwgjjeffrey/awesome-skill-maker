---
name: awesome-skill-maker
description: 创建或改造大型模块化 Skill 开源项目，建立 setup、runtime、目录规范、GitHub 源码追踪及可安装升级的 Release 制品。用户准备长期维护和分发一个大型 Skill 时使用。
---
# Awesome Skill Maker

从当前安装制品执行工具；不要要求用户 clone 本 Skill 的开发仓库。先确认目标项目、能力模块、平台与交付范围；已有项目先保留其业务边界和用户数据。

按任务读取模块：
- 创建项目、拆分模块、校验结构：[project/SKILL.md](project/SKILL.md)。
- 安装、前置校验、升级、回退：[setup/SKILL.md](setup/SKILL.md)。
- 版本、源码追踪、构建及 GitHub 分发：[release/SKILL.md](release/SKILL.md)。
- 设计常驻服务、GUI 和共享调用边界：[runtime/SKILL.md](runtime/SKILL.md)。

`<skill>` 指本文件所在的已安装目录；`<repo>` 指用户目标源码仓库。二者不能混用。Python 3.9+ 是按需工具前提，无常驻服务或第三方 Python 依赖；缺失时明确报告，不改系统 Python 或 shell 配置。

入口只放使用边界、模块导航和真正可执行的操作。模块的 `SKILL.md` 放消费指令，`AGENTS.md` 放开发设计与验证约束。每个脚本用完整动宾名，专属工具留在模块；共用确定性逻辑放 `utils/`。生成脚手架只是起点，业务能力必须实现并验证之后才能宣称可用。
