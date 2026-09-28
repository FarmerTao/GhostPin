# 开发与验证

[English](development.md) | [简体中文](development.zh-CN.md)

## 目录

```text
README.md / README.zh-CN.md         用户入口
skills/ghostpin/SKILL.md        Agent 入口
skills/ghostpin/agents/         Codex 展示元数据
skills/ghostpin/scripts/        安装、CLI、坐标转换、镜像下载
skills/ghostpin/references/     中英文手机流程与示例
docs/                              维护及 skill 中文说明
tests/                             离线行为测试
```

整个 skill 文件夹复制后可以独立使用。脚本按自身目录定位资源，使用当前 Python 解释器，不写死作者机器路径。`requirements.txt` 只固定直接依赖，传递依赖可能变化；升级经过独立验证后可考虑增加平台锁文件。

## 离线检查

在仓库根目录，使用 macOS 上的 Python 3.12+；单元测试使用 POSIX 文件锁：

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q skills/ghostpin/scripts tests
bash -n skills/ghostpin/scripts/bootstrap.sh
python3 skills/ghostpin/scripts/location.py --help
python3 skills/ghostpin/scripts/coordinates.py --lat 31.300023 --lon 121.505283 --source gcj02
git diff --check
```

测试不访问手机或网络，覆盖坐标拒绝和案例转换、零/多设备与原设备缺失、锁屏与挂载证据缺失、超时和错误、会话中断后同设备恢复、恢复失败报告、会话互斥，以及用模拟响应验证固定 commit 与下载校验。

若环境有 Codex `skill-creator`，可额外运行其中的 `scripts/quick_validate.py skills/ghostpin` 检查 frontmatter。它是可选维护检查，不是运行依赖，也不能替代行为测试。

## 真机验证另行记录

原始上游命令证据见[案例](../skills/ghostpin/references/fudan-example.zh-CN.md)。不要声称离线测试能证明新的系统/机型兼容。用户授权真机测试时，记录系统/运行时版本、开发者模式、挂载、set、实际地图观察、按需应用观察、clear，以及恢复后的地图观察。不得提交原始 UDID、配对记录、含隐私的截图或用户位置历史。

可以不运行设备命令，推演这些 agent 场景：开发者模式入口缺失、两台手机连接、挂载前自动锁屏、未知坐标系、地图改变而应用拒绝、会话丢失后要求恢复。正确行为应固定目标设备、等待必要的手机操作、不夸大应用结果、优先恢复。

## 维护

更新固定 CLI 版本前，核查上游命令参数、隧道、镜像选择、错误退出码和恢复行为。iOS 27+ 需专门适配，不能直接沿用 Personalized 路径。镜像不得复制进仓库。API 下载器运行时解析 `main`，本地下载清单可用于排障，也可用其中的 commit 作为 `--ref` 复现。

命令或手机操作变化时同步维护中英文。英文是正式 skill 指令和 CLI 默认语言，agent 应用用户的语言解释。原创代码/文档采用 MIT，运行依赖和 Apple 文件保留各自条款。

分享前检查 `git ls-files` 和 `git status --ignored`，确认未暂存运行数据。只有用户要求发布时才创建远程并推送；本地 `git init` 不代表已经发布到 GitHub。
