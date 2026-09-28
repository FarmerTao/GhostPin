# GhostPin

[English](README.md) | [简体中文](README.zh-CN.md)

让本地 AI agent 引导用户完成 iPhone USB 连接、开启开发者模式、模拟定位、验证及恢复。本仓库把一次真实的 macOS 操作流程整理为可独立安装的 agent skill，附带 Python 工具和手机操作说明。英文是默认文档入口。

**支持范围：** Mac、实体 iPhone、USB 和 `pymobiledevice3`。原始操作没有安装完整 Xcode，也没有越狱。脚本实现 iOS 17–26 的路径；这只是实现范围，**不代表所有版本及 App 均已验证兼容**。

## 已经验证到哪一步

原始会话使用 macOS 15.4、Python 3.12.14、`pymobiledevice3` 11.19.4、iOS 26.6.1，完成了开发者模式查询与入口显示、开发者支持镜像挂载、定位设置命令进入持续等待状态，以及恢复命令成功退出。

目标是复旦大学邯郸校区光华楼附近，用户想在微信小程序“复旦学生注册”中使用。**会话中没有用户确认地图已正确移动，也没有小程序接受模拟位置的证据。** 因此本仓库不声称注册成功、绕过检查或无法被识别。详见[复旦示例](skills/ghostpin/references/fudan-example.zh-CN.md)。

## 安装 skill

把整个 `skills/ghostpin` 文件夹复制到 agent 的 skill 目录，保留脚本和 references。Codex 常用默认路径示例：

```bash
mkdir -p "$HOME/.codex/skills"
# 目标目录若已存在，先检查原内容，不要直接覆盖。
cp -R skills/ghostpin "$HOME/.codex/skills/"
```

根据宿主要求重新加载 skill 或重启 agent。其他 agent 请使用其支持的发现目录，或明确要求它读取 `skills/ghostpin/SKILL.md`。Agent 必须能在**实际连接手机的电脑**上运行终端；远程云沙箱不会自动获得本机 USB 访问能力。

示例请求：

> 使用 $ghostpin，引导我连接 iPhone，把定位模拟到复旦大学邯郸校区附近。帮我在地图中验证，并在结束后恢复真实定位。

用户说“帮我恢复真实定位”时，应直接进入恢复流程，不要先重新设置位置。

## 环境要求

- Mac、支持数据传输的 USB 线，以及可由用户解锁的 iPhone。
- Python 3.12+，包含 `venv` 和 `pip`。如未安装，可通过 [python.org](https://www.python.org/downloads/macos/) 或已有包管理器安装；脚本不会安装系统 Python。
- 能访问 Python 软件源、开发者支持文件以及 Apple 个性化签名服务的网络。
- Agent 终端有 USB 服务与网络访问权限；沙箱权限和手机“信任此电脑”是两层不同的权限。
- 已明确坐标系的目标坐标。模拟使用 WGS84；GCJ-02 转换是近似值。只有地名时，应先明确校区、入口或地标。

## 手动快速使用

以下从仓库根目录执行；安装到其他位置后，修改 `SKILL`。变量需保留在同一个终端中；agent 的独立命令调用可以使用绝对路径。

```bash
SKILL="$PWD/skills/ghostpin"
bash "$SKILL/scripts/bootstrap.sh"
# 指定已经安装的新版 Python：
# PYTHON_BIN=/absolute/path/to/python3.12 bash "$SKILL/scripts/bootstrap.sh"
PY="$SKILL/.venv/bin/python"
"$PY" "$SKILL/scripts/location.py" devices
```

连接并解锁手机，点击“信任此电脑”，**在手机上**输入密码。记录 `devices` 输出的目标设备 ID，仅在本机使用，不要提交或公开。

```bash
DEVICE_ID='replace-with-your-device-id'
"$PY" "$SKILL/scripts/location.py" doctor --udid "$DEVICE_ID"
# 仅在找不到开发者模式入口时：
"$PY" "$SKILL/scripts/location.py" reveal --udid "$DEVICE_ID"
```

手机打开“设置 → 隐私与安全性 → 开发者模式”，开启后按提示重启，解锁并确认“开启”。必要时重新连接。准备过程中保持屏幕亮着。

```bash
"$PY" "$SKILL/scripts/location.py" doctor --udid "$DEVICE_ID"
"$PY" "$SKILL/scripts/location.py" prepare --udid "$DEVICE_ID"
```

自动下载超时，可以通过同一上游项目的 GitHub 官方 API 下载并校验文件，再挂载：

```bash
"$PY" "$SKILL/scripts/fetch_ddi.py" --out "$SKILL/.cache/ddi"
"$PY" "$SKILL/scripts/location.py" prepare --udid "$DEVICE_ID" --ddi-dir "$SKILL/.cache/ddi"
```

光华楼 GCJ-02 示例坐标：

```bash
"$PY" "$SKILL/scripts/location.py" set --udid "$DEVICE_ID" \
  --lat 31.300023 --lon 121.505283 --source gcj02
```

保持终端会话运行。在手机地图点击“当前位置”，再退出并重新进入目标 App 或小程序获取定位。分别记录这两个验证结果。模拟位置可能影响其他 App，App 也可能识别软件模拟位置。命令成功不等于小程序接受。

### 恢复真实定位

在运行中的 helper 终端按 **Ctrl+C**，它会停止自身子进程，并明确执行 `clear`。若进程被强制结束、手机断线或恢复失败，重新连接并解锁**同一台手机**，运行：

```bash
"$PY" "$SKILL/scripts/location.py" clear --udid "$DEVICE_ID"
```

到地图重新确认当前位置。不要假定拔线就会恢复。单独执行 `clear` 不会关闭还在等待的 `set` 终端；开始新会话前先退出旧会话。常规恢复失败时，见[排障说明](skills/ghostpin/references/workflow.zh-CN.md#排障)，包括重启手机后重新检查地图。

## 文档导航

| 内容 | English | 中文 |
|---|---|---|
| Agent 入口 | [SKILL.md](skills/ghostpin/SKILL.md) | [Skill 说明](docs/skill.zh-CN.md) |
| 连接、手机操作、恢复与排障 | [Workflow](skills/ghostpin/references/workflow.md) | [操作与排障](skills/ghostpin/references/workflow.zh-CN.md) |
| 复旦/微信案例与坐标来源 | [Example](skills/ghostpin/references/fudan-example.md) | [复旦示例](skills/ghostpin/references/fudan-example.zh-CN.md) |
| 测试与维护 | [Development](docs/development.md) | [开发说明](docs/development.zh-CN.md) |

## 范围与数据

Skill 只在用户要求的范围内修改设备模拟定位，不负责提交注册、考勤、付款或其他业务操作，不修改 App 的检测机制，也不保证任何服务接受模拟位置。使用者应遵守所使用服务的规则。

仓库不包含凭据、配对记录、真实设备 ID、运行日志、虚拟环境或开发者镜像。工具在本机调用上游软件；上游可能在自己的用户目录缓存支持文件和配对数据。本地依赖、缓存和锁文件均被 Git 忽略。镜像每次下载先将上游版本解析到固定 commit，再校验 Git blob；这验证传输一致性，不是独立的真实性证明。设备仍需通过 Apple 的个性化签名流程。

本仓库原创脚本和文档采用 [MIT 许可证](LICENSE)。`pymobiledevice3`、Apple 组件和其他依赖保留各自许可与条款，本仓库不打包这些组件，也不改变其许可证。
