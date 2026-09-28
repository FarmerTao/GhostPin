# Device workflow and troubleshooting

[English](workflow.md) | [简体中文](workflow.zh-CN.md)

## 1. Establish a usable environment

Use a terminal on the connected Mac. A browser-only or remote agent cannot operate the USB device unless an appropriate local execution tool is available. The supplied wrapper is macOS-only; do not present Windows/Linux instructions as tested equivalents.

`scripts/bootstrap.sh` creates `.venv` inside the skill folder and installs the pinned top-level dependency from `scripts/requirements.txt`. It needs an existing Python 3.12+. Use `PYTHON_BIN` if `python3` points to Apple's older command-line-tools Python. Do not change `HOME`, `CODEX_HOME`, system Python, or global pip packages to make the script work.

The environment, `.cache` downloads, and `.state` lock files are local and ignored by Git. Upstream `pymobiledevice3` may also use `~/.pymobiledevice3` for support files and pairing information. Do not delete that directory as routine cleanup: it may be shared with other tools. Bootstrap downloads can take several minutes on a slow network; inspect progress and report meaningful changes.

## 2. Connect and trust

User instructions:

1. Connect the phone directly with a data-capable cable. A charging indication alone does not prove USB data is working.
2. Unlock the phone. If macOS asks whether to allow the accessory, allow the intended iPhone.
3. On the phone, accept **Trust This Computer** and enter the passcode there.
4. Keep the phone connected. Finder can help confirm it appears, but `location.py devices` is the workflow's device inventory.

`devices` uses a simple USB list, so it can enumerate a phone before pairing is complete. A later `doctor` failure may therefore mean trust is pending. Multiple devices are never implicitly selected. Once selected, retain `--udid` through every step and after reboot.

## 3. Reveal and enable Developer Mode

Run `doctor --udid ID`. If `developer_mode` is false, ask the user to open **Settings → Privacy & Security → Developer Mode**. If the option is missing, run `reveal --udid ID`, then ask them to leave and reopen Settings.

The reveal command only requests that iOS show the option. It does not prove that the user can see it or enable the mode. The user toggles it, accepts the restart, unlocks after restart, and confirms **Turn On**. Recheck `doctor`; do not continue while it returns false. Do not use the upstream automatic enable command to skip the user's restart/confirmation sequence.

Example agent message:

> The Developer Mode entry has been requested. Reopen Settings → Privacy & Security, enable Developer Mode, restart when prompted, then unlock and confirm Turn On. Tell me when the phone is ready.

## 4. Mount developer support

Run `prepare --udid ID` with the phone unlocked. It checks the version, Developer Mode, and whether a Personalized image is already mounted. If absent, it invokes upstream `mounter auto-mount` with a 180-second limit, then independently checks the mount list. A host permission prompt may be needed for USB or network access; respect the agent host's permission flow.

The device's personalization step contacts Apple. An image having been downloaded is not proof that it can be mounted on every phone. Errors about build identity, signing, unsupported services, or a newer iOS release require current upstream investigation; do not cycle through random images or alter device security settings.

### Download fallback

The original session could not promptly reach `raw.githubusercontent.com`, but `api.github.com` was reachable. The helper `fetch_ddi.py`:

1. Resolves the upstream `doronz88/DeveloperDiskImage` ref to one commit.
2. Fetches metadata for the Personalized image, trust cache, and build manifest at that commit.
3. Downloads each blob from GitHub's API with a network timeout.
4. Checks size and Git blob SHA-1, records SHA-256 and commit metadata locally, and writes a completion manifest.

Use `prepare --ddi-dir PATH` only after this helper succeeds. It verifies the files against the local completion manifest. The manifest is not an independent trust anchor; download only from the configured upstream. These files remain external runtime assets and must not be committed.

API rate limits or connectivity failures are reported; retry after addressing the error. No GitHub token is required by this helper. Do not ask users to paste tokens into chat to bypass a rate limit. Default `main` can change across downloads; `--ref COMMIT` can reproduce a previously recorded asset revision. Never replace the runtime's expected asset version silently after an upgrade.

## 5. Choose the location and start a session

Obtain the intended place and source coordinate system. If the user says “Fudan,” clarify the campus; if they have already said “Handan,” preserve it. For exact positioning, use a chosen landmark or address rather than guessing from the university's city.

`location.py set` accepts finite latitude/longitude and requires `--source wgs84` or `--source gcj02`. GCJ-02 conversion uses a commonly used approximation for mainland-China coordinates; it is not a surveying-grade transformation. Unknown or BD-09 coordinates need a separate verified conversion/source. Never reverse latitude and longitude. The [Fudan example](fudan-example.md) records both input and converted coordinates.

Use a persistent terminal/PTY. The helper runs upstream in a child session and waits for it; only one helper `set` session per device can hold its local lock. The upstream message “Press Ctrl+C…” means it reached its waiting stage after the set call. The wrapper's initial “Requesting…” line is only an intention, not evidence of acceptance. Do not announce success while connection/tunnel errors are still present.

The pinned upstream release automatically tries a native macOS tunnel for iOS 17+. A message saying it is retrying over that tunnel is not itself a failure. Do not preemptively start `sudo` tunnels, kill Apple's services, or modify global networking. If automatic transport fails, inspect the actual error and the [upstream tunnel guide](https://doronz88.github.io/pymobiledevice3/guides/ios17-tunnels/).

## 6. Verify separately

Ask the user to:

1. Open Maps and tap the current-location button. Check the blue location marker, not just a searched place pin.
2. Exit and reopen the intended app or mini program, allow location if requested, and trigger a fresh location read.
3. Report both results, including any error shown.

A fresh map result and an app accepting location are separate claims. An app can cache data, combine other signals, or identify simulated location. Apple's [`isSimulatedBySoftware`](https://developer.apple.com/documentation/corelocation/cllocationsourceinformation/issimulatedbysoftware) exposes software simulation information. Stop at reporting an app rejection; do not extend the task into defeating that detection. The user handles any registration or other business submission.

## 7. Restore and finish

- Preferred: Ctrl+C in the exact `location.py set` session. The helper terminates its own child by its live process handle, then runs `clear` on the same UDID.
- If that session is missing or was force-killed: run `clear --udid ID` after reconnecting and unlocking the original phone.
- If clearing from another terminal: the old set session may remain waiting, although it does not continuously resend the location. Close it before starting another session. Avoid overlapping direct-upstream and wrapper sessions.
- Check the exit result. If the command failed or timed out, say recovery is unconfirmed. Never equate killing a process or unplugging USB with clearing location.
- Ask the user to verify current location in Maps. Reopen Maps if it still shows a cached location. If the normal clear path cannot be used, the user can restart the phone and verify again; do not promise a reboot always fixes every app cache.
- Developer Mode remains on. The user may switch it off in Settings after finishing; follow any restart prompt. This is optional cleanup, not automatic behavior of `clear`.

## Troubleshooting

| Symptom | Next step |
|---|---|
| Python is 3.9 / installation rejects Python | Select an existing Python 3.12+ through `PYTHON_BIN`; do not alter system Python. |
| No USB device / charging only | Unlock, reconnect, check data cable/port and accessory permission. |
| Multiple USB devices | Ask which ID; pass `--udid` throughout. |
| Trust/pairing request pending | User confirms on the phone; do not request their passcode. |
| `PermissionError: Operation not permitted` for usbmux | Use the agent host's USB/sandbox permission flow. This is distinct from iPhone trust. |
| Developer Mode missing | `reveal`, reopen Settings, then user enables/restarts/confirms. |
| `DeviceLocked` during preparation | Ask for unlock and keep screen on; retry once after confirmation. |
| Raw GitHub download hangs | Stop that attempt; use `fetch_ddi.py` API fallback and `--ddi-dir`. |
| API 403/429 | Read rate-limit/network error and retry later; don't loop or invent a mirror. |
| Unsupported build/signing/service | Check current upstream support; don't claim all iOS 17–26 devices work. |
| Native tunnel retry warning | Allow the normal fallback to finish; inspect subsequent result. |
| Maps is displaced by hundreds of meters | Recheck source coordinate system and lat/lon order. |
| Maps correct, mini program unchanged/rejected | Report the distinction; reopen and request a fresh location once. No app acceptance guarantee. |
| Restore after disconnect fails | Reconnect/unlock the same device, run clear, verify; consider user-initiated reboot if unavailable. |

After the same failure recurs with no relevant state change, stop dependent operations and request the missing phone action or explain the external blocker. Do not keep a waiting process hidden from the user.
