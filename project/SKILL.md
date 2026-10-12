---
name: awesome-skill-maker-project
description: 从已安装的 Awesome Skill Maker 创建并校验模块化 Skill 项目。
---
# 项目组织

先确定能力归属与实际需要的工具，避免按技术类型堆放所有业务模块。

```sh
python3 <skill>/project/scripts/initialize_skill_project.py --destination <new-repo> --name <skill-name> --repository <owner/repo> --description '<能力和触发场景>'
python3 <skill>/project/scripts/validate_skill_project.py --repo <repo>
```

初始化要求不存在的目标目录，创建独立源码骨架、setup 与 release 工具、GitHub CI；不创建 GitHub 仓库、不提交或推送。接着按用户业务添加 `<module>/SKILL.md`、`<module>/AGENTS.md` 及该模块脚本/模板；将模块加入根入口导航和 `skill-project.json` 的 `artifactPaths`。

结构：根 `SKILL.md` 是消费入口；根 `AGENTS.md` 是开发约束；`setup/` 管生命周期；`release/` 管构建分发；业务模块自持工具；`utils/` 只放确实共享逻辑。开发测试放 `tests/`，设计证据放 `docs/`，二者默认不分发。脚本名完整表达动作对象，例如 `validate_skill_project.py`，不要用 `check.py`、`start.py`。工具说明输入、输出、修改范围和失败处理。

校验器检查名称、版本、白名单、入口、模块开发说明、短脚本名和消费路径泄漏，输出 JSON 并以非零状态报告错误。它不判断业务语义，也不替代业务验收。完成项目后，使用自己的 release 工具构建制品，从临时安装目录执行实际操作；目标仓库只能保留它自己的注册表、适配器、测试用例和依赖声明，不能依赖作者的其他源码仓库。
