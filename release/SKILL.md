---
name: awesome-skill-maker-release
description: 构建可追溯 Skill 制品并通过 GitHub Release 分发。
---
# GitHub 分发

在目标源码仓库执行其 release 工具，或使用本制品的通用构建器：

```sh
python3 <skill>/release/scripts/build_skill_artifact.py --repo <repo>
python3 <repo>/release/scripts/publish_github_release.py --repo <repo>
```

构建输入 `skill-project.json` 和干净的 Git HEAD，输出 `dist/<name>-<version>.tgz` 及 `dist/<name>-release.json`。白名单只打包消费资源，排除开发说明、tests、docs、状态与凭据。manifest 固定 sourceCommit、大小和 SHA-256；若存在关联 tag，必须指向 HEAD。同一版本不得替换内容。

发布器先校验配置中的仓库与 origin、认证、干净状态，再构建；要求 origin/main 已指向本地 HEAD。创建 draft Release 与精确 HEAD tag，上传两个制品、下载读回并比对后才公开。已有同名 Release 拒绝覆盖，失败保留 draft 便于诊断。首次源码仓库按用户授权用 `gh repo create <owner/repo> --public --source <repo> --remote origin`，再提交、推送；不要将凭据写进仓库。没有授权发布时只构建可评审的本地制品。

源码使用 GitHub Git/PR/Issues 追踪，制品使用 GitHub Releases；CI 验证结构和业务测试。发布必须验证安装后的真实入口、升级/失败保留/回退与状态隔离。独立 runtime/GUI 有独立版本；channel promotion 的版本不能冒充每个组件版本。新增多组件产品时扩展 manifest 和 receipt 为 componentVersions，不能只改说明假装已有支持。
