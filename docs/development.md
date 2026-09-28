# Development and validation

[English](development.md) | [简体中文](development.zh-CN.md)

## Layout

```text
README.md / README.zh-CN.md         User entry points
skills/ios-location/SKILL.md        Agent entry point
skills/ios-location/agents/         Codex UI metadata
skills/ios-location/scripts/        Bootstrap, CLI, coordinates, DDI download
skills/ios-location/references/     English/Chinese phone workflow and example
docs/                              Contributor and translated skill guidance
tests/                             Offline behavioral tests
```

The skill directory is self-contained when copied elsewhere. Helpers resolve their own directory, use the running Python interpreter, and do not embed the author's computer paths. `requirements.txt` pins the direct dependency only; transitive dependency resolution can change. Consider a platform-specific lockfile after independently validating upgrades.

## Offline validation

From the repository root, using Python 3.12+ on macOS (the unit suite also uses POSIX file locks):

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q skills/ios-location/scripts tests
bash -n skills/ios-location/scripts/bootstrap.sh
python3 skills/ios-location/scripts/location.py --help
python3 skills/ios-location/scripts/coordinates.py --lat 31.300023 --lon 121.505283 --source gcj02
git diff --check
```

No phone or network is accessed by these tests. They cover coordinate rejection and the recorded landmark conversion, zero/multiple/missing-device selection, locked or unconfirmed mounts, timeout/error handling, same-device cleanup after session interruption, cleanup failure reporting, exclusive session locks, and pinned/checksummed download behavior with mocked responses.

If your environment has Codex's `skill-creator`, its `scripts/quick_validate.py skills/ios-location` additionally validates skill frontmatter. It is an optional maintainer check, not a runtime dependency or a substitute for behavioral testing.

## Hardware validation is separate

The original direct-command evidence is in the [case study](../skills/ios-location/references/fudan-example.md). Do not claim the wrapper tests prove a new OS/device combination works. For a user-authorized hardware test, record OS/runtime versions, Developer Mode state, mount result, set result, actual Maps observation, app observation if requested, clear result, and final Maps observation. Never commit raw UDIDs, pairing records, screenshots containing private information, or a user's location history.

Review an agent against realistic scenarios without executing device commands: a hidden Developer Mode setting, two attached phones, a phone that locks before mounting, an unknown coordinate system, a map that moves while an app rejects location, and a request to restore after the session disappeared. Correct outcomes preserve device selection, wait for required user phone actions, make no unsupported app claims, and prioritize recovery.

## Maintenance

Before changing the pinned CLI, review upstream command help, tunnel behavior, image selection, error exit codes, and cleanup behavior. iOS 27+ intentionally needs adaptation rather than blindly using the Personalized path. Never copy a support image into the repository. The API downloader resolves `main` at runtime; retain the local download manifest for troubleshooting or pass its commit as `--ref` to reproduce it.

Keep English and Chinese guides aligned when commands or phone steps change. English is the canonical skill instruction and CLI language; the agent should explain results in the user's language. Original repository code/docs are MIT; runtime dependencies and Apple files retain their own terms.

Before sharing, inspect `git ls-files` and `git status --ignored` to ensure no runtime data is staged. Create a remote and push only when requested; a local `git init` does not publish a GitHub repository.
