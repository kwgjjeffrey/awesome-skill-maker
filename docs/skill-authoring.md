# Skill 编写约定

本文件沉淀用户对 Skill 组织、命名、分发与本地服务的要求。适用于本仓库后续 Skill 工作；独立 Skill 仓库建立时应带上此文档并在其 AGENTS.md 引用。

## 1. 分发完整能力

Skill 是文档、脚手架工具、模板及必要运行资源的完整分发单位，不只分发说明。
运行所需资源放在 Skill 分发目录内；不能依赖作者机器上未打包的工具目录。
开发测试与制品构建代码可以位于仓库外层，通常不进入用户制品。
第三方依赖如不直接打包，必须有可复现的准备机制，不能当作隐含前提。

## 2. 按模块组织

入口 SKILL.md 负责能力边界、模块导航和按需读取。
每个业务模块有自己的 SKILL.md，专属脚本和模板放模块内。
不要用一个 references 目录堆放全部模块说明来代替模块组织。
真正共用的功能放 utils；不为抽象方便搬走模块专属逻辑。
不要为了凑目录结构创建空 scripts 或虚构命令；设计时列明拟提供的实际工具。

## 3. 文件命名完整表达动作与对象

脚本文件使用完整、明确的动宾命名，建议 snake_case。
不能依靠上层目录才能猜出 inspect.py、check.py、update.py 等名称的对象。

| 避免 | 采用 |
|---|---|
| inspect.py | inspect_target_repository.py |
| check.py | check_api_semantics_consistency.py |
| diff.py | compare_registered_semantics.py |
| update.py | update_api_semantics_variables.py |
| scaffold.py | initialize_api_semantics_variables.py |
| start.py | start_local_runtime.py |

区分查看、比较、校验、生成候选、应用修改、提交注册；名称与实际行为一致。
每个工具说明输入、输出、修改范围、错误与差异处理；只讲“检查”“更新”不够。
模板命名指出生成对象与框架，例如 spring_semantics_controller.java.j2。

## 4. 区分工具、模板和提示词

工具处理确定性的提取、比较、合并、校验、状态管理与调用。
模板提供代码或配置骨架；提示词指导 Agent 理解业务、填写含义与复核。
不把业务理解冒充为脚本自动验证，也不让 Agent 手工重复可靠工具可完成的工作。

## 5. setup 与 local-runtime

setup 是 Skill 模块，具有 SKILL.md，负责初始化、安装、更新及本地服务启停状态。
本地前后端服务命名 local-runtime，表达它是本地运行服务；GUI 是其面向人类的交互入口。
local-runtime 放在完整分发目录内，但不因它有目录就放 SKILL.md；它是实现，不是 Agent 指令模块。
GUI 展示模块能力、真实输入输出及当前项目状态，调用与 Skill 脚本同一套能力，不另写业务规则。
状态、配置与缓存独立保存，更新不能覆盖用户配置或目标项目。
本地服务的协议、状态与生命周期属于设计；不要仅凭“有状态”就增加另一套常驻服务。

## 6. 清楚区分边界

原项目已有开发、测试、发布流程与 Skill 新增改造明确分开。
源码加工、线上业务服务、本地开发服务和平台服务不能混称。
最佳实践不等于协议约束；建议的源码位置不能变成强制项目目录或继承要求。
所有设计说明明确已实现、待实现和本轮不做的能力，不能将拟定命令当作现有能力。

## 8. local runtime 的技术约束

用户机器会同时运行很多 Skill runtime，常驻本地服务使用 Rust，控制空闲内存、线程和进程数量。开发脚本可按需启动；不要为 GUI 常驻额外的 Python 或 Node 服务。发布制品包含对应平台的 runtime 二进制，setup 负责生命周期。性能结论必须附测量范围与数据。

## 单一发现入口（2026-10-12 用户澄清）

一个大型 Skill 只有根 SKILL.md 使用 name/description YAML 元信息。内部模块仍叫 SKILL.md，但使用普通 Markdown，由根入口按需读取，不注册成多个独立 Skill。setup 内随制品分发可复制的安装提示词，面向 GitHub latest Release，并在开始安装时固定一次 release tag，避免下载期间混用版本。
