# GhostPin

[English](README.md) | [简体中文](README.zh-CN.md)

Let a local AI agent guide an iPhone through USB connection, Developer Mode, simulated location, verification, and restoration. This repository packages a real macOS workflow as a self-contained agent skill, with small Python helpers and user-facing phone instructions.

**Scope:** macOS, a physical iPhone, USB, and `pymobiledevice3`. No full Xcode installation or jailbreak was needed in the recorded session. The helpers target iOS 17–26; that is an implementation boundary, **not a compatibility guarantee for every version or app**.

## What was actually verified

In the original session, macOS 15.4, Python 3.12.14, `pymobiledevice3` 11.19.4, and iOS 26.6.1 were used. Developer Mode was queried and its settings entry revealed, a personalized developer image was mounted, the location command entered its active waiting state, and the clear command later exited successfully.

The target was near Guanghua Building, Fudan University Handan Campus. “复旦学生注册” was the user's target WeChat mini program. **The session contains no user confirmation that Maps moved correctly or that the mini program accepted the location.** This repository does not claim successful registration, bypassing app checks, or undetectable simulation. See the [case study](skills/ghostpin/references/fudan-example.md).

## Install the skill

Copy the entire `skills/ghostpin` directory, including its scripts and references, into your agent's skill directory. For Codex with the conventional default directory:

```bash
mkdir -p "$HOME/.codex/skills"
# If this destination already exists, review it before replacing anything.
cp -R skills/ghostpin "$HOME/.codex/skills/"
```

Reload skills or restart the agent if required by your host. For another agent, use its supported skill discovery path, or explicitly ask it to read `skills/ghostpin/SKILL.md`. The agent needs a terminal on the **computer physically connected to the phone**; a remote cloud sandbox cannot access that USB device by itself.

Example request:

> Use $ghostpin to guide me through connecting my iPhone and simulate a location near Fudan University's Handan Campus. Help me verify it in Maps and restore the real location afterwards.

An instruction such as “restore my real location” should trigger the recovery workflow immediately, without setting another location first.

## Prerequisites

- A Mac, a data-capable USB cable, and an iPhone you can unlock.
- Python 3.12 or later, with `venv` and `pip`. If absent, install it from [python.org](https://www.python.org/downloads/macos/) or your existing package manager. The script does not install a system Python.
- Network access for Python dependencies, developer support files, and Apple's personalization service.
- Permission for the agent's terminal to access USB services and the network. Agent sandbox approval is separate from the iPhone's Trust prompt.
- A location with a known coordinate system. WGS84 is used for simulation; GCJ-02 conversion is approximate. A place name alone must be resolved to the intended campus/entrance/landmark.

## Manual quick start

Run the following from this repository's root. After copying the skill elsewhere, adjust `SKILL` to its installed directory. Keep shell variables in the same terminal, or use full paths in agent tool calls.

```bash
SKILL="$PWD/skills/ghostpin"
bash "$SKILL/scripts/bootstrap.sh"
# To select an existing newer Python explicitly:
# PYTHON_BIN=/absolute/path/to/python3.12 bash "$SKILL/scripts/bootstrap.sh"
PY="$SKILL/.venv/bin/python"
"$PY" "$SKILL/scripts/location.py" devices
```

Connect and unlock the phone, accept **Trust This Computer**, and enter the passcode **on the phone**. Select the device ID from `devices`; it is local device information, not something to commit or publish.

```bash
DEVICE_ID='replace-with-your-device-id'
"$PY" "$SKILL/scripts/location.py" doctor --udid "$DEVICE_ID"
# Only if the Developer Mode setting is missing:
"$PY" "$SKILL/scripts/location.py" reveal --udid "$DEVICE_ID"
```

On the phone, open **Settings → Privacy & Security → Developer Mode**, enable it, restart when prompted, unlock, and confirm **Turn On**. Reconnect if necessary. Keep the screen on for preparation.

```bash
"$PY" "$SKILL/scripts/location.py" doctor --udid "$DEVICE_ID"
"$PY" "$SKILL/scripts/location.py" prepare --udid "$DEVICE_ID"
```

If automatic download times out, use the same upstream project's GitHub API fallback, then retry with verified local files:

```bash
"$PY" "$SKILL/scripts/fetch_ddi.py" --out "$SKILL/.cache/ddi"
"$PY" "$SKILL/scripts/location.py" prepare --udid "$DEVICE_ID" --ddi-dir "$SKILL/.cache/ddi"
```

Example using the approximate GCJ-02 coordinates of Guanghua Building:

```bash
"$PY" "$SKILL/scripts/location.py" set --udid "$DEVICE_ID" \
  --lat 31.300023 --lon 121.505283 --source gcj02
```

Keep that terminal/session open. In Maps, tap current location; then reopen the target app or mini program and request location again. Record these as separate observations. Location simulation may affect other apps, and apps can identify software-generated location. A successful command does not prove app acceptance.

### Restore real location

Press **Ctrl+C** in the running helper. It stops its own child process and explicitly attempts `clear`. If the process was forcibly killed, the phone disconnected, or restoration failed, reconnect and unlock the same phone, then run:

```bash
"$PY" "$SKILL/scripts/location.py" clear --udid "$DEVICE_ID"
```

Check current location in Maps. Do not assume unplugging the cable restores it. A separate `clear` command clears location but does not close an already waiting `set` terminal; close that session before starting a new one. If normal recovery fails, consult [troubleshooting](skills/ghostpin/references/workflow.md#troubleshooting), including restarting the phone and rechecking Maps.

## Documentation

| Document | English | 中文 |
|---|---|---|
| Agent entry point | [SKILL.md](skills/ghostpin/SKILL.md) | [Skill explanation](docs/skill.zh-CN.md) |
| Phone setup, agent execution, recovery, troubleshooting | [Workflow](skills/ghostpin/references/workflow.md) | [操作与排障](skills/ghostpin/references/workflow.zh-CN.md) |
| Fudan / WeChat case and coordinate provenance | [Example](skills/ghostpin/references/fudan-example.md) | [复旦示例](skills/ghostpin/references/fudan-example.zh-CN.md) |
| Tests and maintenance | [Development](docs/development.md) | [开发说明](docs/development.zh-CN.md) |

## Boundaries and data

The skill changes a device's simulated location only within the user's request. It does not submit registration, attendance, purchases, or other app actions, modify app defenses, or promise a particular service will accept the location. Users should follow the rules of the service they use.

No credentials, pairing records, actual device IDs, runtime logs, virtual environments, or developer images are shipped. Helpers use upstream software locally; upstream may cache support files and pairing data in its own user directory. Local dependencies, caches, and lock files are ignored by Git. DDI downloads are pinned to a resolved upstream commit per run and checked against Git blob metadata; this checks consistency, not independent authenticity. Apple's device personalization still applies.

The original helper source and documentation use the [MIT license](LICENSE). `pymobiledevice3`, Apple components, and other dependencies retain their own licenses and terms; they are not relicensed or vendored here.
