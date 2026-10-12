---
name: awesome-skill-maker-runtime
description: 设计大型 Skill 的本地 runtime、GUI 和共享业务实现边界。
---
# Runtime 边界

先判断能力是否需要常驻服务；本 Skill 只有按需 Python 工具，无 daemon。需要常驻服务的目标项目采用 Rust，目录命名 `local-runtime/`。它是实现目录，不为了目录存在而添加 SKILL.md。发布对应平台/架构二进制，setup 统一拥有安装、检查、启停、升级和发现端口的实现。

GUI、CLI、MCP 使用相同 use-case/dispatch/validation 实现，不复制业务规则。GUI 展示真实模块输入、输出、项目状态、进度与失败，不放伪成功按钮。服务默认绑定 loopback；鉴权、协议版本、请求范围、发现文件、健康检查、并发、空闲退出和恢复行为都要定义。端口从实际监听结果写发现文件，不靠固定端口猜进程。

配置、账号凭据、状态、缓存与不可变制品分开；凭据用受限权限或系统凭据库，不进入 stdout、日志或 HTML。平台启停通过适配器实现，macOS launchd / Linux user service / Windows Task Scheduler 只宣称实测平台。更新期间防止并行更新，先校验 staged 二进制再激活；业务迁移与制品回退分开设计。

测量真实空闲 RSS、线程、进程数和启动耗时，附机器/版本/范围，不虚构资源预算或性能结果。按需构建工具可使用 Python/Node，避免为 GUI 增加额外常驻 Node/Python 服务。依赖锁定并由 setup 私有准备，不能假定作者机器的 PATH、node_modules 或其他 checkout 存在。
