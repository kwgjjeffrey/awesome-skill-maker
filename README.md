# Awesome Skill Maker

把 Agent Colab、Agent Dev Suite 已验证的工程做法沉淀为可安装的 Skill，用于长期维护的大型 Skill 项目：按模块组织、初始化与校验、外部状态、GitHub 源码追踪、制品构建和安装升级。

消费方使用 Release 制品，开发方维护本仓库。当前实现单一 Python 标准库制品，不依赖其他项目源码；安装适配 macOS/Linux，Python 3.9+ 和 curl。Rust 常驻 runtime、多组件版本管理是目标项目设计约定，本产品没有后台服务。

## 安装制品

从 `kwgjjeffrey/awesome-skill-maker` 的 GitHub Releases 获取 `awesome-skill-maker-0.1.0.tgz` 和 `awesome-skill-maker-release.json`，再获取同一 tag 的 bootstrap：

```sh
curl -fL https://raw.githubusercontent.com/kwgjjeffrey/awesome-skill-maker/v0.1.0/setup/bootstrap_skill_installation.py -o bootstrap_skill_installation.py
python3 bootstrap_skill_installation.py \
  --archive awesome-skill-maker-0.1.0.tgz \
  --manifest awesome-skill-maker-release.json \
  --target "$HOME/.codex/skills/awesome-skill-maker" \
  --store "$HOME/.local/share/awesome-skill-maker"
```

bootstrap 验证 manifest 大小、SHA-256 和归档路径/类型后调用包内安装器。离线安装的 manifest 必须来自可信 Release；远端 upgrade 额外核对 tag/sourceCommit。当前不提供独立签名验证。稳定链接和不可变版本目录分离；其他 Agent 可指定自己的 skills 目录，当前没有自动写宿主配置。

安装完成后调用 `$awesome-skill-maker`。新建示例：

```sh
python3 "$HOME/.codex/skills/awesome-skill-maker/project/scripts/initialize_skill_project.py" \
  --destination ./my-large-skill --name my-large-skill \
  --repository YOUR_ACCOUNT/my-large-skill --description '实际能力与触发场景'
```

生成包含 setup、release、共享工具、开发约定和 CI 的源码骨架；业务模块按实际能力补充，每个模块有消费 `SKILL.md` 和开发 `AGENTS.md`，脚本完整表达动作与对象。生成工具不会把业务模块的计划冒充完成。

```sh
python3 "$HOME/.codex/skills/awesome-skill-maker/setup/scripts/manage_skill_installation.py" check --target "$HOME/.codex/skills/awesome-skill-maker"
python3 "$HOME/.codex/skills/awesome-skill-maker/setup/scripts/manage_skill_installation.py" upgrade --repository kwgjjeffrey/awesome-skill-maker --target "$HOME/.codex/skills/awesome-skill-maker" --store "$HOME/.local/share/awesome-skill-maker"
python3 "$HOME/.codex/skills/awesome-skill-maker/setup/scripts/manage_skill_installation.py" rollback --target "$HOME/.codex/skills/awesome-skill-maker" --store "$HOME/.local/share/awesome-skill-maker"
```

更新保留外部用户配置，只切换自己拥有的目标链接；损坏制品、未知目录、并行安装会拒绝。回退只切换制品，不回滚业务数据。更新锁残留时先确认无安装进程，再处理锁；中断在链接/receipt 提交之间时 check 会报告不一致，需要核对 receipt 和版本目录后恢复。当前没有自动崩溃恢复、卸载/GC、Windows 激活适配器。

## 开发及发布

```sh
python3 project/scripts/validate_skill_project.py --repo .
python3 -m unittest discover -s tests
# 提交为干净 Git HEAD 后：
python3 release/scripts/build_skill_artifact.py --repo .
# origin/main 与 HEAD 一致且 gh 已登录：
python3 release/scripts/publish_github_release.py --repo .
```

`skill-project.json` 是消费文件白名单；构建输出 tgz 和记录 sourceCommit/size/SHA-256 的 manifest。测试、开发 AGENTS.md、私有配置和源证据不进入制品。发布使用 draft → 上传 → 下载校验 → 公开；同版本拒绝覆盖。GitHub Actions 验证结构和生命周期测试，发布命令由人或 Agent 在授权任务内执行。

来源与取舍见 [docs/source-evidence.md](docs/source-evidence.md)，完整用户约定见 [docs/skill-authoring.md](docs/skill-authoring.md)。MIT 开源。
