# Setup

macOS/Linux，Python 3.9+、curl；开发或发布还需要 Git/gh。无第三方依赖，不准备常驻服务。

```sh
python3 <skill>/setup/scripts/manage_skill_installation.py check
python3 <skill>/setup/scripts/manage_skill_installation.py install --archive <release.tgz> --manifest <release.json> --target <agent-skills>/<name> --store <external-version-store>
python3 <skill>/setup/scripts/manage_skill_installation.py check --target <agent-skills>/<name>
python3 <skill>/setup/scripts/manage_skill_installation.py upgrade --repository <owner/repo> --target <agent-skills>/<name> --store <external-version-store>
python3 <skill>/setup/scripts/manage_skill_installation.py rollback --target <agent-skills>/<name> --store <external-version-store>
```

check 只读、输出前置条件及安装 receipt。install 校验 manifest 的大小、SHA-256、版本和归档路径/类型，再解包到隔离 staging、验证结构、激活稳定链接。目标已存在时，仅更新同一 store receipt 所属链接；拒绝普通目录和源码 checkout。版本目录不可修改，receipt 与升级锁放外部 store；用户配置、项目及缓存不放版本目录。失败保留原链接。rollback 切回 receipt 中前一版本；不会回滚业务数据。保留旧版本，不自动清理未知文件。

upgrade 从公开 GitHub latest Release 下载 manifest 与归档，并对照 tag 的 commit 验证 sourceCommit；每次只接受更高版本。GitHub 是当前信任来源，SHA-256 提供完整性而非独立签名。高信任场景另行配置可信签名密钥，不能声称当前实现有签名验证。

首次安装：从 GitHub Release 下载归档及 manifest 后，执行 `python3 setup/bootstrap_skill_installation.py --archive ... --manifest ... --target ... --store ...`。该 bootstrap 从源码分发地址单独获得，先验证归档再运行包内安装器；见仓库 README 的具体 URL。安装完成后由 Agent 原生 loader 发现稳定链接，必要时重启 Agent。

用户要安装提示词或分享本 Skill 时，读取 [install-skill-prompt.md](install-skill-prompt.md)，提供可直接复制的提示词。它指向 latest Release，并在首次安装时固定一个 tag 后校验所有制品；不要给开发 checkout 的安装路径。bootstrap 也作为 Release asset 分发，由 manifest 记录大小与 SHA-256。

兼容说明：0.1.0 的安装器要求内部模块有 frontmatter，无法直接接受新版单入口结构。升级旧安装时使用分享提示词中的已校验 latest bootstrap，沿用原 target/store；新版安装器能管理单入口制品。
