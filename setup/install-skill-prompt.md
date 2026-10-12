# 分享用安装提示词

复制下方整段给目标 Agent。安装 GitHub latest 已发布制品，不 clone 开发源码。适用于 macOS/Linux；其他宿主选择其自己的 skills 目录。

```text
请安装或升级 awesome-skill-maker，使用公开 GitHub 仓库 kwgjjeffrey/awesome-skill-maker 的 latest Release 制品：
https://github.com/kwgjjeffrey/awesome-skill-maker/releases/latest

先只读检查 Python 3.9+、curl、操作系统及目标 Agent 的 skills 目录。Codex 默认目标为 ~/.codex/skills/awesome-skill-maker，外部版本与状态 store 为 ~/.local/share/awesome-skill-maker。其他宿主按实际配置选择 skills 目录，不能猜测或覆盖未知文件。前置条件缺失时报告具体缺项。

若目标已安装，先从目标链接和 store/receipt.json 只读确认它是同一产品的 managed 安装，并沿用原安装 store；不要替换开发 checkout 或普通未托管目录。安装和升级都使用下面从 latest 下载并校验的 bootstrap，避免旧安装器不支持新制品格式。

请求 https://api.github.com/repos/kwgjjeffrey/awesome-skill-maker/releases/latest，记录一次返回的 tag_name，并固定到该 tag 下载，避免后续 latest 发生变化。只接受 vX.Y.Z 格式、公开的非 draft/非 prerelease Release。下载该 Release 的 awesome-skill-maker-release.json、awesome-skill-maker-X.Y.Z.tgz 和 bootstrap_skill_installation.py 三个 assets 到临时目录；所有资源必须属于同一仓库的同一 tag。无需 GitHub 登录。

核对 manifest 的 repository/name/version 与该 Release，核对 tag 对应的 commit 与 manifest.sourceCommit（annotated tag 需解引用）；对归档和 bootstrap 分别验证 manifest 声明的 size 与 SHA-256。任何不一致都停止，不能执行未校验的 bootstrap。

校验完成后执行：
python3 <临时目录>/bootstrap_skill_installation.py --archive <临时目录>/awesome-skill-maker-X.Y.Z.tgz --manifest <临时目录>/awesome-skill-maker-release.json --target <目标目录> --store <外部 store>
再从已安装目录执行：
python3 <目标目录>/setup/scripts/manage_skill_installation.py check --target <目标目录>

使用安装后的根 SKILL.md；不要引用开发仓库，不把内部模块注册为独立 Skill。告知安装版本、路径和校验结果；宿主若尚未发现新入口，提示重新加载或重启会话。完成后清理本次临时下载，保留托管版本和用户状态。
```
